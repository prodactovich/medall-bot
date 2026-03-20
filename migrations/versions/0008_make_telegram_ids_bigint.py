"""make telegram ids bigint"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0008_make_telegram_ids_bigint"
down_revision = "0007_add_user_runtime_state"
branch_labels = None
depends_on = None


ANALYTICS_PATIENT_SESSIONS_SQL = """
CREATE OR REPLACE VIEW analytics_patient_sessions AS
WITH first_doc AS (
    SELECT
        session_id,
        MIN(ts) AS first_doc_ts
    FROM event_log
    WHERE event = 'document_sent'
      AND COALESCE(payload->>'role', '') = 'patient'
    GROUP BY session_id
),
first_expl AS (
    SELECT
        session_id,
        MIN(ts) AS first_explanation_ts,
        MIN(user_id) AS user_id
    FROM event_log
    WHERE event = 'explanation_generated'
      AND COALESCE(payload->>'role', '') = 'patient'
    GROUP BY session_id
),
understood AS (
    SELECT
        session_id,
        MIN(ts) AS understood_ts
    FROM event_log
    WHERE event = 'understood_confirmed'
    GROUP BY session_id
),
clarifying AS (
    SELECT
        session_id,
        COUNT(*)::int AS clarifying_questions
    FROM event_log
    WHERE event = 'clarifying_question_asked'
    GROUP BY session_id
)
SELECT
    fe.session_id,
    fe.user_id,
    fd.first_doc_ts,
    fe.first_explanation_ts,
    u.understood_ts,
    COALESCE(c.clarifying_questions, 0) AS clarifying_questions,
    CASE
        WHEN fe.first_explanation_ts IS NOT NULL AND u.understood_ts IS NOT NULL
        THEN EXTRACT(EPOCH FROM (u.understood_ts - fe.first_explanation_ts))
        ELSE NULL
    END AS ttu_seconds
FROM first_expl fe
LEFT JOIN first_doc fd ON fd.session_id = fe.session_id
LEFT JOIN understood u ON u.session_id = fe.session_id
LEFT JOIN clarifying c ON c.session_id = fe.session_id;
"""


ANALYTICS_PATIENT_METRICS_DAILY_SQL = """
CREATE OR REPLACE VIEW analytics_patient_metrics_daily AS
SELECT
    DATE(first_explanation_ts) AS metric_date,
    COUNT(*)::int AS sessions_total,
    COUNT(*) FILTER (WHERE understood_ts IS NOT NULL)::int AS sessions_understood,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE understood_ts IS NOT NULL)
        / NULLIF(COUNT(*), 0),
        2
    ) AS clarity_rate_percent,
    ROUND(AVG(clarifying_questions)::numeric, 2) AS avg_clarifying_questions,
    ROUND(
        percentile_cont(0.5) WITHIN GROUP (ORDER BY ttu_seconds)::numeric,
        2
    ) AS median_ttu_seconds,
    ROUND(
        percentile_cont(0.9) WITHIN GROUP (ORDER BY ttu_seconds)::numeric,
        2
    ) AS p90_ttu_seconds
FROM analytics_patient_sessions
WHERE first_explanation_ts IS NOT NULL
GROUP BY DATE(first_explanation_ts);
"""


def _drop_analytics_views_if_postgres() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("DROP VIEW IF EXISTS analytics_patient_metrics_daily")
    op.execute("DROP VIEW IF EXISTS analytics_patient_sessions")


def _recreate_analytics_views_if_postgres() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(ANALYTICS_PATIENT_SESSIONS_SQL)
    op.execute(ANALYTICS_PATIENT_METRICS_DAILY_SQL)


def upgrade() -> None:
    _drop_analytics_views_if_postgres()

    op.alter_column(
        "users",
        "telegram_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )
    op.alter_column(
        "subscriptions",
        "user_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )
    op.alter_column(
        "quota_snapshots",
        "user_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )
    op.alter_column(
        "documents",
        "user_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )
    op.alter_column(
        "requests",
        "user_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
    )
    op.alter_column(
        "event_log",
        "user_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
    )
    op.alter_column(
        "user_runtime_state",
        "user_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )

    _recreate_analytics_views_if_postgres()


def downgrade() -> None:
    _drop_analytics_views_if_postgres()

    op.alter_column(
        "user_runtime_state",
        "user_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "event_log",
        "user_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
    )
    op.alter_column(
        "requests",
        "user_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
    )
    op.alter_column(
        "documents",
        "user_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "quota_snapshots",
        "user_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "subscriptions",
        "user_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "users",
        "telegram_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )

    _recreate_analytics_views_if_postgres()
