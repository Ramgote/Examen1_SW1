import asyncio
import logging
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from app.models.chat import HelpRequest, ChatMessage
from app.models.canvas import CanvasSnapshot
from app.services.ai.moderator import AIModerator
from app.services.ai.context_service import ContextService
from app.services.chat.message_service import MessageService
from app.services.chat.help_request_service import HelpRequestService
from app.services.websocket.connection_manager import manager

logger = logging.getLogger(__name__)


async def _get_worker_session():
    """Obtiene una sesión de base de datos, respetando dependency_overrides en tests."""
    from main import app
    from app.core.database import get_db, AsyncSessionLocal

    override = app.dependency_overrides.get(get_db)
    if override:
        gen = override()
        session = await anext(gen)
        return session, False
    return AsyncSessionLocal(), True


async def process_help_request_task(
    project_id: UUID,
    help_request_id: UUID,
    requester_name: str,
    prompt: str,
    source_message_id: UUID
):
    """
    Tarea asíncrona en segundo plano para procesar la solicitud de ayuda con el Desarrollador Senior.
    Garantiza que la API responda inmediatamente al usuario sin bloquear el hilo principal.
    """
    db, should_close = await _get_worker_session()
    try:
        # 1. Marcar la solicitud como 'processing'
        help_req = await db.get(HelpRequest, help_request_id)
        if not help_req:
            logger.error("HelpRequest %s no encontrada en worker", help_request_id)
            return

        help_req.status = "processing"
        await db.commit()

        await manager.broadcast(project_id, {
            "type": "help.processing",
            "help_request_id": str(help_request_id),
            "source_message_id": str(source_message_id),
            "requester_name": requester_name,
        })

        # 2. Cargar contexto del lienzo UML y mensajes recientes
        snapshot = await db.scalar(
            select(CanvasSnapshot).where(CanvasSnapshot.project_id == project_id)
        )

        # Últimos mensajes como historial acotado de referencia
        recent_msgs_query = (
            select(ChatMessage)
            .where(ChatMessage.project_id == project_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(10)
        )
        recent_msgs = list(await db.scalars(recent_msgs_query))
        recent_msgs.reverse()

        history = ContextService.format_conversation_history(
            recent_messages=recent_msgs,
            current_source_id=source_message_id,
            max_messages=6
        )

        # 3. Invocar al moderador senior (con validación de concurrencia y versión esperada)
        moderator = AIModerator()
        senior_advice = await moderator.answer_help_request(
            requester_name=requester_name,
            user_prompt=prompt,
            snapshot=snapshot,
            history=history,
            expected_version=help_req.context_revision
        )

        # 4. Persistir mensaje de respuesta del asistente
        assistant_msg = await MessageService.create_message(
            db=db,
            project_id=project_id,
            author_id=None,
            author_type="assistant",
            author_name="Desarrollador Senior Virtual",
            content=senior_advice,
            reply_to_message_id=source_message_id
        )

        # 5. Actualizar HelpRequest a 'completed'
        await HelpRequestService.update_help_request_status(
            db=db,
            help_request=help_req,
            status="completed",
            response_message_id=assistant_msg.id
        )
        await db.commit()

        # 6. Difundir eventos por WebSocket a todos los miembros de la sala
        await manager.broadcast(project_id, {
            "type": "chat.message",
            "message": {
                "id": str(assistant_msg.id),
                "project_id": str(project_id),
                "author_id": None,
                "author_type": "assistant",
                "author_name": assistant_msg.author_name,
                "content": assistant_msg.content,
                "reply_to_message_id": str(source_message_id),
                "created_at": assistant_msg.created_at.isoformat(),
            }
        })

        await manager.broadcast(project_id, {
            "type": "help.answered",
            "help_request_id": str(help_request_id),
            "source_message_id": str(source_message_id),
            "response_message_id": str(assistant_msg.id),
            "status": "completed",
        })

    except HTTPException as exc:
        logger.warning("Error HTTP en worker de ayuda: %s", exc.detail)
        await _handle_failure(db, project_id, help_request_id, source_message_id, f"HTTP_{exc.status_code}", str(exc.detail))
    except Exception as exc:
        logger.exception("Fallo inesperado procesando solicitud de ayuda")
        await _handle_failure(db, project_id, help_request_id, source_message_id, "INTERNAL_ERROR", "Error temporal al procesar la asistencia técnica.")
    finally:
        if should_close:
            await db.close()


async def _handle_failure(
    db,
    project_id: UUID,
    help_request_id: UUID,
    source_message_id: UUID,
    error_code: str,
    error_message: str
):
    try:
        help_req = await db.get(HelpRequest, help_request_id)
        if help_req:
            await HelpRequestService.update_help_request_status(
                db=db,
                help_request=help_req,
                status="failed",
                error_code=error_code,
                error_message=error_message
            )
            await db.commit()

        await manager.broadcast(project_id, {
            "type": "help.failed",
            "help_request_id": str(help_request_id),
            "source_message_id": str(source_message_id),
            "status": "failed",
            "error_code": error_code,
            "error_message": error_message,
        })
    except Exception:
        logger.exception("Error al registrar fallo de help request")
