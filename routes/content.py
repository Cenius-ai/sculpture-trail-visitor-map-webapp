"""Read APIs for trail stages and sculptures."""

from __future__ import annotations

from sanic import Blueprint, Request
from sanic.response import json

import auth
import db
import repo
from errors import invalid, not_found


def sculpture_payload(row: dict) -> dict:
    average = row.get("average_rating")
    return {
        "id": int(row["id"]),
        "title": row["title"],
        "artist": row["artist"],
        "material": row["material"],
        "description": row["description"],
        "lat": float(row["lat"]),
        "lng": float(row["lng"]),
        "created_at": row["created_at"],
        "stage": {
            "id": int(row["stage_id"]),
            "name": row["stage_name"],
            "sequence": int(row["stage_sequence"]),
            "accessibility_notes": row.get("stage_accessibility_notes", ""),
        },
        "feedback_count": int(row.get("feedback_count") or 0),
        "average_rating": float(average) if average is not None else None,
    }


def stage_payload(row: dict) -> dict:
    return {
        "id": int(row["id"]),
        "name": row["name"],
        "sequence": int(row["sequence"]),
        "description": row["description"],
        "accessibility_notes": row["accessibility_notes"],
        "created_at": row["created_at"],
        "sculpture_count": int(row.get("sculpture_count") or 0),
    }


bp = Blueprint("content", url_prefix="/api")


@bp.get("/stages")
async def list_stages(request: Request):
    auth.require_user(request)
    async with db.connect() as conn:
        rows = await repo.list_stages(conn)
    return json({"stages": [stage_payload(row) for row in rows]})


@bp.get("/stages/<stage_id:int>")
async def get_stage(request: Request, stage_id: int):
    auth.require_user(request)
    async with db.connect() as conn:
        stage = await repo.get_stage(conn, stage_id)
        if stage is None:
            raise not_found("That trail stage could not be found.")
        sculptures = await repo.list_sculptures(conn, stage_id)
    payload = stage_payload(stage)
    payload["sculptures"] = [sculpture_payload(row) for row in sculptures]
    return json({"stage": payload})


@bp.get("/sculptures")
async def list_sculptures(request: Request):
    auth.require_user(request)
    raw_stage = request.args.get("stage_id")
    stage_id = None
    if raw_stage not in (None, "", "all"):
        try:
            stage_id = int(raw_stage)
        except ValueError as exc:
            raise invalid({"stage_id": "The stage filter must be a whole number."}) from exc
    async with db.connect() as conn:
        if stage_id is not None and await repo.get_stage(conn, stage_id) is None:
            raise not_found("That trail stage could not be found.")
        rows = await repo.list_sculptures(conn, stage_id)
    return json(
        {
            "sculptures": [sculpture_payload(row) for row in rows],
            "count": len(rows),
            "stage_id": stage_id,
        }
    )


@bp.get("/sculptures/<sculpture_id:int>")
async def get_sculpture(request: Request, sculpture_id: int):
    auth.require_user(request)
    async with db.connect() as conn:
        row = await repo.get_sculpture(conn, sculpture_id)
        if row is None:
            raise not_found("That sculpture could not be found.")
        stats = await repo.feedback_stats(conn, sculpture_id)
    payload = sculpture_payload(row)
    payload["average_rating"] = (
        float(stats["average"]) if stats["average"] is not None else None
    )
    payload["feedback_count"] = int(stats["count"])
    return json({"sculpture": payload})
