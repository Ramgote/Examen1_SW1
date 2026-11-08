from datetime import datetime, timezone
from typing import Optional, List, Tuple
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chat import ChatMessage


class MessageService:
    @staticmethod
    async def create_message(
        db: AsyncSession,
        project_id: UUID,
        author_id: Optional[UUID],
        author_type: str,
        author_name: str,
        content: str,
        reply_to_message_id: Optional[UUID] = None
    ) -> ChatMessage:
        # Si tiene referencia a mensaje previo, verificar que pertenezca al mismo proyecto (aislamiento estricto)
        if reply_to_message_id:
            referenced = await db.scalar(
                select(ChatMessage).where(
                    ChatMessage.id == reply_to_message_id,
                    ChatMessage.project_id == project_id
                )
            )
            if referenced is None:
                raise HTTPException(
                    status_code=400,
                    detail="El mensaje al que intentas responder no existe en este proyecto."
                )

        message = ChatMessage(
            project_id=project_id,
            author_id=author_id,
            author_type=author_type,
            author_name=author_name,
            content=content.strip(),
            reply_to_message_id=reply_to_message_id,
            created_at=datetime.now(timezone.utc)
        )
        db.add(message)
        await db.flush()
        await db.refresh(message)
        return message

    @staticmethod
    async def get_messages(
        db: AsyncSession,
        project_id: UUID,
        limit: int = 50,
        before: Optional[datetime] = None
    ) -> Tuple[List[ChatMessage], int, bool]:
        limit = max(1, min(limit, 100))

        # Conteo total en el proyecto
        total = await db.scalar(
            select(func.count(ChatMessage.id)).where(ChatMessage.project_id == project_id)
        ) or 0

        query = select(ChatMessage).where(ChatMessage.project_id == project_id)
        if before:
            query = query.where(ChatMessage.created_at < before)

        # Consultar los más recientes primero para la página solicitada
        query = query.order_by(desc(ChatMessage.created_at)).limit(limit + 1)
        result = await db.scalars(query)
        fetched = list(result)

        has_more = len(fetched) > limit
        page_messages = fetched[:limit]

        # Retornar en orden cronológico ascendente para renderizado natural del chat
        page_messages.reverse()
        return page_messages, total, has_more
