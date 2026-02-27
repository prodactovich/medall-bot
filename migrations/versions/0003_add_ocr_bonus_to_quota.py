"""add ocr bonus fields to quota snapshots"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0003_add_ocr_bonus_to_quota"
down_revision = "0002_plan_plus_to_pro"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "quota_snapshots",
        sa.Column(
            "bonus_ocr_left",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "quota_snapshots",
        sa.Column(
            "bonus_ocr_granted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("quota_snapshots", "bonus_ocr_granted")
    op.drop_column("quota_snapshots", "bonus_ocr_left")
