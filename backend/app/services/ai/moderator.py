import logging
from typing import Optional, List, Dict, Any
from app.models.canvas import CanvasSnapshot
from app.services.ai.provider import AIProvider, GeminiProvider
from app.services.ai.prompts import SENIOR_DEVELOPER_SYSTEM_INSTRUCTION
from app.services.ai.context_service import ContextService, UMLContextResult

logger = logging.getLogger(__name__)


def summarize_uml_model(snapshot: Optional[CanvasSnapshot]) -> str:
    """Conserva compatibilidad retroactiva delegando en ContextService."""
    result = ContextService.build_uml_context(snapshot)
    return result.formatted_context


class AIModerator:
    """
    Coordina la generación de respuestas de asistencia técnica actuando como Desarrollador Senior.
    Integra el estado autorizado del diagrama UML y el historial acotado de conversación.
    """

    def __init__(self, provider: Optional[AIProvider] = None):
        self.provider = provider or GeminiProvider()

    async def answer_help_request(
        self,
        requester_name: str,
        user_prompt: str,
        snapshot: Optional[CanvasSnapshot],
        history: Optional[List[Dict[str, Any]]] = None,
        expected_version: Optional[int] = None
    ) -> str:
        # 1. Compilar contexto estructurado con priorización inteligente
        uml_result: UMLContextResult = ContextService.build_uml_context(
            snapshot=snapshot,
            user_prompt=user_prompt
        )

        # 2. Comprobar concurrencia: si la versión cambió respecto a la esperada
        concurrency_notice = ""
        if expected_version is not None and snapshot is not None and snapshot.version != expected_version:
            concurrency_notice = (
                f"\n\n[NOTA DE CONCURRENCIA: El lienzo fue modificado a la versión {snapshot.version} "
                f"mientras se procesaba la solicitud (versión inicial solicitada: {expected_version}). "
                f"Informa al desarrollador que tu respuesta se basa en la versión {snapshot.version}.]"
            )

        warnings_note = ""
        if uml_result.warnings:
            warnings_note = f"\n[ADVERTENCIAS DE CONTEXTO: {'; '.join(uml_result.warnings)}]"

        # 3. Formular prompt seguro con instrucciones de rol y datos delimitados
        prompt_with_requester = (
            f"El desarrollador '{requester_name}' ha solicitado tu ayuda técnica con la siguiente consulta:\n"
            f"«{user_prompt}»\n\n"
            f"Dirígete directamente a {requester_name}. Aplica el contexto del modelo provisto (versión {uml_result.diagram_version})."
            f"{warnings_note}{concurrency_notice}"
        )

        result = await self.provider.generate_advice(
            system_instruction=SENIOR_DEVELOPER_SYSTEM_INSTRUCTION,
            user_prompt=prompt_with_requester,
            uml_context=uml_result.formatted_context,
            history=history
        )
        return str(result)
