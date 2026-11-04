import asyncio
from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatHistoryResponse,
    HelpRequestCreate,
    HelpRequestResponse,
    ModeratorSettingsUpdate,
    ModeratorSettingsResponse,
)
from app.services.projects import project_access
from app.services.chat.message_service import MessageService
from app.services.chat.help_request_service import HelpRequestService
from app.services.chat.settings_service import ModeratorSettingsService
from app.services.chat.worker import process_help_request_task
from app.services.ai.trigger_policy import TriggerPolicy
from app.services.ai.metrics import ai_metrics
from app.services.websocket.connection_manager import manager

router = APIRouter(prefix="/projects", tags=["Chat y Asistente Colaborativo"])


@router.get("/{project_id}/messages", response_model=ChatHistoryResponse)
async def get_messages(
    project_id: UUID,
    response: Response,
    limit: int = Query(default=50, ge=1, le=100),
    before: Optional[datetime] = Query(default=None),
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(current_user)
):
    """Recupera el historial de mensajes del proyecto de forma paginada."""
    await project_access(db, project_id, user)
    response.headers["Cache-Control"] = "no-store"
    messages, total, has_more = await MessageService.get_messages(
        db=db, project_id=project_id, limit=limit, before=before
    )
    return ChatHistoryResponse(
        messages=[ChatMessageResponse.model_validate(m) for m in messages],
        total=total,
        has_more=has_more
    )


@router.post("/{project_id}/messages", response_model=ChatMessageResponse, status_code=201)
async def post_message(
    project_id: UUID,
    body: ChatMessageCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(current_user)
):
    """
    Publica un mensaje en el canal colaborativo.
    Si contiene la mención @IA o explicit_help_requested=True, se inicia el procesamiento de asistencia del Desarrollador Senior.
    """
    await project_access(db, project_id, user)

    # 1. Evaluar si la política reactiva activa la IA
    decision = TriggerPolicy.evaluate(body.content, body.explicit_help_requested)

    # 2. Persistir mensaje de usuario
    user_msg = await MessageService.create_message(
        db=db,
        project_id=project_id,
        author_id=user.id,
        author_type="user",
        author_name=user.full_name or "Desarrollador",
        content=body.content,
        reply_to_message_id=body.reply_to_message_id
    )
    await db.commit()
    await db.refresh(user_msg)

    # 3. Difundir mensaje de usuario inmediatamente por WebSocket
    await manager.broadcast(project_id, {
        "type": "chat.message",
        "message": {
            "id": str(user_msg.id),
            "project_id": str(project_id),
            "author_id": str(user.id),
            "author_type": "user",
            "author_name": user_msg.author_name,
            "content": user_msg.content,
            "reply_to_message_id": str(user_msg.reply_to_message_id) if user_msg.reply_to_message_id else None,
            "created_at": user_msg.created_at.isoformat(),
        }
    })

    # 4. Si la IA fue activada explícitamente, registrar HelpRequest e iniciar tarea en background
    if decision.should_trigger:
        idempotency_key = body.idempotency_key or f"msg-{user_msg.id}"
        help_req, is_new = await HelpRequestService.create_help_request(
            db=db,
            project_id=project_id,
            requester=user,
            content=decision.cleaned_prompt,
            idempotency_key=idempotency_key,
            source_message_id=user_msg.id
        )
        await db.commit()
        await db.refresh(help_req)

        if is_new:
            await manager.broadcast(project_id, {
                "type": "help.requested",
                "help_request_id": str(help_req.id),
                "source_message_id": str(user_msg.id),
                "requester_id": str(user.id),
                "requester_name": user_msg.author_name,
                "status": "pending",
            })

            background_tasks.add_task(
                process_help_request_task,
                project_id=project_id,
                help_request_id=help_req.id,
                requester_name=user_msg.author_name,
                prompt=decision.cleaned_prompt,
                source_message_id=user_msg.id
            )

    return ChatMessageResponse.model_validate(user_msg)


@router.post("/{project_id}/help-requests", response_model=HelpRequestResponse, status_code=201)
async def request_help(
    project_id: UUID,
    body: HelpRequestCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(current_user)
):
    """
    Endpoint dedicado para el botón explícito de 'Solicitar ayuda'.
    Garantiza idempotencia ante reintentos o reconexiones.
    """
    await project_access(db, project_id, user)

    decision = TriggerPolicy.evaluate(body.content, explicit_help_requested=True)
    help_req, is_new = await HelpRequestService.create_help_request(
        db=db,
        project_id=project_id,
        requester=user,
        content=decision.cleaned_prompt,
        idempotency_key=body.idempotency_key,
        source_message_id=body.source_message_id
    )
    await db.commit()
    await db.refresh(help_req)

    if is_new:
        # Difundir evento de nueva solicitud a la sala
        await manager.broadcast(project_id, {
            "type": "help.requested",
            "help_request_id": str(help_req.id),
            "source_message_id": str(help_req.source_message_id),
            "requester_id": str(user.id),
            "requester_name": user.full_name or "Desarrollador",
            "status": "pending",
        })

        background_tasks.add_task(
            process_help_request_task,
            project_id=project_id,
            help_request_id=help_req.id,
            requester_name=user.full_name or "Desarrollador",
            prompt=decision.cleaned_prompt,
            source_message_id=help_req.source_message_id
        )

    response_data = HelpRequestResponse.model_validate(help_req)
    response_data.requester_name = user.full_name
    return response_data


@router.get("/{project_id}/help-requests/{help_request_id}", response_model=HelpRequestResponse)
async def get_help_request(
    project_id: UUID,
    help_request_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(current_user)
):
    """Consulta el estado de una solicitud de ayuda existente."""
    await project_access(db, project_id, user)
    help_req = await HelpRequestService.get_help_request(db, project_id, help_request_id)
    return HelpRequestResponse.model_validate(help_req)


@router.get("/{project_id}/moderator-settings", response_model=ModeratorSettingsResponse)
async def get_moderator_settings(
    project_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(current_user)
):
    """Obtiene la configuración de moderación del proyecto."""
    await project_access(db, project_id, user)
    settings = await ModeratorSettingsService.get_or_create(db, project_id)
    return ModeratorSettingsResponse.model_validate(settings)


@router.patch("/{project_id}/moderator-settings", response_model=ModeratorSettingsResponse)
async def update_moderator_settings(
    project_id: UUID,
    body: ModeratorSettingsUpdate,
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(current_user)
):
    """Permite al propietario del proyecto actualizar el modo del moderador."""
    await project_access(db, project_id, user, roles={"OWNER"})
    updated = await ModeratorSettingsService.update(
        db=db,
        project_id=project_id,
        mode=body.mode,
        require_human_approval=body.require_human_approval
    )
    await db.commit()
    return ModeratorSettingsResponse.model_validate(updated)


@router.get("/{project_id}/assistant/telemetry")
async def get_assistant_telemetry(
    project_id: UUID,
    response: Response,
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(current_user)
):
    """Consulta las métricas agregadas de latencia y uso del asistente sin exponer secretos."""
    await project_access(db, project_id, user)
    response.headers["Cache-Control"] = "no-store"
    return ai_metrics.get_summary()
