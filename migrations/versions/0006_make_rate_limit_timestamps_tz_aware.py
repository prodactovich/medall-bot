"""make rate_limit_buckets timestamps timezone aware"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0006_rate_limit_tz_aware"
down_revision = "0005_add_rate_limit_buckets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.alter_column(
            "rate_limit_buckets",
            "expires_at",
            existing_type=sa.DateTime(),
            type_=sa.DateTime(timezone=True),
            postgresql_using="expires_at AT TIME ZONE 'UTC'",
        )
        op.alter_column(
            "rate_limit_buckets",
            "updated_at",
            existing_type=sa.DateTime(),
            type_=sa.DateTime(timezone=True),
            postgresql_using="updated_at AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.alter_column(
            "rate_limit_buckets",
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            type_=sa.DateTime(),
            postgresql_using="updated_at AT TIME ZONE 'UTC'",
        )
        op.alter_column(
            "rate_limit_buckets",
            "expires_at",
            existing_type=sa.DateTime(timezone=True),
            type_=sa.DateTime(),
            postgresql_using="expires_at AT TIME ZONE 'UTC'",
        )
