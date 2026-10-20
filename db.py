"""SQLite access for the Sculpture Trail Visitor Map.

One embedded database file (``trail.db`` by default, override with the
``SCULPTURE_DB_PATH`` environment variable) opened per request. SQLite is
opened with foreign keys enforced and WAL enabled so the seeded trail and the
visitor writes survive restarts.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Iterable, Sequence

import aiosqlite

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "schema.sql"


def _resolve_db_path() -> str:
    """Resolve the SQLite path, honouring an explicit env override.

    Relative paths resolve against the project root, so the file always lives
    inside the project no matter which directory the server was started from.
    """
    explicit = os.getenv("SCULPTURE_DB_PATH")
    if not explicit:
        database_url = os.getenv("DATABASE_URL", "")
        if database_url.startswith("sqlite:///"):
            explicit = database_url[len("sqlite:///") :]
    if not explicit:
        return str(BASE_DIR / "trail.db")
    path = Path(explicit)
    if not path.is_absolute():
        path = BASE_DIR / path
    return str(path)


DB_PATH = _resolve_db_path()


@asynccontextmanager
async def connect() -> AsyncIterator[aiosqlite.Connection]:
    """Open a short-lived connection with FKs on and a busy timeout."""
    parent = Path(DB_PATH).parent
    parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(DB_PATH, timeout=10)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys = ON")
    await conn.execute("PRAGMA busy_timeout = 5000")
    try:
        yield conn
    finally:
        await conn.close()


async def init_db() -> None:
    """Create the schema if it is missing and switch the file to WAL mode."""
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    async with connect() as conn:
        await conn.execute("PRAGMA journal_mode = WAL")
        await conn.executescript(schema_sql)
        await conn.commit()


async def fetch_all(
    conn: aiosqlite.Connection, sql: str, params: Sequence[Any] = ()
) -> list[dict[str, Any]]:
    async with conn.execute(sql, params) as cursor:
        rows: Iterable[aiosqlite.Row] = await cursor.fetchall()
    return [dict(row) for row in rows]


async def fetch_one(
    conn: aiosqlite.Connection, sql: str, params: Sequence[Any] = ()
) -> dict[str, Any] | None:
    async with conn.execute(sql, params) as cursor:
        row = await cursor.fetchone()
    return dict(row) if row else None


async def fetch_value(
    conn: aiosqlite.Connection, sql: str, params: Sequence[Any] = ()
) -> Any:
    async with conn.execute(sql, params) as cursor:
        row = await cursor.fetchone()
    return row[0] if row else None


async def execute(
    conn: aiosqlite.Connection, sql: str, params: Sequence[Any] = ()
) -> int:
    """Run a write statement, commit, and return the new row id (or 0)."""
    cursor = await conn.execute(sql, params)
    await conn.commit()
    last_row_id = cursor.lastrowid or 0
    await cursor.close()
    return last_row_id
