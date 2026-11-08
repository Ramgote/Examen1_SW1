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
from app.schemas.ai import AssistantRequest, HelpChatRequest, HelpChatResponse
from app.services.projects import project_access
from app.services.canvas import document
from app.services.ai import gemini
from app.services.ai.limits import limits
from app.services.ai.vision_service import MAX_BODY, decode_attachments
from app.services.ai.tool_caller import build_preview
from google import genai
from google.genai import types, errors
import asyncio

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
        if body.history:
            proposal = await gemini.propose(original, body.prompt, media, history=body.history)
        else:
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


HELP_SYSTEM_INSTRUCTION = """Eres el asistente oficial de orientación de UML Studio 2.5, una plataforma CASE para modelado UML colaborativo. Tu única función es enseñar a utilizar la interfaz y explicar las funciones del software. Responde siempre en español claro, con pasos numerados cuando corresponda.

Conoces estas áreas: barra superior con Inicio, Diagrama, Modelado, Intercambio XMI, Generación Código, Asistente IA y Chat & Senior Dev; Explorador de Paquetes y Elementos de Clase/Relaciones en el panel izquierdo; lienzo central con herramientas de selección, mano, conexión, organizar, snap y zoom; Inspector de Propiedades a la derecha; colaboración en vivo, reservas, guardado y sincronización; importación/exportación XMI; validación y generación de proyectos Spring Boot y Flutter.

Crear una clase: Elementos de clase > Clase; seleccionar la clase; revisar nombre, paquete, atributos y métodos en Inspector. Crear relaciones: elegir tipo de relación en Class Relationships y conectar las clases en el lienzo. XMI: permite importar/exportar; aplicar una importación reemplaza el modelo actual, por eso debe revisarse la vista previa. Generación: validar primero el modelo, corregir errores y revisar advertencias. Colaboración: respetar reservas, permisos y sincronización.

Reglas de seguridad: NUNCA afirmes que puedes modificar, guardar, borrar, sincronizar o ejecutar acciones en nombre del usuario. Este endpoint es solo de consulta y no recibe ni modifica el diagrama. No inventes botones, menús ni capacidades. Si una función específica no está confirmada en este contexto, dilo claramente y orienta al usuario a consultar la interfaz. No confundas este asistente de ayuda con el Asistente IA que propone cambios UML ni con Chat & Senior Dev. Mantén las respuestas prácticas y concisas."""


@router.post('/{project_id}/assistant/help', response_model=HelpChatResponse)
async def help_chat(project_id: UUID, body: HelpChatRequest,
                    db: AsyncSession = Depends(get_db, scope='function'),
                    user: User = Depends(current_user)):
    await project_access(db, project_id, user)
    if not settings.GEMINI_API_KEY.strip():
        raise HTTPException(503, 'El asistente de orientación requiere GEMINI_API_KEY en backend/.env.')
    with limits.claim(user.id):
        try:
            async with genai.Client(api_key=settings.GEMINI_API_KEY,
                    http_options=types.HttpOptions(timeout=settings.AI_TIMEOUT_SECONDS * 1000,
                                                  retry_options=types.HttpRetryOptions(attempts=1))).aio as client:
                async with asyncio.timeout(settings.AI_TIMEOUT_SECONDS):
                    result = await client.models.generate_content(
                        model=settings.GEMINI_MODEL,
                        contents=body.question,
                        config=types.GenerateContentConfig(
                            system_instruction=HELP_SYSTEM_INSTRUCTION,
                            temperature=0.25,
                            max_output_tokens=1200,
                        ),
                    )
            answer = (result.text or '').strip()
            if not answer:
                raise HTTPException(502, 'El asistente no devolvió una explicación. Intenta nuevamente.')
            return HelpChatResponse(answer=answer[:5000])
        except TimeoutError:
            raise HTTPException(504, 'El asistente tardó demasiado. Intenta nuevamente.') from None
        except errors.APIError as exc:
            if exc.code == 429:
                raise HTTPException(429, 'Se alcanzó temporalmente el límite de consultas de Gemini.') from None
            if exc.code in (401, 403):
                raise HTTPException(503, 'Gemini rechazó la clave API. Revisa GEMINI_API_KEY.') from None
            raise HTTPException(502, 'Gemini no pudo responder en este momento.') from None
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(502, 'No se pudo conectar con el asistente. Intenta más tarde.') from None
