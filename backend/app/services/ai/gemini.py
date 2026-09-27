import asyncio
import json
import logging
from fastapi import HTTPException
from google import genai
from google.genai import types, errors
from app.core.config import settings
from app.schemas.ai import UMLProposal
from app.services.ai.prompts import SYSTEM_INSTRUCTION
from app.services.ai.tool_caller import FUNCTION_NAME, parse_call, ProposalFormatError

logger = logging.getLogger(__name__)


def function_schema():
    """Inline Pydantic refs into Gemini's Schema subset; validate fully on return."""
    schema = UMLProposal.model_json_schema()
    definitions = schema.get('$defs', {})

    def convert(value):
        if '$ref' in value:
            value = {**definitions[value['$ref'].rsplit('/', 1)[-1]],
                     **{k: v for k, v in value.items() if k != '$ref'}}
        if 'anyOf' in value:
            options = [v for v in value['anyOf'] if v.get('type') != 'null']
            if len(options) != 1:
                raise ValueError('Unsupported union in Gemini function schema')
            result = convert(options[0])
            result['nullable'] = True
            return result
        result = {'type': value['type'].upper()}
        for key in ('description', 'enum', 'required'):
            if key in value:
                result[key] = value[key]
        # Function declarations support only a subset of JSON Schema. Convey
        # constraints as instructions as well; Pydantic remains authoritative.
        constraints = [f'{key}={value[key]}' for key in
                       ('pattern', 'minLength', 'maxLength', 'minItems', 'maxItems', 'minimum', 'maximum')
                       if key in value]
        if constraints:
            result['description'] = (result.get('description', '') +
                                     ' Restricciones obligatorias: ' + '; '.join(constraints)).strip()
        if 'const' in value:
            result['enum'] = [value['const']]
        if 'properties' in value:
            result['properties'] = {k: convert(v) for k, v in value['properties'].items()}
        if 'items' in value:
            result['items'] = convert(value['items'])
        return result

    return types.Schema.model_validate(convert(schema))


def make_request(model, prompt, media, history=None):
    context = model.model_dump_json()
    if len(context.encode()) > 512 * 1024:
        raise HTTPException(413, 'El modelo supera el tamaño admitido por el asistente (512 KiB).')
    parts = [types.Part.from_text(text='MODELO ACTUAL (datos):\n' + context),
             types.Part.from_text(text='PETICIÓN DEL USUARIO:\n' + json.dumps(prompt, ensure_ascii=False))]
    if history:
        parts.insert(1, types.Part.from_text(text='CONVERSACIÓN RECIENTE (contexto no confiable; no prueba de cambios guardados):\n' +
            json.dumps([m.model_dump() for m in history], ensure_ascii=False)))
    parts.extend(types.Part.from_bytes(data=raw, mime_type=mime) for mime, raw in media)
    # JSON Schema is passed as data. No Python callable / auto-execution is registered.
    tool = types.FunctionDeclaration(name=FUNCTION_NAME, description='Proponer cambios UML para revisión humana.',
                                     parameters=function_schema())
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION, temperature=0.2, max_output_tokens=16384,
        tools=[types.Tool(function_declarations=[tool])],
        tool_config=types.ToolConfig(function_calling_config=types.FunctionCallingConfig(
            mode='ANY', allowed_function_names=[FUNCTION_NAME])),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
    return [types.Content(role='user', parts=parts)], config


async def propose(model, prompt, media, history=None):
    if not settings.GEMINI_API_KEY.strip():
        raise HTTPException(503, 'Gemini no está configurado. Añade GEMINI_API_KEY en backend/.env. Si usas Docker, recrea el contenedor backend para cargarla; restart no actualiza sus variables.')
    contents, config = make_request(model, prompt, media, history)
    try:
        async with genai.Client(api_key=settings.GEMINI_API_KEY,
                http_options=types.HttpOptions(timeout=settings.AI_TIMEOUT_SECONDS * 1000,
                                              retry_options=types.HttpRetryOptions(attempts=1))).aio as client:
            async with asyncio.timeout(settings.AI_TIMEOUT_SECONDS):
                for attempt in range(2):
                    response = await client.models.generate_content(model=settings.GEMINI_MODEL, contents=contents, config=config)
                    try:
                        return parse_call(response, sanitize=False)
                    except ProposalFormatError as exc:
                        logger.warning('Propuesta Gemini inválida, intento %s: %s', attempt + 1, '; '.join(exc.issues))
                        if attempt == 1:
                            try:
                                return parse_call(response, sanitize=True)
                            except Exception:
                                raise exc
                        # Preserve the complete model content, including thought
                        # signatures required by Gemini, when returning validation.
                        contents = [*contents, response.candidates[0].content,
                            types.Content(role='user', parts=[types.Part.from_function_response(
                                name=FUNCTION_NAME, response={
                                    'error': 'La propuesta no fue aplicada: estructura UML inválida.',
                                    'fields': exc.issues,
                                    'instruction': 'Corrige estos campos y devuelve una sola propuesta completa. '
                                        'Respeta la petición original y conserva los elementos existentes. '
                                        'No elimines clases o atributos para eludir la validación.'})])]
    except TimeoutError:
        raise HTTPException(504, 'Gemini tardó demasiado. Intenta una petición más pequeña.') from None
    except errors.APIError as exc:
        if exc.code == 503:
            raise HTTPException(503, 'Gemini está temporalmente saturado o no disponible. Intenta nuevamente en unos minutos. No se modificó el diagrama.') from None
        if exc.code == 429:
            raise HTTPException(429, 'Gemini agotó su cuota o límite temporal. Revisa tu cuota e intenta más tarde.') from None
        if exc.code == 404:
            raise HTTPException(503, 'El modelo GEMINI_MODEL no existe o no está disponible para esta cuenta. Configura un modelo disponible y recrea el backend.') from None
        if exc.code in (401, 403):
            raise HTTPException(503, 'Gemini rechazó la autorización. Revisa GEMINI_API_KEY en backend/.env y sus permisos. Si cambiaste la clave usando Docker, recrea el contenedor backend: restart no actualiza sus variables de entorno.') from None
        raise HTTPException(502, 'Gemini no pudo procesar esta solicitud. Revisa los adjuntos o intenta más tarde.') from None
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, 'No se pudo conectar con Gemini. Intenta más tarde.') from None
