from typing import Literal
from pydantic import Field, model_validator
from app.schemas.uml import UMLModel, UMLClassNode, UMLEdge, ElementId


class Attachment(UMLModel):
    name: str = Field(min_length=1, max_length=160)
    mime_type: Literal['image/png', 'image/jpeg', 'image/webp', 'audio/webm', 'audio/ogg', 'audio/wav', 'audio/mpeg']
    data: str = Field(min_length=1, max_length=8 * 1024 * 1024, repr=False)


class AssistantRequest(UMLModel):
    expected_version: int = Field(ge=1, le=2147483646, strict=True)
    prompt: str = Field(default='', max_length=8000)
    attachments: list[Attachment] = Field(default_factory=list, max_length=4)

    @model_validator(mode='after')
    def content_required(self):
        if not self.prompt and not self.attachments:
            raise ValueError('Escribe una instrucción o adjunta una imagen o audio.')
        if sum(a.mime_type.startswith('image/') for a in self.attachments) > 3:
            raise ValueError('Máximo tres imágenes por solicitud.')
        if sum(a.mime_type.startswith('audio/') for a in self.attachments) > 1:
            raise ValueError('Máximo un audio por solicitud.')
        return self


class UMLProposal(UMLModel):
    message: str = Field(min_length=1, max_length=3000, description='Explicación en español o pregunta de aclaración.')
    transcript: str = Field(default='', max_length=8000, description='Transcripción del audio, vacía si no hay voz.')
    warnings: list[str] = Field(default_factory=list, max_length=20)
    upsert_nodes: list[UMLClassNode] = Field(default_factory=list, max_length=200, description='Clases completas nuevas o modificadas. Conservar IDs existentes.')
    delete_node_ids: list[ElementId] = Field(default_factory=list, max_length=200)
    upsert_edges: list[UMLEdge] = Field(default_factory=list, max_length=500, description='Relaciones completas nuevas o modificadas. Conservar IDs existentes.')
    delete_edge_ids: list[ElementId] = Field(default_factory=list, max_length=500)
