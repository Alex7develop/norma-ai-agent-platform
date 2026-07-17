"""Persisted multi-agent workflow runs and produced artifacts."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models import Base


class WorkflowStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ArtifactKind(enum.StrEnum):
    RESEARCH = "research"
    COMPETITORS = "competitors"
    POSITIONING = "positioning"
    ROADMAP = "roadmap"
    MARKETING = "marketing"
    BUSINESS_MODEL = "business_model"
    FINANCIAL = "financial"
    PRD = "prd"
    TECH_SPEC = "tech_spec"
    CURSOR_PROMPTS = "cursor_prompts"
    LINKEDIN = "linkedin"
    TELEGRAM = "telegram"
    PACK = "pack"


workflow_status_enum = Enum(
    WorkflowStatus,
    name="workflow_run_status",
    values_callable=lambda enum_class: [member.value for member in enum_class],
)

artifact_kind_enum = Enum(
    ArtifactKind,
    name="workflow_artifact_kind",
    values_callable=lambda enum_class: [member.value for member in enum_class],
)


class WorkflowRun(Base):
    """One auditable execution of a multi-agent workflow."""

    __tablename__ = "workflow_runs"
    __table_args__ = (
        Index("ix_workflow_runs_workspace_id", "workspace_id"),
        Index("ix_workflow_runs_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    workflow_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[WorkflowStatus] = mapped_column(
        workflow_status_enum,
        nullable=False,
        default=WorkflowStatus.PENDING,
        server_default=WorkflowStatus.PENDING.value,
    )
    brief: Mapped[str] = mapped_column(Text, nullable=False)
    product_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    artifacts: Mapped[list["WorkflowArtifact"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="WorkflowArtifact.created_at",
    )


class WorkflowArtifact(Base):
    """Markdown artifact produced by a workflow agent step."""

    __tablename__ = "workflow_artifacts"
    __table_args__ = (Index("ix_workflow_artifacts_run_id", "run_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[ArtifactKind] = mapped_column(artifact_kind_enum, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    run: Mapped[WorkflowRun] = relationship(back_populates="artifacts")
