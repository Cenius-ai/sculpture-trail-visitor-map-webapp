"""Authentication API: register, sign in, sign out, and the current user."""

from __future__ import annotations

from sanic import Blueprint, Request
from sanic.response import json

import auth
import db
import services
from errors import invalid, unauthorized
from validation import json_body

bp = Blueprint("auth", url_prefix="/api/auth")


def public_user(row: dict) -> dict:
    return {
        "id": int(row["id"]),
        "email": row["email"],
        "username": row["username"],
        "display_name": row["display_name"],
        "is_curator": bool(int(row["is_curator"])),
        "created_at": row["created_at"],
    }


@bp.post("/register")
async def register(request: Request):
    data = await json_body(request)
    async with db.connect() as conn:
        user, token = await services.register(conn, data)
    response = json({"user": public_user(user)}, status=201)
    return auth.attach_session(response, token)


@bp.post("/login")
async def login(request: Request):
    data = await json_body(request)
    identifier = data.get("email") or data.get("identifier") or ""
    password = data.get("password") or ""
    if not isinstance(identifier, str) or not isinstance(password, str) or not identifier.strip() or not password:
        raise invalid(
            {
                "email": "" if identifier else "Enter your email or username.",
                "password": "" if password else "Enter your password.",
            },
            "Enter your email or username and password.",
        )
    identifier = identifier.strip()

    key = auth.throttle_key(request, identifier)
    wait = auth.check_login_throttle(key)
    if wait is not None:
        response = json(
            {
                "error": {
                    "code": "too_many_attempts",
                    "message": "Too many sign-in attempts. Try again shortly.",
                }
            },
            status=429,
        )
        response.headers["Retry-After"] = str(wait)
        return response

    async with db.connect() as conn:
        user = await services.authenticate(conn, identifier, password)
        if user is None:
            auth.record_login_failure(key)
            raise unauthorized("That email and password do not match an account.")
        auth.reset_login_throttle(key)
        await auth.purge_expired_sessions(conn)
        token = await auth.issue_session(conn, int(user["id"]))
    return auth.attach_session(json({"user": public_user(user)}), token)


@bp.post("/logout")
async def logout(request: Request):
    auth.require_user(request)
    token = request.cookies.get(auth.SESSION_COOKIE)
    async with db.connect() as conn:
        if token:
            await auth.revoke_session(conn, token)
    return auth.clear_session(json({"ok": True}))


@bp.get("/me")
async def me(request: Request):
    user = auth.require_user(request)
    return json({"user": public_user(user)})
