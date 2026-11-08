from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chat import ModeratorSettings


class ModeratorSettingsService:
    @staticmethod
    async def get_or_create(db: AsyncSession, project_id: UUID) -> ModeratorSettings:
        settings = await db.scalar(
            select(ModeratorSettings).where(ModeratorSettings.project_id == project_id)
        )
        if settings is None:
            settings = ModeratorSettings(
                project_id=project_id,
                mode="reactive",
                require_human_approval=True,
                updated_at=datetime.now(timezone.utc)
            )
            db.add(settings)
            await db.flush()
            await db.refresh(settings)
        return settings

    @staticmethod
    async def update(
        db: AsyncSession,
        project_id: UUID,
        mode: Optional[str] = None,
        require_human_approval: Optional[bool] = None
    ) -> ModeratorSettings:
        settings = await ModeratorSettingsService.get_or_create(db, project_id)
        if mode is not None:
            settings.mode = mode
        if require_human_approval is not None:
            settings.require_human_approval = require_human_approval
        settings.updated_at = datetime.now(timezone.utc)

        await db.flush()
        await db.refresh(settings)
        return settings
