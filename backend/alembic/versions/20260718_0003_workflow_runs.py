"""Create workflow runs and artifacts tables."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260718_0003"
down_revision: str | None = "20260718_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

workflow_status = sa.Enum(
    "pending",
    "running",
    "completed",
    "failed",
    name="workflow_run_status",
)
artifact_kind = sa.Enum(
    "research",
    "competitors",
    "positioning",
    "roadmap",
    "marketing",
    "pack",
    name="workflow_artifact_kind",
)


def upgrade() -> None:
    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_type", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            workflow_status,
            server_default="pending",
            nullable=False,
        ),
        sa.Column("brief", sa.Text(), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workflow_runs_workspace_id",
        "workflow_runs",
        ["workspace_id"],
    )
    op.create_index("ix_workflow_runs_user_id", "workflow_runs", ["user_id"])
    op.create_table(
        "workflow_artifacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("kind", artifact_kind, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["workflow_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workflow_artifacts_run_id",
        "workflow_artifacts",
        ["run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_artifacts_run_id", table_name="workflow_artifacts")
    op.drop_table("workflow_artifacts")
    op.drop_index("ix_workflow_runs_user_id", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_workspace_id", table_name="workflow_runs")
    op.drop_table("workflow_runs")
    artifact_kind.drop(op.get_bind(), checkfirst=True)
    workflow_status.drop(op.get_bind(), checkfirst=True)
