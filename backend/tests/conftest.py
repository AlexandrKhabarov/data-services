"""
Test configuration.

Uses an in-memory SQLite database so tests run without PostgreSQL.
The global `engine` in app.core.db is monkey-patched to point at the
test engine before any app code touches it.

The FastAPI lifespan is NOT triggered (we create TestClient without the
context manager), so no real Telegram connections are attempted.
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

import app.core.db as db_module
from app.api.deps import get_db
from app.core.config import settings
from app.main import app
from app.telegram.account_manager import AccountManager


@pytest.fixture(scope="function", autouse=True)
def patch_engine():
    """Replace the global PostgreSQL engine with an in-memory SQLite engine."""
    import app.models  # noqa: F401 — register all SQLModel tables

    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)

    # Patch the module-level engine used by CRUD, worker, etc.
    original = db_module.engine
    db_module.engine = test_engine
    yield test_engine
    db_module.engine = original
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture()
def db(patch_engine):
    with Session(patch_engine) as session:
        yield session


@pytest.fixture()
def client(patch_engine):
    """
    TestClient without context manager → lifespan does NOT run.
    We manually set app.state.account_manager so the dependency works.
    """
    def override_get_db():
        with Session(patch_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.state.account_manager = AccountManager()

    yield TestClient(app, raise_server_exceptions=True)

    app.dependency_overrides.clear()


@pytest.fixture()
def admin_headers() -> dict[str, str]:
    return {"X-API-Key": settings.ADMIN_API_KEY}
