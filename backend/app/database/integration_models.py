"""OAuth / integration connection persistence."""

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models import Base


class IntegrationConnection(Base):
    """Workspace-scoped third-party connection for one Norma user."""

    __tablename__ = "integration_connections"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "user_id",
            "workspace_id",
            name="uq_integration_provider_user_workspace",
        ),
        Index("ix_integration_connections_workspace_id", "workspace_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    external_workspace_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    external_workspace_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
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
