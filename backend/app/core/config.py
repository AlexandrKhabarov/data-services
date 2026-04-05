import secrets
from typing import Literal

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    # ── Security ──────────────────────────────────────────────────────────────
    SECRET_KEY: str = secrets.token_urlsafe(32)

    # Admin key — full access (account CRUD + analysis submit)
    ADMIN_API_KEY: str = secrets.token_urlsafe(32)

    # Additional API keys for external callers (read/submit only, no account mgmt)
    # Comma-separated string parsed into a list by pydantic-settings
    API_KEYS: list[str] = []

    # Fernet key for encrypting Telegram session strings at rest.
    # Generate with: python -c "from cryptography.fernet import Fernet;
    #   print(Fernet.generate_key().decode())"
    SESSION_ENCRYPTION_KEY: str = secrets.token_urlsafe(32)

    # ── CORS ──────────────────────────────────────────────────────────────────
    BACKEND_CORS_ORIGINS: list[str] = []
    FRONTEND_HOST: str = "http://localhost:5173"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        origins = list(self.BACKEND_CORS_ORIGINS)
        if self.FRONTEND_HOST not in origins:
            origins.append(self.FRONTEND_HOST)
        return origins

    # ── Database ──────────────────────────────────────────────────────────────
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "dataservices"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ── Telegram ──────────────────────────────────────────────────────────────
    TELEGRAM_TARGET_BOT: str = "mycommentinst_bot"
    TELEGRAM_REPLY_TIMEOUT_SECONDS: int = 60

    # ── Sentry ────────────────────────────────────────────────────────────────
    SENTRY_DSN: str | None = None


settings = Settings()
