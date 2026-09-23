from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool
from app.api.deps import current_user
from app.core.database import get_db
from app.models.user import User
from app.models.canvas import CanvasSnapshot
from app.schemas.generation import SpringGenerationRequest
from app.services.projects import project_access
from app.services.canvas import document
from app.services.generator.ast_transformer import transform, GenerationError
from app.services.generator.packager import generate_spring, generate_solution

router = APIRouter(prefix='/projects', tags=['Generación Spring Boot y Flutter'])


async def saved_model(project_id, expected_version, db, user):
    await project_access(db, project_id, user)
    snapshot = await db.scalar(select(CanvasSnapshot).where(CanvasSnapshot.project_id == project_id))
    if snapshot is None:
        raise HTTPException(404, 'Lienzo no encontrado')
    if snapshot.version != expected_version:
        raise HTTPException(409, 'El diagrama cambió. Sincroniza y vuelve a validar antes de generar.')
    return document(snapshot)


@router.post('/{project_id}/generate/spring/validate')
async def validate_spring(project_id: UUID, body: SpringGenerationRequest,
                          db: AsyncSession = Depends(get_db, scope='function'), user: User = Depends(current_user)):
    model = await saved_model(project_id, body.expected_version, db, user)
    try:
        plan = await run_in_threadpool(transform, model)
    except GenerationError as exc:
        return {'valid': False, 'version': model.version, 'errors': exc.errors, 'warnings': []}
    return {'valid': True, 'version': model.version, 'errors': [], 'warnings': plan['warnings'],
            'classes': len(plan['classes'])}


@router.post('/{project_id}/generate/spring', response_class=Response)
async def download_spring(project_id: UUID, body: SpringGenerationRequest,
                          db: AsyncSession = Depends(get_db, scope='function'), user: User = Depends(current_user)):
    model = await saved_model(project_id, body.expected_version, db, user)
    try:
        raw, _ = await run_in_threadpool(generate_spring, model)
    except GenerationError as exc:
        raise HTTPException(422, detail={'message': 'Modelo incompatible con el perfil Spring', 'errors': exc.errors}) from None
    return Response(raw, media_type='application/zip', headers={
        'Content-Disposition': f'attachment; filename="spring-{project_id}-v{model.version}.zip"',
        'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})


@router.post('/{project_id}/generate/solution/validate')
async def validate_solution(project_id: UUID, body: SpringGenerationRequest,
                            db: AsyncSession = Depends(get_db, scope='function'), user: User = Depends(current_user)):
    model = await saved_model(project_id, body.expected_version, db, user)
    try:
        _, warnings = await run_in_threadpool(generate_solution, model, project_id)
    except GenerationError as exc:
        return {'valid': False, 'version': model.version, 'errors': exc.errors, 'warnings': []}
    return {'valid': True, 'version': model.version, 'errors': [], 'warnings': warnings,
            'artifacts': ['Spring Boot', 'Flutter Android'], 'local_stt': False}


@router.post('/{project_id}/generate/solution', response_class=Response)
async def download_solution(project_id: UUID, body: SpringGenerationRequest,
                            db: AsyncSession = Depends(get_db, scope='function'), user: User = Depends(current_user)):
    model = await saved_model(project_id, body.expected_version, db, user)
    try:
        raw, _ = await run_in_threadpool(generate_solution, model, project_id)
    except GenerationError as exc:
        raise HTTPException(422, detail={'message': 'Modelo incompatible', 'errors': exc.errors}) from None
    return Response(raw, media_type='application/zip', headers={
        'Content-Disposition': f'attachment; filename="solution-{project_id}-v{model.version}.zip"',
        'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
