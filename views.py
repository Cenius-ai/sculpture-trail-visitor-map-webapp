"""Server-side rendering helpers: Jinja environment, date filters, page context."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sanic import Request
from sanic.response import HTTPResponse, html

WEB_DIR = Path(__file__).resolve().parent / "web"

env = Environment(
    loader=FileSystemLoader(str(WEB_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def human_date(value: Any) -> str:
    """Humanised date: Today / Yesterday / N days ago / 12 Jun 2025."""
    if not value:
        return ""
    try:
        moment = datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return str(value)
    today = datetime.now(timezone.utc).date()
    days = (today - moment.date()).days
    if days <= 0:
        return "Today"
    if days == 1:
        return "Yesterday"
    if days < 30:
        return f"{days} days ago"
    return f"{moment.day} {moment.strftime('%b %Y')}"


def short_date(value: Any) -> str:
    if not value:
        return ""
    try:
        moment = datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return str(value)
    return f"{moment.day} {moment.strftime('%b %Y')}"


def rating_label(value: Any) -> str:
    if value is None:
        return "No ratings yet"
    return f"{float(value):.1f} / 5"


def star_string(value: Any) -> str:
    """Five-star glyph string for a 0-5 average."""
    if value is None or value == "":
        return "☆☆☆☆☆"
    try:
        filled = int(round(float(value)))
    except (TypeError, ValueError):
        return "☆☆☆☆☆"
    filled = max(0, min(5, filled))
    return "★" * filled + "☆" * (5 - filled)


def coordinate(value: Any, positive: str, negative: str) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    hemisphere = positive if number >= 0 else negative
    return f"{abs(number):.4f}° {hemisphere}"


env.filters["human_date"] = human_date
env.filters["short_date"] = short_date
env.filters["rating_label"] = rating_label
env.filters["coordinate"] = coordinate
env.filters["stars"] = star_string

DEMO_ACCOUNT = {"email": "cenius@cenius.ai", "password": "cenius"}
VISITOR_ACCOUNT = {"email": "visitor@example.com", "password": "trail1234"}


def public_user(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        "id": int(row["id"]),
        "email": row["email"],
        "username": row["username"],
        "display_name": row["display_name"],
        "is_curator": bool(int(row["is_curator"])),
    }


def trail_bounds(sculptures: list[dict[str, Any]]) -> dict[str, float]:
    """Bounding box used by the local SVG projection."""
    if not sculptures:
        return {"min_lat": 53.3400, "max_lat": 53.3560, "min_lng": -1.8420, "max_lng": -1.8180}
    lats = [float(row["lat"]) for row in sculptures]
    lngs = [float(row["lng"]) for row in sculptures]
    pad_lat = max((max(lats) - min(lats)) * 0.12, 0.0004)
    pad_lng = max((max(lngs) - min(lngs)) * 0.12, 0.0006)
    return {
        "min_lat": min(lats) - pad_lat,
        "max_lat": max(lats) + pad_lat,
        "min_lng": min(lngs) - pad_lng,
        "max_lng": max(lngs) + pad_lng,
    }


def base_context(
    request: Request,
    *,
    stages: list[dict[str, Any]] | None = None,
    sculptures: list[dict[str, Any]] | None = None,
    title: str = "Trail map",
) -> dict[str, Any]:
    stages = stages or []
    sculptures = sculptures or []
    palette_items: list[dict[str, str]] = [
        {"label": "Trail map", "hint": "Dashboard", "href": "/", "kind": "Page"},
    ]
    for stage in stages:
        palette_items.append(
            {
                "label": stage["name"],
                "hint": f"Stage {stage['sequence']} · {stage['sculpture_count']} sculptures",
                "href": f"/stages/{int(stage['id'])}",
                "kind": "Stage",
            }
        )
    for sculpture in sculptures:
        palette_items.append(
            {
                "label": sculpture["title"],
                "hint": f"{sculpture['artist']} · {sculpture['stage_name']}",
                "href": f"/sculptures/{int(sculpture['id'])}",
                "kind": "Sculpture",
            }
        )
    current_user = public_user(getattr(request.ctx, "user", None))
    if current_user and current_user["is_curator"]:
        palette_items.append(
            {"label": "Curator studio", "hint": "Manage sculptures and stages", "href": "/curator", "kind": "Page"}
        )
    return {
        "request_path": request.path,
        "user": current_user,
        "nav_stages": stages,
        "palette_items": palette_items,
        "page_title": title,
        "demo_account": DEMO_ACCOUNT,
        "visitor_account": VISITOR_ACCOUNT,
    }


def render(
    request: Request,
    template: str,
    *,
    status: int = 200,
    headers: dict[str, str] | None = None,
    **context: Any,
) -> HTTPResponse:
    markup = env.get_template(template).render(**context)
    return html(markup, status=status, headers=headers or {})
