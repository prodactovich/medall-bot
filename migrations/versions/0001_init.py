"""init db"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column(
            "plan",
            sa.String(length=16),
            nullable=False,
            server_default="basic",
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

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("plan", sa.String(length=16), nullable=False),
        sa.Column(
            "start_date",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("end_date", sa.DateTime(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "auto_renew",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("payment_id", sa.String(length=128), nullable=True),
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

    op.create_table(
        "quota_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("month", sa.String(length=7), nullable=False),
        sa.Column(
            "used_messages", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "used_docs", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "used_essays", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "used_tokens", sa.Integer(), nullable=False, server_default="0"
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
        sa.UniqueConstraint("user_id", "month", name="uq_quota_user_month"),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("telegram_file_id", sa.String(length=256), nullable=False),
        sa.Column(
            "doc_type",
            sa.String(length=32),
            nullable=False,
            server_default="other",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True, index=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("plan", sa.String(length=16), nullable=False),
        sa.Column("request_type", sa.String(length=32), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("request_text", sa.Text(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column(
            "tokens_used", sa.Integer(), nullable=False, server_default="0"
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
        sa.Column("document_id", sa.Integer(), nullable=True),
    )

    op.create_table(
        "usage_stats",
        sa.Column(
            "month", sa.String(length=7), primary_key=True, nullable=False
        ),
        sa.Column(
            "input_chars", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "output_chars", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            onupdate=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "event_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ts",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("event", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True, index=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("event_log")
    op.drop_table("usage_stats")
    op.drop_table("requests")
    op.drop_table("documents")
    op.drop_table("quota_snapshots")
    op.drop_table("subscriptions")
    op.drop_table("users")
