from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from starlette.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import current_user
from app.core.database import get_db
from app.models.user import User
from app.models.canvas import CanvasSnapshot
from app.services.projects import project_access
from app.services.canvas import document
from app.services.xmi.parser import parse_xmi
from app.services.xmi.serializer import serialize_xmi
from app.services.xmi.ea_serializer import serialize_ea_xmi
from app.services.xmi.common import MAX_BYTES, XMIError

router = APIRouter(prefix='/projects', tags=['Intercambio XMI'])


@router.get('/{project_id}/xmi', response_class=Response)
async def export_xmi(project_id: UUID, db: AsyncSession = Depends(get_db, scope='function'),
                     user: User = Depends(current_user), format: Literal['standard', 'ea15', 'ea17'] = 'ea17'):
    project, _ = await project_access(db, project_id, user)
    snapshot = await db.scalar(select(CanvasSnapshot).where(CanvasSnapshot.project_id == project_id))
    if snapshot is None:
        raise HTTPException(404, 'Lienzo no encontrado')
    try:
        raw = (await run_in_threadpool(serialize_ea_xmi, document(snapshot), project.id, project.name)
               if format in {'ea15', 'ea17'} else await run_in_threadpool(serialize_xmi, document(snapshot)))
    except XMIError as exc:
        raise HTTPException(422, str(exc)) from None
    except ValueError:
        raise HTTPException(422, 'El modelo contiene texto que no se puede representar en XML 1.0') from None
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, 'El modelo exportado supera el límite de intercambio de 4 MiB')
    return Response(raw, media_type='application/xml', headers={
        'Content-Disposition': f'attachment; filename="proyecto-{project_id}{"-" + format if format != "standard" else ""}.xmi"',
        'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})


@router.post('/{project_id}/xmi/preview')
async def preview_xmi(project_id: UUID, request: Request,
                      db: AsyncSession = Depends(get_db, scope='function'), user: User = Depends(current_user)):
    await project_access(db, project_id, user, {'OWNER', 'EDITOR'})
    if request.headers.get('content-type', '').split(';')[0].strip() not in {'application/xml', 'text/xml', 'application/octet-stream'}:
        raise HTTPException(415, 'Envía el contenido XML del archivo, no un formulario multipart')
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > MAX_BYTES:
            raise HTTPException(413, 'El archivo supera 4 MiB')
        raw.extend(chunk)
    try:
        imported, warnings = await run_in_threadpool(parse_xmi, bytes(raw))
    except XMIError as exc:
        raise HTTPException(422, str(exc)) from None
    snapshot = await db.scalar(select(CanvasSnapshot).where(CanvasSnapshot.project_id == project_id))
    if snapshot is None:
        raise HTTPException(404, 'Lienzo no encontrado')
    return {'document': imported.model_copy(update={'version': snapshot.version}), 'warnings': warnings,
            'summary': {'classes': len(imported.nodes), 'relationships': len(imported.edges),
                        'attributes': sum(len(n.data.attributes) for n in imported.nodes),
                        'methods': sum(len(n.data.methods) for n in imported.nodes)}}
