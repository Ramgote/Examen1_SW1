from datetime import datetime, timezone
from typing import Optional, Tuple
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chat import HelpRequest, ChatMessage
from app.models.canvas import CanvasSnapshot
from app.models.user import User
from app.services.chat.message_service import MessageService


class HelpRequestService:
    @staticmethod
    async def create_help_request(
        db: AsyncSession,
        project_id: UUID,
        requester: User,
        content: str,
        idempotency_key: str,
        source_message_id: Optional[UUID] = None,
        context_revision: Optional[int] = None
    ) -> Tuple[HelpRequest, bool]:
        """
        Crea una solicitud de ayuda con garantía de idempotencia.
        Retorna (HelpRequest, is_new: bool).
        """
        # 1. Comprobar si ya existe una solicitud con la misma clave en este proyecto
        existing = await db.scalar(
            select(HelpRequest).where(
                HelpRequest.project_id == project_id,
                HelpRequest.idempotency_key == idempotency_key
            )
        )
        if existing is not None:
            return existing, False

        # 2. Si no se especificó la versión del diagrama, obtener la versión actual del lienzo
        if context_revision is None:
            version = await db.scalar(
                select(CanvasSnapshot.version).where(CanvasSnapshot.project_id == project_id)
            )
            context_revision = version if version is not None else 1

        # 3. Si no hay mensaje de chat fuente vinculado, crear el mensaje de usuario primero
        if source_message_id is None:
            user_msg = await MessageService.create_message(
                db=db,
                project_id=project_id,
                author_id=requester.id,
                author_type="user",
                author_name=requester.full_name or "Desarrollador",
                content=content
            )
            source_message_id = user_msg.id
        else:
            # Validar que el source_message_id pertenezca a este proyecto
            msg = await db.scalar(
                select(ChatMessage).where(
                    ChatMessage.id == source_message_id,
                    ChatMessage.project_id == project_id
                )
            )
            if msg is None:
                raise HTTPException(
                    status_code=400,
                    detail="El mensaje fuente vinculado a la solicitud no existe en este proyecto."
                )

        # 4. Crear el registro HelpRequest en estado 'pending'
        help_request = HelpRequest(
            project_id=project_id,
            requester_id=requester.id,
            source_message_id=source_message_id,
            status="pending",
            idempotency_key=idempotency_key,
            context_revision=context_revision,
            created_at=datetime.now(timezone.utc)
        )
        db.add(help_request)
        await db.flush()
        await db.refresh(help_request)
        return help_request, True

    @staticmethod
    async def get_help_request(
        db: AsyncSession,
        project_id: UUID,
        help_request_id: UUID
    ) -> HelpRequest:
        req = await db.scalar(
            select(HelpRequest).where(
                HelpRequest.id == help_request_id,
                HelpRequest.project_id == project_id
            )
        )
        if req is None:
            raise HTTPException(status_code=404, detail="Solicitud de ayuda no encontrada.")
        return req

    @staticmethod
    async def update_help_request_status(
        db: AsyncSession,
        help_request: HelpRequest,
        status: str,
        response_message_id: Optional[UUID] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> HelpRequest:
        help_request.status = status
        if response_message_id:
            help_request.response_message_id = response_message_id
        if error_code:
            help_request.error_code = error_code
        if error_message:
            help_request.error_message = error_message
        if status in ("completed", "failed"):
            help_request.completed_at = datetime.now(timezone.utc)

        await db.flush()
        await db.refresh(help_request)
        return help_request
