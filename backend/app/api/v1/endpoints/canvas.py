from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import current_user
from app.core.database import get_db
from app.models.canvas import CanvasSnapshot
from app.models.user import User
from app.schemas.uml import UMLCanvasDiagram
from app.services.projects import project_access
from app.services.canvas import document
from app.services.websocket.connection_manager import manager
from app.services.websocket.reservations import affected_classes

router = APIRouter(prefix='/projects', tags=['Lienzo UML'])


@router.get('/{project_id}/canvas', response_model=UMLCanvasDiagram)
async def read_canvas(project_id: UUID, db: AsyncSession = Depends(get_db, scope="function"),
                      user: User = Depends(current_user)):
    await project_access(db, project_id, user)
    snapshot = await db.scalar(select(CanvasSnapshot).where(CanvasSnapshot.project_id == project_id))
    if snapshot is None:
        raise HTTPException(404, 'Este proyecto no tiene lienzo inicial')
    return document(snapshot)


@router.put('/{project_id}/canvas', response_model=UMLCanvasDiagram)
async def save_canvas(project_id: UUID, data: UMLCanvasDiagram,
                      db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(current_user),
                      x_collaboration_session: UUID | None = Header(default=None)):
    async with manager.lock(project_id):
        result = await _save_canvas(project_id, data, db, user, x_collaboration_session)
        # Commit before releasing the same mutex used by reservation grants and WS.
        await db.commit()
        return result


async def _save_canvas(project_id, data, db, user, session_id):
    # Comparte el bloqueo con cambios de miembros: la autorización y escritura se ordenan.
    await project_access(db, project_id, user, {'OWNER', 'EDITOR'}, lock=True)
    payload = data.model_dump(mode='json')
    snapshot = await db.scalar(select(CanvasSnapshot).where(CanvasSnapshot.project_id == project_id))
    if snapshot is None:
        raise HTTPException(404, 'Este proyecto no tiene lienzo inicial')
    owner = next((p.id for p in manager.rooms.get(project_id, ())
                  if p.id == str(session_id) and p.user_id == str(user.id) and p.role != 'VIEWER'), None)
    manager.reservations.check(project_id,
        affected_classes(document(snapshot).model_dump(mode='json'), payload), owner)
    result = await db.execute(update(CanvasSnapshot).where(
        CanvasSnapshot.project_id == project_id, CanvasSnapshot.version == data.version,
    ).values(nodes=payload['nodes'], edges=payload['edges'],
             metadata_info={**payload['metadata'], 'schema_version': data.schema_version},
             version=CanvasSnapshot.version + 1).returning(CanvasSnapshot.version))
    version = result.scalar_one_or_none()
    if version is None:
        current = await db.scalar(select(CanvasSnapshot.version).where(CanvasSnapshot.project_id == project_id))
        if current is None:
            raise HTTPException(404, 'Este proyecto no tiene lienzo inicial')
        raise HTTPException(409, {'message': 'El diagrama cambió. Recarga la versión del servidor antes de guardar.',
                                  'current_version': current})
    return data.model_copy(update={'version': version})
