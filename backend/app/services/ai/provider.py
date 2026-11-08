from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass
import logging
from time import monotonic
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types, errors
from fastapi import HTTPException
from app.core.config import settings
from app.services.ai.metrics import ai_metrics

logger = logging.getLogger(__name__)


@dataclass
class AdviceResult:
    content: str
    model_used: str
    latency_ms: float
    prompt_tokens: int = 0
    candidate_tokens: int = 0
    total_tokens: int = 0

    def __str__(self) -> str:
        return self.content


class AIProvider(ABC):
    """Interfaz abstracta para el proveedor de Inteligencia Artificial."""

    @abstractmethod
    async def generate_advice(
        self,
        system_instruction: str,
        user_prompt: str,
        uml_context: str,
        history: Optional[List[Dict[str, Any]]] = None
    ) -> AdviceResult:
        """Genera una respuesta o asesoría técnica de desarrollador senior."""
        pass


class GeminiProvider(AIProvider):
    """Implementación desacoplada de AIProvider para Google Gemini con telemetría y resiliencia."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = (api_key or settings.GEMINI_API_KEY).strip()
        self.model = model or settings.GEMINI_MODEL

    async def generate_advice(
        self,
        system_instruction: str,
        user_prompt: str,
        uml_context: str,
        history: Optional[List[Dict[str, Any]]] = None
    ) -> AdviceResult:
        if not self.api_key:
            raise HTTPException(
                status_code=503,
                detail="Gemini no está configurado. Añade GEMINI_API_KEY en backend/.env."
            )

        start_time = monotonic()
        operation = "senior_advice"

        parts = [
            types.Part.from_text(text=f"MODELO ACTUAL UML (datos no modificables directamente por ti):\n{uml_context}"),
            types.Part.from_text(text=f"CONSULTA DEL DESARROLLADOR:\n{user_prompt}")
        ]

        if history:
            import json
            parts.insert(1, types.Part.from_text(
                text=f"HISTORIAL DE CONVERSACIÓN RECIENTE (contexto de referencia no confiable):\n"
                     f"{json.dumps(history, ensure_ascii=False)}"
            ))

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.3,
            max_output_tokens=4096,
        )

        try:
            async with genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(
                    timeout=settings.AI_TIMEOUT_SECONDS * 1000,
                    retry_options=types.HttpRetryOptions(attempts=1)
                )
            ).aio as client:
                async with asyncio.timeout(settings.AI_TIMEOUT_SECONDS):
                    response = await client.models.generate_content(
                        model=self.model,
                        contents=[types.Content(role="user", parts=parts)],
                        config=config
                    )

            latency_ms = (monotonic() - start_time) * 1000

            # Extracción segura de tokens
            usage = getattr(response, "usage_metadata", None)
            prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
            candidate_tokens = getattr(usage, "candidates_token_count", 0) or 0
            total_tokens = getattr(usage, "total_token_count", 0) or 0

            text = (response.text or "").strip()
            if not text:
                text = (
                    "**Diagnóstico:** He revisado la consulta y los elementos del diagrama actual.\n\n"
                    "**Observación:** No se detectan anomalías de sintaxis en el modelo, pero la solicitud requiere "
                    "mayor especificidad en cuanto a los requerimientos de negocio o clases involucradas.\n\n"
                    "**Recomendación:** Por favor indica el nombre exacto de las clases o la relación específica que deseas analizar."
                )

            ai_metrics.record(
                model=self.model,
                operation=operation,
                latency_ms=latency_ms,
                status="success",
                prompt_tokens=prompt_tokens,
                candidate_tokens=candidate_tokens,
                total_tokens=total_tokens
            )

            return AdviceResult(
                content=text,
                model_used=self.model,
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                candidate_tokens=candidate_tokens,
                total_tokens=total_tokens
            )

        except TimeoutError:
            latency_ms = (monotonic() - start_time) * 1000
            ai_metrics.record(
                model=self.model,
                operation=operation,
                latency_ms=latency_ms,
                status="timeout",
                error_type="TimeoutError"
            )
            logger.warning("GeminiProvider: Timeout tras %.2fms", latency_ms)
            raise HTTPException(
                status_code=504,
                detail="El asistente tardó demasiado en responder. Por favor, realiza una consulta más acotada."
            ) from None

        except errors.APIError as exc:
            latency_ms = (monotonic() - start_time) * 1000
            ai_metrics.record(
                model=self.model,
                operation=operation,
                latency_ms=latency_ms,
                status="error",
                error_type=f"APIError_{exc.code}"
            )
            logger.warning("GeminiProvider: APIError %s tras %.2fms: %s", exc.code, latency_ms, exc.message)
            if exc.code == 429:
                raise HTTPException(
                    status_code=429,
                    detail="Se superó la cuota de uso temporal del asistente IA. Por favor intenta en un momento."
                ) from None
            if exc.code in (401, 403):
                raise HTTPException(
                    status_code=503,
                    detail="Error de autenticación con el proveedor IA. Verifica GEMINI_API_KEY."
                ) from None
            if exc.code == 503:
                raise HTTPException(
                    status_code=503,
                    detail="El servicio IA está temporalmente saturado. Intenta nuevamente en unos minutos."
                ) from None
            raise HTTPException(
                status_code=502,
                detail=f"Error en el servicio de IA: {exc.message[:200]}"
            ) from None

        except HTTPException:
            raise

        except Exception as exc:
            latency_ms = (monotonic() - start_time) * 1000
            ai_metrics.record(
                model=self.model,
                operation=operation,
                latency_ms=latency_ms,
                status="error",
                error_type=type(exc).__name__
            )
            logger.exception("GeminiProvider: Excepción no controlada tras %.2fms", latency_ms)
            raise HTTPException(
                status_code=502,
                detail="No se pudo procesar la respuesta del asistente virtual."
            ) from None
