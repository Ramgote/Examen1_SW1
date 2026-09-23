from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.schemas.uml import UMLCanvasDiagram


class Authenticate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    type: Literal['authenticate']
    token: str = Field(min_length=1, max_length=8192)


class Update(BaseModel):
    model_config = ConfigDict(extra='forbid')
    type: Literal['update']
    op_id: UUID
    base: UMLCanvasDiagram
    document: UMLCanvasDiagram

    @model_validator(mode='after')
    def same_version(self):
        if self.base.version != self.document.version:
            raise ValueError('El borrador y su base deben tener la misma versión')
        return self


class ReservationEvent(BaseModel):
    model_config = ConfigDict(extra='forbid')
    type: Literal['reserve', 'release']
    op_id: UUID
    node_ids: list[str] = Field(default_factory=list, max_length=200)

    @model_validator(mode='after')
    def valid_ids(self):
        if any(not value or len(value) > 100 for value in self.node_ids):
            raise ValueError('Identificador de clase inválido')
        return self
