"""Create state document storage.

Revision ID: 20260411_0001
Revises:
Create Date: 2026-04-11 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260411_0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Create the persistent document table."""

    op.create_table(
        "state_documents",
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("name"),
    )


def downgrade() -> None:
    """Drop the persistent document table."""

    op.drop_table("state_documents")
