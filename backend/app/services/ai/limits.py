"""Bound concurrency and per-user request rate for the single-worker deployment."""
from collections import OrderedDict, deque
from contextlib import contextmanager
from time import monotonic
from fastapi import HTTPException


class AssistantLimits:
    def __init__(self):
        self.active = set()
        self.requests = OrderedDict()

    @contextmanager
    def claim(self, user_id):
        now = monotonic()
        if user_id in self.active or len(self.active) >= 4:
            raise HTTPException(429, 'El asistente está ocupado. Espera a que termine la solicitud actual.')
        times = self.requests.setdefault(user_id, deque())
        while times and now - times[0] >= 60:
            times.popleft()
        if len(times) >= 6:
            raise HTTPException(429, 'Máximo seis solicitudes por minuto. Espera antes de volver a enviar.')
        times.append(now)
        self.requests.move_to_end(user_id)
        while len(self.requests) > 1024:
            self.requests.popitem(last=False)
        self.active.add(user_id)
        try:
            yield
        finally:
            self.active.discard(user_id)


limits = AssistantLimits()
