from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from time import monotonic
from typing import Optional, List, Dict, Any

logger = logging.getLogger("ai.telemetry")


@dataclass
class AIMetricRecord:
    timestamp: datetime
    model: str
    operation: str
    latency_ms: float
    status: str
    prompt_tokens: int = 0
    candidate_tokens: int = 0
    total_tokens: int = 0
    error_type: Optional[str] = None


class AIMetricsCollector:
    """
    Colector de métricas de latencia y uso del asistente IA en memoria.
    No almacena nunca claves de API, secretos ni contenido sensible de los usuarios.
    """
    def __init__(self, max_records: int = 500):
        self.max_records = max_records
        self.records: List[AIMetricRecord] = []

    def record(
        self,
        model: str,
        operation: str,
        latency_ms: float,
        status: str,
        prompt_tokens: int = 0,
        candidate_tokens: int = 0,
        total_tokens: int = 0,
        error_type: Optional[str] = None
    ) -> AIMetricRecord:
        entry = AIMetricRecord(
            timestamp=datetime.now(timezone.utc),
            model=model,
            operation=operation,
            latency_ms=round(latency_ms, 2),
            status=status,
            prompt_tokens=prompt_tokens,
            candidate_tokens=candidate_tokens,
            total_tokens=total_tokens,
            error_type=error_type
        )
        self.records.append(entry)
        if len(self.records) > self.max_records:
            self.records.pop(0)

        logger.info(
            "AI Telemetry [%s] op=%s status=%s latency=%.2fms tokens=%s error=%s",
            model, operation, status, latency_ms, total_tokens, error_type
        )
        return entry

    def get_summary(self) -> Dict[str, Any]:
        if not self.records:
            return {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "avg_latency_ms": 0.0,
                "total_tokens_consumed": 0,
            }

        total = len(self.records)
        successful = sum(1 for r in self.records if r.status == "success")
        failed = total - successful
        avg_lat = sum(r.latency_ms for r in self.records) / total
        tokens = sum(r.total_tokens for r in self.records)

        return {
            "total_calls": total,
            "successful_calls": successful,
            "failed_calls": failed,
            "avg_latency_ms": round(avg_lat, 2),
            "total_tokens_consumed": tokens,
            "last_recorded_at": self.records[-1].timestamp.isoformat() if self.records else None
        }


ai_metrics = AIMetricsCollector()
