"""Service layer: account creation and sign-in rules shared by the JSON API
and the server-rendered form fallbacks."""

from __future__ import annotations

import secrets

import aiosqlite

import auth
import repo
import validation
from errors import conflict
from validation import Form

MIN_PASSWORD_LENGTH = 8


async def unique_username(conn: aiosqlite.Connection, base: str) -> str:
    candidate = base
    for _ in range(40):
        if await repo.get_user_by_username(conn, candidate) is None:
            return candidate
        candidate = f"{base[:16]}{secrets.randbelow(9000) + 1000}"
    raise conflict("That email cannot be used for a new account. Try a different one.")


async def register(
    conn: aiosqlite.Connection, data: dict
) -> tuple[dict, str]:
    """Validate a registration payload, create the account, and open a session."""
    form = Form(data)
    display_name = form.text("display_name", "Your name", min_len=2, max_len=60)
    email = form.email()
    password = data.get("password") if isinstance(data.get("password"), str) else ""
    confirmation = data.get("password_confirm") if isinstance(data.get("password_confirm"), str) else ""
    validation.validate_password_matches(password or "", confirmation, form)
    form.raise_if_invalid("Check your name, email, and password.")

    if await repo.get_user_by_email(conn, email) is not None:
        raise conflict("An account with that email already exists. Sign in instead.")

    username = await unique_username(conn, validation.slug_username(email))
    user_id = await repo.create_user(
        conn,
        email=email,
        username=username,
        display_name=display_name,
        password_hash=auth.hash_password(password),
        is_curator=False,
        created_at=auth.utc_timestamp(),
    )
    user = await repo.get_user(conn, user_id)
    token = await auth.issue_session(conn, user_id)
    return user, token


async def authenticate(
    conn: aiosqlite.Connection, identifier: str, password: str
) -> dict | None:
    """Return the user row when the credential pair matches, else None."""
    user = await repo.get_user_by_login(conn, identifier)
    if user is None:
        return None
    if not auth.verify_password(user["password_hash"], password):
        return None
    return user
