# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All commands run from the `backend/` directory unless stated otherwise.

```bash
# Install dev dependencies
pip install -e '.[dev]'

# Format code
make fmt

# Lint and type check
make lint

# Run tests (uses in-memory SQLite, no Postgres needed)
make test

# Run a single test file or test
pytest tests/test_analyze.py
pytest tests/test_analyze.py::test_submit_job

# Build wheel
make build

# Run locally (Postgres + FastAPI at localhost:8000)
docker compose up                   # from repo root
alembic upgrade head                # apply migrations manually if needed
```

## After finishing a feature

Always run the following before considering a task done:

```bash
make lint
make test
```

Fix all failures before stopping.

## Architecture

This is a FastAPI proxy service that routes photo-analysis requests through a pool of real Telegram user accounts to a target bot (`@mycommentinst_bot`).

### Request flow

1. Client `POST /api/v1/analyze` (multipart photo) → creates `AnalysisJob` row (status: pending), returns `job_id`
2. Background task `process_job()` acquires a free account from `AccountManager`
3. Telethon client sends the photo to the target bot via that account's Telegram session
4. Worker waits for the bot reply (up to `TELEGRAM_REPLY_TIMEOUT_SECONDS`)
5. Reply JSON is stored on the job row → status becomes `completed` (or `failed`)
6. Client polls `GET /api/v1/analyze/{job_id}` until done

### Key modules

| Path | Role |
|------|------|
| `app/telegram/manager.py` | `AccountManager` — in-memory pool, round-robin acquisition, `_in_flight` tracking |
| `app/telegram/client.py` | Sends photo + waits for reply using Telethon |
| `app/api/v1/analyze.py` | Submit/poll endpoints; fires background task |
| `app/api/v1/accounts.py` | Admin CRUD for the Telegram account pool |
| `app/core/config.py` | All settings via `pydantic-settings` |
| `app/core/db.py` | Global SQLModel `engine`; patched in tests |
| `app/crud/` | DB layer (jobs + accounts) |
| `app/models/` | `TelegramAccount`, `AnalysisJob` SQLModel table definitions |

### Concurrency constraint

`AccountManager` enforces **one in-flight job per account** to avoid bot-reply ambiguity. Jobs queue if all accounts are busy.

### Auth model

- `X-API-Key` header required on all endpoints
- `ADMIN_API_KEY`: full access (accounts CRUD + analysis)
- `API_KEYS` (comma-separated): submit/poll analysis only

### Encrypted sessions

Telegram session strings are encrypted at rest with Fernet (`SESSION_ENCRYPTION_KEY`). The `scripts/add_account.py` helper encrypts and inserts a session into Postgres.

### Test setup

`tests/conftest.py` swaps the global `engine` to an in-memory SQLite DB and disables the FastAPI lifespan (no real Telegram connections). Tests should never require a running Postgres instance.
