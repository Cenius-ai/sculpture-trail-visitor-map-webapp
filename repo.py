"""Repository layer: every SQL statement for the trail lives here.

All statements use bound parameters; no value is ever formatted into SQL.
"""

from __future__ import annotations

from typing import Any, Sequence

import aiosqlite

import db

SCULPTURE_COLUMNS = """
    sc.id, sc.title, sc.artist, sc.material, sc.description,
    sc.lat, sc.lng, sc.stage_id, sc.created_at,
    st.name AS stage_name, st.sequence AS stage_sequence,
    st.accessibility_notes AS stage_accessibility_notes,
    (SELECT COUNT(*) FROM feedback f WHERE f.sculpture_id = sc.id) AS feedback_count,
    (SELECT ROUND(AVG(f.rating), 2) FROM feedback f WHERE f.sculpture_id = sc.id) AS average_rating
"""


# --- users -----------------------------------------------------------------


async def get_user_by_login(conn: aiosqlite.Connection, identifier: str) -> dict[str, Any] | None:
    return await db.fetch_one(
        conn,
        "SELECT * FROM users WHERE email = ? COLLATE NOCASE OR username = ? COLLATE NOCASE",
        (identifier, identifier),
    )


async def get_user_by_email(conn: aiosqlite.Connection, email: str) -> dict[str, Any] | None:
    return await db.fetch_one(conn, "SELECT * FROM users WHERE email = ? COLLATE NOCASE", (email,))


