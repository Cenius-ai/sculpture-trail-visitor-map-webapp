"""HTML pages. Every page is rendered server-side with real data, then enhanced
with vanilla JS (map projection, stage filter, feedback form, curator forms).

The sign-in and sign-up pages also accept plain form posts, so the app still
works if JavaScript is unavailable: same rules, same session cookie, same
redirect.
"""

from __future__ import annotations

from urllib.parse import quote
from typing import Any

from sanic import Blueprint, Request
from sanic.response import HTTPResponse, redirect

import auth
import db
import errors
import repo
import services
import views

bp = Blueprint("pages")

FORM_FIELDS = ("display_name", "email", "password", "password_confirm")


def safe_next(raw: str | None) -> str:
    """Only allow same-site relative redirect targets."""
    if not raw or not raw.startswith("/") or raw.startswith("//"):
        return "/"
    return raw


def login_redirect(request: Request) -> HTTPResponse:
    wanted = request.path + (("?" + request.query_string) if request.query_string else "")
    return redirect(f"/login?next={quote(safe_next(wanted))}")


async def form_payload(request: Request) -> dict[str, str]:
    """Read a urlencoded form body into a flat dict of strings."""
    try:
        raw = request.form
    except Exception:  # not a form-encoded body
        return {key: "" for key in FORM_FIELDS}
    payload: dict[str, str] = {}
    for key in FORM_FIELDS:
        value: Any = raw.get(key, "")
        if isinstance(value, (list, tuple)):
            value = value[0] if value else ""
        payload[key] = value if isinstance(value, str) else ""
    return payload


def _render_login(
    request: Request,
    *,
    errors_map: dict[str, str] | None = None,
    message: str = "",
    email: str = "",
    status: int = 200,
) -> HTTPResponse:
    ctx = views.base_context(request, title="Sign in")
    return views.render(
        request,
        "login.html",
        next_url=safe_next(request.args.get("next")),
        errors=errors_map or {},
        message=message,
        email=email,
        status=status,
        **ctx,
    )


def _render_signup(
    request: Request,
    *,
    errors_map: dict[str, str] | None = None,
    message: str = "",
    values: dict[str, str] | None = None,
    status: int = 200,
) -> HTTPResponse:
    ctx = views.base_context(request, title="Create account")
    return views.render(
        request,
        "signup.html",
        next_url=safe_next(request.args.get("next")),
        errors=errors_map or {},
        message=message,
        values=values or {},
        status=status,
        **ctx,
    )


@bp.get("/login")
async def login_page(request: Request):
    if getattr(request.ctx, "user", None):
        return redirect(safe_next(request.args.get("next")))
    return _render_login(request)


@bp.post("/login")
async def login_submit(request: Request):
    data = await form_payload(request)
    identifier = data["email"].strip()
    password = data["password"]
    target = safe_next(request.args.get("next"))

    if not identifier or not password:
        return _render_login(
            request,
            errors_map={
                "email": "" if identifier else "Enter your email or username.",
                "password": "" if password else "Enter your password.",
            },
            message="Enter your email or username and password.",
            email=identifier,
            status=400,
        )

    throttle_key = auth.throttle_key(request, identifier)
    wait = auth.check_login_throttle(throttle_key)
    if wait is not None:
        return _render_login(
            request,
            message="Too many sign-in attempts. Try again shortly.",
            email=identifier,
            status=429,
        )

    async with db.connect() as conn:
        user = await services.authenticate(conn, identifier, password)
        if user is None:
            auth.record_login_failure(throttle_key)
            return _render_login(
                request,
                message="That email and password do not match an account.",
                email=identifier,
                status=401,
            )
        auth.reset_login_throttle(throttle_key)
        await auth.purge_expired_sessions(conn)
        token = await auth.issue_session(conn, int(user["id"]))
    return auth.attach_session(redirect(target), token)


@bp.get("/signup")
async def signup_page(request: Request):
    if getattr(request.ctx, "user", None):
        return redirect("/")
    return _render_signup(request)


@bp.post("/signup")
async def signup_submit(request: Request):
    data = await form_payload(request)
    target = safe_next(request.args.get("next"))
    values = {
        "display_name": data["display_name"],
        "email": data["email"],
    }
    async with db.connect() as conn:
        try:
            user, token = await services.register(conn, data)
        except errors.ApiError as exc:
            return _render_signup(
                request,
                errors_map=exc.fields,
                message="" if exc.fields else exc.message,
                values=values,
                status=exc.status_code,
            )
    return auth.attach_session(redirect(target), token)


