"""migrate legacy plus plan to pro"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_plan_plus_to_pro"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Унифицируем legacy-план "plus" в текущий premium-код "pro".
    op.execute("UPDATE users SET plan = 'pro' WHERE plan = 'plus'")
    op.execute("UPDATE subscriptions SET plan = 'pro' WHERE plan = 'plus'")
    op.execute("UPDATE requests SET plan = 'pro' WHERE plan = 'plus'")


def downgrade() -> None:
    # Миграция сознательно необратима: после унификации невозможно отделить
    # бывшие plus-записи от исходных pro-записей.
    pass
