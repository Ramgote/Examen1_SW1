import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TriggerDecision:
    should_trigger: bool
    cleaned_prompt: str
    reason: str
    is_explicit: bool = True


class TriggerPolicy:
    """
    Decide cuándo se debe invocar a la IA.
    En el MVP, la política es estrictamente REACTIVA:
    Solo se activa ante mención explícita (@IA) o cuando se solicita ayuda expresamente (botón).
    """
    MENTION_PATTERN = re.compile(r'(?i)(?:^|\s)@ia(?:\b|[:,\s])')

    @classmethod
    def evaluate(cls, content: str, explicit_help_requested: bool = False) -> TriggerDecision:
        text = (content or "").strip()
        has_mention = bool(cls.MENTION_PATTERN.search(text))

        if not has_mention and not explicit_help_requested:
            return TriggerDecision(
                should_trigger=False,
                cleaned_prompt=text,
                reason="Conversación ordinaria entre miembros; sin solicitud explícita ni mención @IA.",
                is_explicit=False
            )

        # Limpiar la mención @IA y normalizar espacios múltiples
        replaced = cls.MENTION_PATTERN.sub(' ', text)
        cleaned = re.sub(r'\s+', ' ', replaced).strip()
        # Si quedó vacío (solo decía "@IA"), conservar texto base
        if not cleaned:
            cleaned = "Por favor, revisa el estado actual del diagrama y ofrece recomendaciones como desarrollador senior."

        reason = "Mención explícita @IA" if has_mention else "Solicitud explícita de ayuda (botón)"
        return TriggerDecision(
            should_trigger=True,
            cleaned_prompt=cleaned,
            reason=reason,
            is_explicit=True
        )

    @classmethod
    def evaluate_proactive(cls, project_id, recent_messages, diagram_snapshot) -> Optional[dict]:
        """
        Punto de extensión futuro para la fase proactiva.
        En el MVP siempre retorna None (moderación pasiva).
        """
        return None
