from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.project import Project, ProjectCollaborator
from app.models.user import User
from app.schemas.project import ProjectRead


async def project_access(db: AsyncSession, project_id: UUID, user: User,
                         roles=None, lock=False):
    query = select(Project).where(Project.id == project_id)
    if lock:
        query = query.with_for_update()
    project = await db.scalar(query)
    if project is None:
        raise HTTPException(404, "Proyecto no encontrado")
    if project.owner_id == user.id:
        role = "OWNER"
    else:
        member = await db.get(ProjectCollaborator, (project.id, user.id))
        if member is None:
            raise HTTPException(404, "Proyecto no encontrado")
        # Un OWNER legado en membresías nunca concede privilegios de propietario.
        role = member.role if member.role in ("EDITOR", "VIEWER") else "VIEWER"
    if roles and role not in roles:
        raise HTTPException(403, "No tienes permiso para esta operación")
    return project, role


def project_read(project, role):
    return ProjectRead(id=project.id, name=project.name, description=project.description,
                       owner_id=project.owner_id, role=role,
                       created_at=project.created_at, updated_at=project.updated_at)
