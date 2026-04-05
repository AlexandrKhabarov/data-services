from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
)


def init_db() -> None:
    """Create all tables. Used in tests and local dev without Docker.
    Production should use `alembic upgrade head`."""
    # Import models so SQLModel registers them before create_all
    import app.models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_db():
    """FastAPI dependency that yields a DB session."""
    with Session(engine) as session:
        yield session
