from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.canvas import CanvasSnapshot
from app.schemas.ai import AssistantRequest
from app.services.projects import project_access
from app.services.canvas import document
from app.services.ai import gemini
from app.services.ai.limits import limits
from app.services.ai.vision_service import MAX_BODY, decode_attachments
from app.services.ai.tool_caller import build_preview

router = APIRouter(prefix='/projects', tags=['Asistente multimodal'])


@router.get('/{project_id}/assistant/status')
async def status(project_id: UUID, response: Response,
                 db: AsyncSession = Depends(get_db, scope='function'), user: User = Depends(current_user)):
    _, role = await project_access(db, project_id, user)
    response.headers['Cache-Control'] = 'no-store'
    return {'configured': bool(settings.GEMINI_API_KEY.strip()), 'provider': 'Gemini',
            'model': settings.GEMINI_MODEL, 'can_edit': role in {'OWNER', 'EDITOR'}}


@router.post('/{project_id}/assistant/preview')
async def preview(project_id: UUID, request: Request, response: Response,
                  db: AsyncSession = Depends(get_db, scope='function'), user: User = Depends(current_user)):
    await project_access(db, project_id, user, {'OWNER', 'EDITOR'})
    user_id = user.id
    if request.headers.get('content-type', '').split(';')[0].strip() != 'application/json':
        raise HTTPException(415, 'Envía una solicitud JSON con texto y adjuntos base64.')
    with limits.claim(user_id):
        raw = bytearray()
        async for chunk in request.stream():
            if len(raw) + len(chunk) > MAX_BODY:
                raise HTTPException(413, 'La solicitud supera 12 MiB.')
            raw.extend(chunk)
        try:
            body = AssistantRequest.model_validate_json(raw)
        except ValidationError:
            raise HTTPException(422, 'Solicitud inválida: texto hasta 8000 caracteres, hasta tres imágenes y un audio, y versión válida.') from None
        media = decode_attachments(body.attachments)
        snapshot = await db.scalar(select(CanvasSnapshot).where(CanvasSnapshot.project_id == project_id))
        if snapshot is None:
            raise HTTPException(404, 'Lienzo no encontrado')
        if snapshot.version != body.expected_version:
            raise HTTPException(409, 'El diagrama cambió. Sincroniza antes de consultar al asistente.')
        original = document(snapshot)
        proposal = await gemini.propose(original, body.prompt, media)
        # Recheck membership and version after the external wait; no writes or locks.
        db.expire_all()
        current = await db.get(User, user_id)
        if current is None or not current.is_active:
            raise HTTPException(401, 'Sesión inválida o vencida')
        await project_access(db, project_id, current, {'OWNER', 'EDITOR'})
        version = await db.scalar(select(CanvasSnapshot.version).where(CanvasSnapshot.project_id == project_id))
        if version != body.expected_version:
            raise HTTPException(409, 'Otro participante cambió el diagrama durante la consulta. Revisa el lienzo y vuelve a solicitar la propuesta.')
        result = build_preview(original, proposal)
        response.headers['Cache-Control'] = 'no-store'
        return result
