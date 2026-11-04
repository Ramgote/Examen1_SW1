import uuid
from datetime import datetime, timezone
from typing import List, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, CheckConstraint, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint(
            "author_type IN ('user', 'assistant', 'system')",
            name="check_chat_author_type"
        ),
        Index("idx_chat_messages_project_created", "project_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    author_type: Mapped[str] = mapped_column(
        String(20),
        default="user",
        nullable=False
    )
    author_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    reply_to_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="SET NULL"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relaciones
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="messages"
    )
    author: Mapped["User | None"] = relationship(
        "User"
    )
    reply_to: Mapped["ChatMessage | None"] = relationship(
        "ChatMessage",
        remote_side=[id],
        back_populates="replies"
    )
    replies: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="reply_to"
    )


class HelpRequest(Base):
    __tablename__ = "help_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="check_help_request_status"
        ),
        UniqueConstraint("project_id", "idempotency_key", name="uq_help_request_idempotency"),
        Index("idx_help_requests_project_status", "project_id", "status"),
        Index("idx_help_requests_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    source_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="SET NULL"),
        nullable=True
    )
    response_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="SET NULL"),
        nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(120),
        nullable=False
    )
    context_revision: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False
    )
    error_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relaciones
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="help_requests"
    )
    requester: Mapped["User"] = relationship(
        "User"
    )
    source_message: Mapped["ChatMessage | None"] = relationship(
        "ChatMessage",
        foreign_keys=[source_message_id]
    )
    response_message: Mapped["ChatMessage | None"] = relationship(
        "ChatMessage",
        foreign_keys=[response_message_id]
    )


class ModeratorSettings(Base):
    __tablename__ = "moderator_settings"
    __table_args__ = (
        CheckConstraint(
            "mode IN ('off', 'reactive', 'proactive')",
            name="check_moderator_mode"
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True
    )
    mode: Mapped[str] = mapped_column(
        String(20),
        default="reactive",
        nullable=False
    )
    require_human_approval: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relación
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="moderator_settings"
    )
