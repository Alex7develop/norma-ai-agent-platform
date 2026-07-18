"""Create integration_connections for Notion OAuth tokens.

Revision ID: 20260718_0009
Revises: 20260718_0008
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260718_0009"
down_revision: str | None = "20260718_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "integration_connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("external_workspace_id", sa.String(length=255), nullable=True),
        sa.Column("external_workspace_name", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "user_id",
            "workspace_id",
            name="uq_integration_provider_user_workspace",
        ),
    )
    op.create_index(
        "ix_integration_connections_user_id",
        "integration_connections",
        ["user_id"],
    )
    op.create_index(
        "ix_integration_connections_workspace_id",
        "integration_connections",
        ["workspace_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_integration_connections_workspace_id",
        table_name="integration_connections",
    )
    op.drop_index(
        "ix_integration_connections_user_id",
        table_name="integration_connections",
    )
    op.drop_table("integration_connections")
