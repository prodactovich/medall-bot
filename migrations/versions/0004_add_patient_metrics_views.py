"""add indexes and analytics views for patient clarity and TTU"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0004_add_patient_metrics_views"
down_revision = "0003_add_ocr_bonus_to_quota"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_event_log_event_ts",
        "event_log",
        ["event", "ts"],
        unique=False,
    )
    op.create_index(
        "ix_event_log_session_event_ts",
        "event_log",
        ["session_id", "event", "ts"],
        unique=False,
    )

    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        """
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
    )

    op.execute(
        """
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
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP VIEW IF EXISTS analytics_patient_metrics_daily")
        op.execute("DROP VIEW IF EXISTS analytics_patient_sessions")

    op.drop_index("ix_event_log_session_event_ts", table_name="event_log")
    op.drop_index("ix_event_log_event_ts", table_name="event_log")
