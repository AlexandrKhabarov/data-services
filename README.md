# data-services

A FastAPI proxy service that routes photo-analysis requests through a pool of real Telegram user accounts to a target bot (`@mycommentinst_bot`). Clients submit a photo, get back a `job_id`, and poll until the bot reply is ready.

## How it works

1. `POST /api/v1/analyze` — upload a photo, receive a `job_id`
2. Background task picks a free Telegram account and sends the photo to the bot
3. Worker waits for the bot reply (up to `TELEGRAM_REPLY_TIMEOUT_SECONDS`)
4. `GET /api/v1/analyze/{job_id}` — poll until `status: completed` and read the result

## Local setup

**Prerequisites:** [Docker](https://docs.docker.com/get-docker/), [uv](https://github.com/astral-sh/uv)

### 1. Configure environment

```bash
cp .env.example .env
```

Edit `.env` — at minimum set:

| Variable | Description |
|---|---|
| `POSTGRES_PASSWORD` | Any strong password |
| `ADMIN_API_KEY` | Your admin key for the API |
| `SESSION_ENCRYPTION_KEY` | Fernet key for encrypting Telegram sessions |

Generate a Fernet key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 2. Start services

```bash
docker compose up
```

This starts Postgres and the FastAPI backend at `http://localhost:8000`. Migrations run automatically on startup.

### 3. Add a Telegram account

The service needs at least one Telegram account in the pool to process jobs.

```bash
cd backend
uv sync
python scripts/add_account.py
```

The script prompts for your [Telegram API credentials](https://my.telegram.org/apps), authenticates interactively, and registers the account via the admin API.

### 4. Verify

```bash
curl http://localhost:8000/api/v1/health
```

## Development

All commands run from the `backend/` directory.

```bash
# Install dependencies
uv sync

# Format code
make fmt

# Lint and type-check
make lint

# Run tests (in-memory SQLite, no Postgres needed)
make test

# Run a single test
uv run pytest tests/test_health.py::test_health

# Build wheel
make build
```

## API auth

All endpoints require an `X-API-Key` header:

- `ADMIN_API_KEY` — full access (account management + analysis)
- `API_KEYS` — analysis submit/poll only (comma-separated list in `.env`)
