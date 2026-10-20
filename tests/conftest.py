"""pytest configuration: point the app at a throwaway seeded SQLite database."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_DB = Path(tempfile.mkdtemp(prefix="trail-tests-")) / "trail-test.db"
os.environ.setdefault("SCULPTURE_DB_PATH", str(TEST_DB))
os.environ.setdefault("SESSION_SECRET", "cenius-dev-test-only-session-secret")

from app import app  # noqa: E402  (import after the DB path is fixed)

DEMO_CURATOR = {"email": "cenius@cenius.ai", "password": "cenius"}
DEMO_VISITOR = {"email": "visitor@example.com", "password": "trail1234"}


@pytest_asyncio.fixture
async def client():
    """A fresh ASGI client with no session cookie."""
    asgi = app.asgi_client
    asgi.cookies.clear()
    return asgi


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def sign_in(client, credentials):
    request, response = await client.post("/api/auth/login", json=credentials)
    assert response.status == 200, response.text
    return response.json["user"]
