import uuid
from datetime import datetime, timezone
from typing import List, TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.canvas import CanvasSnapshot


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relaciones
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="owned_projects"
    )
    collaborators: Mapped[List["ProjectCollaborator"]] = relationship(
        "ProjectCollaborator",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    canvas_snapshot: Mapped["CanvasSnapshot"] = relationship(
        "CanvasSnapshot",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan"
    )


class ProjectCollaborator(Base):
    __tablename__ = "project_collaborators"
    __table_args__ = (
        CheckConstraint(
            "role IN ('OWNER', 'EDITOR', 'VIEWER')",
            name="check_collaborator_role"
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )
    role: Mapped[str] = mapped_column(
        String(20),
        default="EDITOR",
        nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relaciones
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="collaborators"
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="collaborations"
    )