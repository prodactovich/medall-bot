"""add persistent user runtime state"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0007_add_user_runtime_state"
down_revision = "0006_rate_limit_tz_aware"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_runtime_state",
        sa.Column("user_id", sa.BigInteger(), primary_key=True),
        sa.Column("profile_type", sa.String(length=32), nullable=True),
        sa.Column("current_mode", sa.String(length=64), nullable=True),
        sa.Column(
            "last_document_text",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "last_ai_breakdown",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "last_document_summary",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
        sa.Column("scenario_messages", sa.JSON(), nullable=True),
        sa.Column(
            "docs_used",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "deep_used",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            onupdate=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade() -> None:
    op.drop_table("user_runtime_state")