async def get_user_by_username(conn: aiosqlite.Connection, username: str) -> dict[str, Any] | None:
    return await db.fetch_one(conn, "SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,))


async def get_user(conn: aiosqlite.Connection, user_id: int) -> dict[str, Any] | None:
    return await db.fetch_one(conn, "SELECT * FROM users WHERE id = ?", (user_id,))


async def create_user(
    conn: aiosqlite.Connection,
    *,
    email: str,
    username: str,
    display_name: str,
    password_hash: str,
    is_curator: bool = False,
    created_at: str,
) -> int:
    return await db.execute(
        conn,
        "INSERT INTO users (email, username, display_name, password_hash, is_curator, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (email, username, display_name, password_hash, 1 if is_curator else 0, created_at),
    )


async def update_user_password(
    conn: aiosqlite.Connection, user_id: int, password_hash: str
) -> None:
    await db.execute(
        conn, "UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id)
    )


# --- stages ----------------------------------------------------------------


async def list_stages(conn: aiosqlite.Connection) -> list[dict[str, Any]]:
    return await db.fetch_all(
        conn,
        """
        SELECT st.id, st.name, st.sequence, st.description, st.accessibility_notes, st.created_at,
               (SELECT COUNT(*) FROM sculptures sc WHERE sc.stage_id = st.id) AS sculpture_count
        FROM trail_stages st
        ORDER BY st.sequence ASC, st.id ASC
        """,
    )


async def get_stage(conn: aiosqlite.Connection, stage_id: int) -> dict[str, Any] | None:
    return await db.fetch_one(
        conn,
        """
        SELECT st.id, st.name, st.sequence, st.description, st.accessibility_notes, st.created_at,
               (SELECT COUNT(*) FROM sculptures sc WHERE sc.stage_id = st.id) AS sculpture_count
        FROM trail_stages st
        WHERE st.id = ?
        """,
        (stage_id,),
    )


async def get_stage_by_name(conn: aiosqlite.Connection, name: str) -> dict[str, Any] | None:
    return await db.fetch_one(conn, "SELECT * FROM trail_stages WHERE name = ?", (name,))


async def count_sculptures_in_stage(conn: aiosqlite.Connection, stage_id: int) -> int:
    value = await db.fetch_value(
        conn, "SELECT COUNT(*) FROM sculptures WHERE stage_id = ?", (stage_id,)
    )
    return int(value or 0)


async def create_stage(
    conn: aiosqlite.Connection,
    *,
    name: str,
    sequence: int,
    description: str,
    accessibility_notes: str,
    created_at: str,
) -> int:
    return await db.execute(
        conn,
        "INSERT INTO trail_stages (name, sequence, description, accessibility_notes, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (name, sequence, description, accessibility_notes, created_at),
    )


async def update_stage(
    conn: aiosqlite.Connection,
    stage_id: int,
    *,
    name: str,
    sequence: int,
    description: str,
    accessibility_notes: str,
) -> None:
    await db.execute(
        conn,
        "UPDATE trail_stages SET name = ?, sequence = ?, description = ?, accessibility_notes = ?"
        " WHERE id = ?",
        (name, sequence, description, accessibility_notes, stage_id),
    )


async def delete_stage(conn: aiosqlite.Connection, stage_id: int) -> None:
    await db.execute(conn, "DELETE FROM trail_stages WHERE id = ?", (stage_id,))


# --- sculptures ------------------------------------------------------------


async def list_sculptures(
    conn: aiosqlite.Connection, stage_id: int | None = None
) -> list[dict[str, Any]]:
    sql = (
        f"SELECT {SCULPTURE_COLUMNS} FROM sculptures sc"
        " JOIN trail_stages st ON st.id = sc.stage_id"
    )
    params: Sequence[Any] = ()
    if stage_id is not None:
        sql += " WHERE sc.stage_id = ?"
        params = (stage_id,)
    sql += " ORDER BY st.sequence ASC, sc.id ASC"
    return await db.fetch_all(conn, sql, params)


async def get_sculpture(conn: aiosqlite.Connection, sculpture_id: int) -> dict[str, Any] | None:
    return await db.fetch_one(
        conn,
        f"SELECT {SCULPTURE_COLUMNS} FROM sculptures sc"
        " JOIN trail_stages st ON st.id = sc.stage_id WHERE sc.id = ?",
        (sculpture_id,),
    )


async def get_sculpture_by_title(conn: aiosqlite.Connection, title: str) -> dict[str, Any] | None:
    return await db.fetch_one(conn, "SELECT * FROM sculptures WHERE title = ?", (title,))


async def create_sculpture(
    conn: aiosqlite.Connection,
    *,
    title: str,
    artist: str,
    material: str,
    description: str,
    lat: float,
    lng: float,
    stage_id: int,
    created_at: str,
) -> int:
    return await db.execute(
        conn,
        "INSERT INTO sculptures (title, artist, material, description, lat, lng, stage_id, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (title, artist, material, description, lat, lng, stage_id, created_at),
    )


async def update_sculpture(
    conn: aiosqlite.Connection,
    sculpture_id: int,
    *,
    title: str,
    artist: str,
    material: str,
    description: str,
    lat: float,
    lng: float,
    stage_id: int,
) -> None:
    await db.execute(
        conn,
        "UPDATE sculptures SET title = ?, artist = ?, material = ?, description = ?,"
        " lat = ?, lng = ?, stage_id = ? WHERE id = ?",
        (title, artist, material, description, lat, lng, stage_id, sculpture_id),
    )


async def delete_sculpture(conn: aiosqlite.Connection, sculpture_id: int) -> None:
    await db.execute(conn, "DELETE FROM sculptures WHERE id = ?", (sculpture_id,))


# --- feedback --------------------------------------------------------------


async def list_feedback(conn: aiosqlite.Connection, sculpture_id: int) -> list[dict[str, Any]]:
    return await db.fetch_all(
        conn,
        """
        SELECT f.id, f.sculpture_id, f.rating, f.comment, f.created_at,
               u.display_name AS author, u.id AS user_id
        FROM feedback f
        JOIN users u ON u.id = f.user_id
        WHERE f.sculpture_id = ?
        ORDER BY f.created_at DESC, f.id DESC
        """,
        (sculpture_id,),
    )


async def feedback_stats(conn: aiosqlite.Connection, sculpture_id: int) -> dict[str, Any]:
    row = await db.fetch_one(
        conn,
        "SELECT COUNT(*) AS count, ROUND(AVG(rating), 2) AS average FROM feedback"
        " WHERE sculpture_id = ?",
        (sculpture_id,),
    )
    if not row:
        return {"count": 0, "average": None}
    return {"count": int(row["count"] or 0), "average": row["average"]}


async def create_feedback(
    conn: aiosqlite.Connection,
    *,
    sculpture_id: int,
    user_id: int,
    rating: int,
    comment: str,
    created_at: str,
) -> int:
    return await db.execute(
        conn,
        "INSERT INTO feedback (sculpture_id, user_id, rating, comment, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (sculpture_id, user_id, rating, comment, created_at),
    )


async def get_feedback(conn: aiosqlite.Connection, feedback_id: int) -> dict[str, Any] | None:
    return await db.fetch_one(
        conn,
        """
        SELECT f.id, f.sculpture_id, f.rating, f.comment, f.created_at,
               u.display_name AS author, u.id AS user_id
        FROM feedback f JOIN users u ON u.id = f.user_id
        WHERE f.id = ?
        """,
        (feedback_id,),
    )


# --- trail-wide aggregates -------------------------------------------------


async def trail_stats(conn: aiosqlite.Connection) -> dict[str, Any]:
    row = await db.fetch_one(
        conn,
        """
        SELECT
            (SELECT COUNT(*) FROM sculptures) AS sculpture_count,
            (SELECT COUNT(*) FROM trail_stages) AS stage_count,
            (SELECT COUNT(*) FROM feedback) AS feedback_count,
            (SELECT ROUND(AVG(rating), 2) FROM feedback) AS average_rating
        """,
    )
    return row or {
        "sculpture_count": 0,
        "stage_count": 0,
        "feedback_count": 0,
        "average_rating": None,
    }
