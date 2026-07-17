"""Add full launch-pack artifact kinds to workflow enum."""

from collections.abc import Sequence

from alembic import op

revision: str = "20260718_0004"
down_revision: str | None = "20260718_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_KINDS = (
    "business_model",
    "financial",
    "prd",
    "tech_spec",
    "cursor_prompts",
    "linkedin",
    "telegram",
)


def upgrade() -> None:
    for kind in NEW_KINDS:
        op.execute(
            f"ALTER TYPE workflow_artifact_kind ADD VALUE IF NOT EXISTS '{kind}'"
        )


def downgrade() -> None:
    # PostgreSQL cannot remove enum values safely; leave values in place.
    pass
