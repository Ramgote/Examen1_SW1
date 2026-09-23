from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=5000)


class ProjectRead(ProjectInput):
    id: UUID
    owner_id: UUID
    role: Literal["OWNER", "EDITOR", "VIEWER"]
    created_at: datetime
    updated_at: datetime


class MemberInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=255, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    role: Literal["EDITOR", "VIEWER"]

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class MemberRead(BaseModel):
    user_id: UUID
    email: str
    full_name: str
    role: Literal["OWNER", "EDITOR", "VIEWER"]
