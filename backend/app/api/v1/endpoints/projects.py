from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import current_user
from app.core.database import get_db
from app.models.canvas import CanvasSnapshot
from app.models.project import Project, ProjectCollaborator
from app.models.user import User
from app.schemas.project import MemberInput, MemberRead, ProjectInput, ProjectRead
from app.services.projects import project_access, project_read

router = APIRouter(prefix="/projects", tags=["Proyectos"])


@router.get("", response_model=list[ProjectRead])
async def list_projects(offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100),
                        db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(current_user)):
    rows = (await db.execute(select(Project, ProjectCollaborator.role).outerjoin(
        ProjectCollaborator, (ProjectCollaborator.project_id == Project.id) &
        (ProjectCollaborator.user_id == user.id)).where(or_(
        Project.owner_id == user.id, ProjectCollaborator.user_id == user.id
    )).order_by(Project.created_at.desc(), Project.id).offset(offset).limit(limit))).all()
    return [project_read(p, "OWNER" if p.owner_id == user.id else
                         (r if r in ("EDITOR", "VIEWER") else "VIEWER")) for p, r in rows]


@router.post("", response_model=ProjectRead, status_code=201)
async def create_project(data: ProjectInput, db: AsyncSession = Depends(get_db, scope="function"),
                         user: User = Depends(current_user)):
    project = Project(**data.model_dump(), owner_id=user.id)
    db.add(project)
    await db.flush()
    db.add(CanvasSnapshot(project_id=project.id))
    await db.flush()
    return project_read(project, "OWNER")


@router.get("/{project_id}", response_model=ProjectRead)
async def read_project(project_id: UUID, db: AsyncSession = Depends(get_db, scope="function"),
                       user: User = Depends(current_user)):
    return project_read(*await project_access(db, project_id, user))


@router.put("/{project_id}", response_model=ProjectRead)
async def update_project(project_id: UUID, data: ProjectInput,
                         db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(current_user)):
    project, role = await project_access(db, project_id, user, {"OWNER", "EDITOR"}, lock=True)
    project.name, project.description = data.name, data.description
    await db.flush()
    return project_read(project, role)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: UUID, db: AsyncSession = Depends(get_db, scope="function"),
                         user: User = Depends(current_user)):
    await project_access(db, project_id, user, {"OWNER"}, lock=True)
    await db.execute(delete(Project).where(Project.id == project_id))
    return Response(status_code=204)


@router.get("/{project_id}/members", response_model=list[MemberRead])
async def members(project_id: UUID, db: AsyncSession = Depends(get_db, scope="function"),
                  user: User = Depends(current_user)):
    project, _ = await project_access(db, project_id, user, {"OWNER"})
    owner = await db.get(User, project.owner_id)
    result = [MemberRead(user_id=owner.id, email=owner.email, full_name=owner.full_name, role="OWNER")]
    rows = (await db.execute(select(User, ProjectCollaborator.role).join(
        ProjectCollaborator, ProjectCollaborator.user_id == User.id).where(
        ProjectCollaborator.project_id == project_id, User.id != owner.id))).all()
    return result + [MemberRead(user_id=u.id, email=u.email, full_name=u.full_name,
                               role=r if r in ("EDITOR", "VIEWER") else "VIEWER") for u, r in rows]


@router.put("/{project_id}/members", response_model=MemberRead)
async def set_member(project_id: UUID, data: MemberInput,
                     db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(current_user)):
    project, _ = await project_access(db, project_id, user, {"OWNER"}, lock=True)
    member_user = await db.scalar(select(User).where(User.email == data.email, User.is_active.is_(True)))
    if member_user is None:
        raise HTTPException(404, "El usuario debe registrarse primero")
    if member_user.id == project.owner_id:
        raise HTTPException(409, "El propietario no puede cambiar su rol")
    member = await db.get(ProjectCollaborator, (project.id, member_user.id))
    if member is None:
        db.add(ProjectCollaborator(project_id=project.id, user_id=member_user.id, role=data.role))
    else:
        member.role = data.role
    await db.flush()
    return MemberRead(user_id=member_user.id, email=member_user.email,
                      full_name=member_user.full_name, role=data.role)


@router.delete("/{project_id}/members/{user_id}", status_code=204)
async def remove_member(project_id: UUID, user_id: UUID,
                        db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(current_user)):
    project, _ = await project_access(db, project_id, user, {"OWNER"}, lock=True)
    if user_id == project.owner_id:
        raise HTTPException(409, "No se puede retirar al propietario")
    await db.execute(delete(ProjectCollaborator).where(
        ProjectCollaborator.project_id == project_id, ProjectCollaborator.user_id == user_id))
    return Response(status_code=204)
