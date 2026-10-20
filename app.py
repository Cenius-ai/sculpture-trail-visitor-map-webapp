"""Sculpture Trail Visitor Map — Sanic application entrypoint.

One process serves the JSON API, the server-rendered pages, and the static
assets. The database is created and seeded on the normal boot path, so a fresh
clone with no .env and no database file boots straight into a working app.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from envfile import load_environment

load_environment()  # makes an install-generated .env effective; safe when absent

from sanic import Sanic, Request
from sanic.exceptions import NotFound, SanicException
from sanic.log import logger
from sanic.response import HTTPResponse, json, text

import auth
import db
import routes
import seed
import views
from errors import ApiError, forbidden

BASE_DIR = Path(__file__).resolve().parent

app = Sanic("sculpture_trail_map")
app.config.REQUEST_MAX_SIZE = 1_000_000
app.config.KEEP_ALIVE = True

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; "
    "img-src 'self' data:; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; "
    "connect-src 'self'; form-action 'self'"
)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
}


def is_api(request: Request) -> bool:
    return request.path.startswith("/api/")


def check_same_origin(request: Request) -> None:
    """CSRF defence: state-changing calls must come from this origin."""
    origin = request.headers.get("origin")
    if origin:
        if urlparse(origin).netloc != request.host:
            raise forbidden("Cross-site requests are not allowed.")
    fetch_site = request.headers.get("sec-fetch-site")
    if fetch_site and fetch_site not in ("same-origin", "none"):
        raise forbidden("Cross-site requests are not allowed.")


@app.on_request
async def attach_identity(request: Request):
    request.ctx.user = await auth.resolve_user(request)
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        check_same_origin(request)


@app.on_response
async def harden_response(request: Request, response: HTTPResponse):
    for header, value in SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)
    if request.path.startswith("/static/"):
        response.headers.setdefault("Cache-Control", "public, max-age=3600")


@app.exception(ApiError)
async def handle_api_error(request: Request, exception: ApiError):
    return json(exception.to_dict(), status=exception.status_code)


@app.exception(NotFound)
async def handle_not_found(request: Request, exception: NotFound):
    if is_api(request):
        return json(
            {"error": {"code": "not_found", "message": "That endpoint does not exist."}},
            status=404,
        )
    return views.render(
        request,
        "not_found.html",
        message="That page is not on the trail.",
        status=404,
        **views.base_context(request, title="Not found"),
    )


@app.exception(SanicException)
async def handle_sanic_exception(request: Request, exception: SanicException):
    status = exception.status_code or 500
    if is_api(request):
        return json(
            {
                "error": {
                    "code": "request_failed",
                    "message": exception.message or "That request could not be completed.",
                }
            },
            status=status,
        )
    if status == 404:
        return await handle_not_found(request, NotFound(exception.message or "Not found"))
    return views.render(
        request,
        "error.html",
        status_code=status,
        message=exception.message or "That request could not be completed.",
        status=status,
        **views.base_context(request, title="Something went wrong"),
    )


@app.exception(Exception)
async def handle_unexpected(request: Request, exception: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.path)
    if is_api(request):
        return json(
            {"error": {"code": "server_error", "message": "Something went wrong on our side."}},
            status=500,
        )
    return views.render(
        request,
        "error.html",
        status_code=500,
        message="Something went wrong on our side. Please try again.",
        status=500,
        **views.base_context(request, title="Something went wrong"),
    )


app.static("/static", str(BASE_DIR / "web" / "static"), name="static")


@app.get("/health")
async def health(request: Request):
    return text("ok")


@app.before_server_start
async def prepare_trail(app: Sanic, loop):
    if getattr(app.ctx, "booted", False):
        return
    await db.init_db()
    summary = await seed.ensure_seed()
    app.ctx.booted = True
    app.ctx.seed_summary = summary
    logger.info(
        "Trail ready at %s — %s sculptures, %s stages, %s feedback entries",
        db.DB_PATH,
        summary["sculptures"],
        summary["stages"],
        summary["feedback_total"],
    )


routes.register(app)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    print(f"Sculpture Trail Visitor Map listening on 0.0.0.0:{port}", flush=True)
    app.run(host="0.0.0.0", port=port, single_process=True, motd=False, access_log=True)
