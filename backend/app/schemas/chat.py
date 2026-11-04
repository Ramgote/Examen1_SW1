import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

AuthorType = Literal['user', 'assistant', 'system']
HelpRequestStatus = Literal['pending', 'processing', 'completed', 'failed']
ModeratorMode = Literal['off', 'reactive', 'proactive']


class ChatMessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    content: str = Field(min_length=1, max_length=5000)
    reply_to_message_id: uuid.UUID | None = None
    idempotency_key: str | None = Field(default=None, max_length=120)
    explicit_help_requested: bool = False


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    author_id: uuid.UUID | None
    author_type: AuthorType
    author_name: str
    content: str
    reply_to_message_id: uuid.UUID | None
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessageResponse]
    total: int
    has_more: bool


class HelpRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    content: str = Field(min_length=1, max_length=5000)
    idempotency_key: str = Field(min_length=1, max_length=120)
    source_message_id: uuid.UUID | None = None


class HelpRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    requester_id: uuid.UUID
    requester_name: str | None = None
    source_message_id: uuid.UUID | None
    response_message_id: uuid.UUID | None
    status: HelpRequestStatus
    idempotency_key: str
    context_revision: int
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class ModeratorSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: ModeratorMode | None = None
    require_human_approval: bool | None = None


class ModeratorSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: uuid.UUID
    mode: ModeratorMode
    require_human_approval: bool
    updated_at: datetime


class InterventionCandidate(BaseModel):
    """Contrato preparado para la futura fase de moderación proactiva."""
    model_config = ConfigDict(extra="forbid")

    project_id: uuid.UUID
    reason: str = Field(max_length=500)
    evidence_message_ids: list[uuid.UUID] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    status: Literal['proposed', 'dismissed', 'acted'] = 'proposed'
