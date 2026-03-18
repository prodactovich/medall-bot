# MedAll Bot

> AI-assisted Telegram bot for patient-friendly interpretation of medical documents, urgency estimation, and doctor-prep guidance.

## Overview

**MedAll** is a Telegram MVP focused on one practical job: help a patient understand a medical document in plain language without pretending to replace a doctor.

The product is built around short, actionable patient flows:

- `explain_document`
- `urgency_check`
- `next_24h_plan`
- `questions_for_doctor`

It also supports adjacent roles:

- `doctor`
- `student`

## Product Value

| Layer | What MedAll gives |
|---|---|
| Clarity | Explains medical text in simpler language |
| Triage | Helps estimate whether a situation looks urgent |
| Next step | Suggests what to do in the next 24 hours |
| Consultation prep | Builds a list of questions for the doctor |
| Safety | Avoids diagnosis, prescriptions, and pretending to replace in-person care |

## Core Business Metrics

The MVP is already instrumented around two product metrics.

### `clarity_rate_percent`

Share of patient sessions where the user explicitly confirms that the explanation became understandable.

Source signal:

- `understood_confirmed`

### `TTU (Time To Understanding)`

Time from the first generated explanation to the first explicit understanding signal from the user.

Stored as:

- `ttu_seconds`

### Supporting Product Signals

- `document_sent`
- `explanation_generated`
- `clarifying_question_asked`
- `understood_confirmed`

### Analytics Objects

- `analytics_patient_sessions`
- `analytics_patient_metrics_daily`

Detailed metric notes and SQL checks are available in [analytics_metrics.md](/d:/STARTAP/medall-bot/docs/analytics_metrics.md).

## High-Level Architecture

```text
Telegram User
    |
    v
python-telegram-bot handlers
    |
    +--> OCR layer (photo -> text)
    |
    +--> context + role + scenario builder
    |
    +--> LLM prompt orchestration
    |
    +--> response back to Telegram
    |
    +--> event_log + analytics views in PostgreSQL
```

### Runtime Flow

1. User sends text or photo in Telegram.
2. Bot detects role, active scenario, quota, and safety context.
3. OCR is applied for image-based documents.
4. Prompt and structured context are sent to the LLM.
5. Response is returned to the user.
6. Product telemetry is written into `event_log`.
7. KPI views are computed in PostgreSQL.

## Tech Stack

| Area | Stack |
|---|---|
| Runtime | Python 3.11 |
| Bot framework | `python-telegram-bot` |
| ORM / DB access | SQLAlchemy 2.x |
| Migrations | Alembic |
| Primary database | PostgreSQL 16 |
| PostgreSQL driver | `psycopg` |
| LLM HTTP client | `aiohttp` |
| OCR HTTP client | `requests` |
| Containers | Docker, Docker Compose |
| Dev quality | Pytest, Black, Ruff |

## Repository Map

| Path | Responsibility |
|---|---|
| [src/bot.py](/d:/STARTAP/medall-bot/src/bot.py) | Application entrypoint |
| `src/handlers/` | Telegram handlers and routing |
| [src/prompts.py](/d:/STARTAP/medall-bot/src/prompts.py) | Main prompt rules |
| [src/services/patient_prompts.py](/d:/STARTAP/medall-bot/src/services/patient_prompts.py) | Patient-specific prompt templates |
| `src/db/` | SQLAlchemy models and sessions |
| [domain/analytics.py](/d:/STARTAP/medall-bot/domain/analytics.py) | Event tracking and analytics logging |
| `migrations/` | Alembic migrations |
| `docs/` | Supporting product / analytics docs |
| `tests/` | Basic test coverage |

## Database Design

This project currently uses an **operational-first database model**, not a full star schema.

From a middle-level data engineering perspective, the DB is split into four layers:

### 1. OLTP application state

- `users`
- `subscriptions`
- `quota_snapshots`
- `documents`
- `requests`
- `rate_limit_buckets`

### 2. Event layer

- `event_log`

This is the main telemetry source for product analytics.

### 3. Aggregate usage layer

- `usage_stats`

### 4. Analytical SQL views

- `analytics_patient_sessions`
- `analytics_patient_metrics_daily`

### Short data-engineering interpretation

The application stores transactional state and product telemetry separately, then computes KPI-ready analytical views directly in PostgreSQL. For an MVP this is a practical design:

- simple enough for fast product iteration;
- structured enough for DBeaver analysis and BI;
- easy to evolve later into a dedicated mart or star-schema layer if volume grows.

## Local Setup

### 1. Environment

Create `.env` from `.env.example` and fill the required values:

- `TELEGRAM_TOKEN`
- `DEEPSEEK_API_KEY`
- `OCR_SPACE_API_KEY`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `DATABASE_URL`

Example local DSN:

```bash
DATABASE_URL=postgresql+psycopg://medall:strong_password@localhost:5432/medall
```

Example Docker DSN:

```bash
DATABASE_URL=postgresql+psycopg://medall:strong_password@postgres:5432/medall
```

### 2. Apply migrations

```bash
python -m alembic upgrade head
```

### 3. Run the bot

```bash
python -m src.bot
```

## Docker Run

```bash
docker compose up -d --build
```

The compose stack starts:

- PostgreSQL
- Telegram bot container

The bot applies Alembic migrations on startup before polling begins.

## DBeaver / Analytics Access

Use DBeaver to inspect PostgreSQL schema, event data, and analytical views.

### Connection Parameters

| Field | Value |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| Database | value from `POSTGRES_DB` |
| User | value from `POSTGRES_USER` |
| Password | value from `POSTGRES_PASSWORD` |

### Example Checks

```sql
SELECT *
FROM analytics_patient_sessions
ORDER BY first_explanation_ts DESC
LIMIT 20;
```

```sql
SELECT *
FROM analytics_patient_metrics_daily
ORDER BY metric_date DESC;
```

## Security and Production Notes

> The project is already hardened for MVP production use, but still assumes controlled rollout rather than large-scale traffic.

- `.env` must never be committed.
- Docker build excludes `.env` through [`.dockerignore`](/d:/STARTAP/medall-bot/.dockerignore).
- Runtime validates required environment variables on startup.
- Rate limiting is backed by PostgreSQL TTL buckets.
- Sensitive feedback text is redacted before analytics persistence.
- Migrations are part of the standard startup path.

## Tests

```bash
python -m pytest -q
```

## Project Structure

```text
src/
  bot.py
  handlers/
  db/
  services/
  ui/
domain/
  analytics.py
migrations/
docs/
tests/
```

## Current Positioning

MedAll is not a generic “medical chatbot”. It is a narrow workflow product focused on:

- understanding a medical document;
- reducing ambiguity;
- shortening time to understanding;
- preparing the user for a better doctor interaction.
