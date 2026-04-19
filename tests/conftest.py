"""Shared test fixtures."""

import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ["SHORTCUTS_AUTH_TOKEN"] = "test-token-12345"
os.environ["INFERENCE_BACKEND"] = "gemma"
os.environ["NTFY_TOPIC"] = ""

from app.main import app  # noqa: E402


@pytest.fixture
async def db_path(tmp_path):
    """Provide a temp DB path with initialized tables."""
    from app.config import settings
    from app.db import init_db
    original = settings.DB_PATH
    settings.DB_PATH = str(tmp_path / "test.db")
    import app.db as db_mod
    db_mod._db_path = None
    await init_db()
    from app.audit import init_audit_table
    await init_audit_table()
    yield settings.DB_PATH
    settings.DB_PATH = original
    db_mod._db_path = None


@pytest.fixture
async def client(db_path):
    """Async test client with initialized DB."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token-12345"}


@pytest.fixture
def tailscale_headers():
    return {"Tailscale-User-Login": "testuser@example.com"}