@bp.post("/logout")
async def logout_page(request: Request):
    token = request.cookies.get(auth.SESSION_COOKIE)
    if token:
        async with db.connect() as conn:
            await auth.revoke_session(conn, token)
    return auth.clear_session(redirect("/login"))


@bp.get("/")
async def dashboard(request: Request):
    if not getattr(request.ctx, "user", None):
        return login_redirect(request)
    async with db.connect() as conn:
        stages = await repo.list_stages(conn)
        sculptures = await repo.list_sculptures(conn)
        stats = await repo.trail_stats(conn)
    ctx = views.base_context(request, stages=stages, sculptures=sculptures, title="Trail map")
    return views.render(
        request,
        "dashboard.html",
        stages=stages,
        sculptures=sculptures,
        stats=stats,
        bounds=views.trail_bounds(sculptures),
        **ctx,
    )


async def _sculpture_page(request: Request, sculpture_id: int) -> HTTPResponse:
    if not getattr(request.ctx, "user", None):
        return login_redirect(request)
    async with db.connect() as conn:
        sculpture = await repo.get_sculpture(conn, sculpture_id)
        if sculpture is None:
            return not_found_page(request, "That sculpture is not on the trail.")
        feedback = await repo.list_feedback(conn, sculpture_id)
        stats = await repo.feedback_stats(conn, sculpture_id)
        stages = await repo.list_stages(conn)
        sculptures = await repo.list_sculptures(conn)
    next_piece = _next_on_route(sculptures, sculpture_id)
    ctx = views.base_context(
        request, stages=stages, sculptures=sculptures, title=sculpture["title"]
    )
    return views.render(
        request,
        "sculpture.html",
        sculpture=sculpture,
        feedback=feedback,
        stats=stats,
        next_piece=next_piece,
        **ctx,
    )


@bp.get("/sculptures/<sculpture_id:int>")
async def sculpture_page(request: Request, sculpture_id: int):
    return await _sculpture_page(request, sculpture_id)


@bp.get("/stages/<stage_id:int>")
async def stage_page(request: Request, stage_id: int):
    if not getattr(request.ctx, "user", None):
        return login_redirect(request)
    async with db.connect() as conn:
        stage = await repo.get_stage(conn, stage_id)
        if stage is None:
            return not_found_page(request, "That trail stage could not be found.")
        stages = await repo.list_stages(conn)
        sculptures = await repo.list_sculptures(conn)
        stage_sculptures = [row for row in sculptures if int(row["stage_id"]) == stage_id]
    ctx = views.base_context(request, stages=stages, sculptures=sculptures, title=stage["name"])
    return views.render(
        request,
        "stage.html",
        stage=stage,
        stage_sculptures=stage_sculptures,
        bounds=views.trail_bounds(sculptures),
        **ctx,
    )


@bp.get("/curator")
async def curator_page(request: Request):
    user = getattr(request.ctx, "user", None)
    if not user:
        return login_redirect(request)
    async with db.connect() as conn:
        stages = await repo.list_stages(conn)
        sculptures = await repo.list_sculptures(conn)
        stats = await repo.trail_stats(conn)
    ctx = views.base_context(request, stages=stages, sculptures=sculptures, title="Curator studio")
    if int(user["is_curator"]) != 1:
        return views.render(request, "forbidden.html", status=403, **ctx)
    return views.render(
        request,
        "curator.html",
        stages=stages,
        sculptures=sculptures,
        stats=stats,
        bounds=views.trail_bounds(sculptures),
        **ctx,
    )


def _next_on_route(sculptures: list[dict], sculpture_id: int) -> dict | None:
    """The next sculpture in trail order, wrapping around at the end."""
    for index, row in enumerate(sculptures):
        if int(row["id"]) == sculpture_id:
            if len(sculptures) < 2:
                return None
            return sculptures[(index + 1) % len(sculptures)]
    return sculptures[0] if sculptures else None


def not_found_page(request: Request, message: str = "That page is not on the trail.") -> HTTPResponse:
    ctx = views.base_context(request, title="Not found")
    return views.render(request, "not_found.html", message=message, status=404, **ctx)
