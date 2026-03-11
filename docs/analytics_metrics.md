# MedAll Analytics: Clarity and TTU

## PostgreSQL Connection (DBeaver)

- Host: `localhost`
- Port: `5432`
- Database: `medall`
- User: `medall`
- Password: from `.env` (`POSTGRES_PASSWORD`)
- JDBC URL example: `jdbc:postgresql://localhost:5432/medall`

## Apply migrations

```bash
python -m alembic upgrade head
```

## Core analytics objects

- View: `analytics_patient_sessions`
  - Session-level fact for patient flows
  - Fields: `first_explanation_ts`, `understood_ts`, `clarifying_questions`, `ttu_seconds`

- View: `analytics_patient_metrics_daily`
  - Daily aggregates
  - Fields: `clarity_rate_percent`, `median_ttu_seconds`, `p90_ttu_seconds`

## Quick checks

```sql
SELECT * FROM analytics_patient_sessions
ORDER BY first_explanation_ts DESC
LIMIT 50;
```

```sql
SELECT * FROM analytics_patient_metrics_daily
ORDER BY metric_date DESC;
```
