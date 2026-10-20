"""Authentication: scrypt password hashes, DB-backed sessions, access guards.

Passwords are hashed with scrypt and a per-user random salt. A sign-in issues a
random 256-bit session token; only its HMAC-SHA256 digest is stored, so a
database read never yields a usable token and sign-out genuinely revokes the
session server-side. The cookie is HttpOnly and SameSite=Lax, with ``Secure``
env-gated so the plain-HTTP preview can sign in.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any

import aiosqlite
from sanic import Request
from sanic.response import HTTPResponse

import db
from errors import forbidden, unauthorized

SESSION_COOKIE = "trail_session"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 7

# Dev fallback keeps a fresh clone bootable with no .env; install.sh writes a
# generated secret into .env so a deployed instance never shares this value.
SESSION_SECRET = os.getenv("SESSION_SECRET") or "cenius-dev-4f7a19c2b8d35e60"
COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_DKLEN = 32


def _now() -> datetime:
    return datetime.now(timezone.utc)


def utc_timestamp(moment: datetime | None = None) -> str:
    return (moment or _now()).strftime("%Y-%m-%d %H:%M:%S")


# --- passwords -------------------------------------------------------------


def hash_password(password: str) -> str:
    """Hash a password with scrypt and a fresh 16-byte salt."""
    salt = os.urandom(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_DKLEN,
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(stored_hash: str, attempt: str) -> bool:
    """Constant-time verification of a password against a stored scrypt hash."""
    try:
        scheme, n, r, p, salt_hex, digest_hex = stored_hash.split("$")
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(
            attempt.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(digest_hex) // 2,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


# --- sessions --------------------------------------------------------------


def _token_digest(token: str) -> str:
    return hmac.new(SESSION_SECRET.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()


async def issue_session(conn: aiosqlite.Connection, user_id: int) -> str:
    """Create a session row and return the raw token for the cookie."""
    token = secrets.token_urlsafe(32)
    expires_at = utc_timestamp(_now() + timedelta(seconds=SESSION_TTL_SECONDS))
    await db.execute(
        conn,
        "INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (_token_digest(token), int(user_id), utc_timestamp(), expires_at),
    )
    return token


async def revoke_session(conn: aiosqlite.Connection, token: str) -> None:
    await db.execute(conn, "DELETE FROM sessions WHERE token_hash = ?", (_token_digest(token),))


async def purge_expired_sessions(conn: aiosqlite.Connection) -> None:
    await db.execute(conn, "DELETE FROM sessions WHERE expires_at <= ?", (utc_timestamp(),))


async def session_user(conn: aiosqlite.Connection, token: str) -> dict[str, Any] | None:
    return await db.fetch_one(
        conn,
        """
        SELECT u.id, u.email, u.username, u.display_name, u.is_curator, u.created_at
        FROM sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token_hash = ? AND s.expires_at > ?
        """,
        (_token_digest(token), utc_timestamp()),
    )


def attach_session(response: HTTPResponse, token: str) -> HTTPResponse:
    response.add_cookie(
        SESSION_COOKIE,
        token,
        path="/",
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="Lax",
        secure=COOKIE_SECURE,
    )
    return response


def clear_session(response: HTTPResponse) -> HTTPResponse:
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


# --- request identity ------------------------------------------------------


async def resolve_user(request: Request) -> dict[str, Any] | None:
    """Load the signed-in user for this request, if any."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    async with db.connect() as conn:
        return await session_user(conn, token)


def require_user(request: Request) -> dict[str, Any]:
    user = getattr(request.ctx, "user", None)
    if not user:
        raise unauthorized()
    return user


def require_curator(request: Request) -> dict[str, Any]:
    user = require_user(request)
    if int(user["is_curator"]) != 1:
        raise forbidden("Only trail curators can manage trail content.")
    return user


# --- login throttling ------------------------------------------------------

_LOGIN_WINDOW_SECONDS = 60
_LOGIN_MAX_ATTEMPTS = 10
_login_attempts: dict[str, deque[float]] = {}


def throttle_key(request: Request, identifier: str) -> str:
    peer = request.remote_addr or "unknown"
    return f"{peer}|{identifier.strip().lower()}"


def check_login_throttle(key: str) -> int | None:
    """Return seconds to wait when this peer+identifier is throttled."""
    now = time.time()
    bucket = _login_attempts.setdefault(key, deque())
    while bucket and now - bucket[0] > _LOGIN_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= _LOGIN_MAX_ATTEMPTS:
        return max(1, int(_LOGIN_WINDOW_SECONDS - (now - bucket[0])) + 1)
    return None


def record_login_failure(key: str) -> None:
    bucket = _login_attempts.setdefault(key, deque())
    bucket.append(time.time())
    if len(_login_attempts) > 512:
        for stale_key in [k for k, v in list(_login_attempts.items()) if not v][:128]:
            _login_attempts.pop(stale_key, None)


def reset_login_throttle(key: str) -> None:
    _login_attempts.pop(key, None)
