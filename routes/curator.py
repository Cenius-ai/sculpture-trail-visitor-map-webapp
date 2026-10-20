"""Curator-only write API for sculptures and trail stages.

Every handler re-checks the curator flag server-side; the client never decides
who may write. Field-level validation runs before any SQL is issued.
"""

from __future__ import annotations

import aiosqlite
from sanic import Blueprint, Request
from sanic.response import json

import auth
import db
import repo
from errors import conflict, invalid, not_found
from routes.content import sculpture_payload, stage_payload
from validation import Form, json_body

bp = Blueprint("curator", url_prefix="/api")

SHORT_TEXT = 90
LONG_TEXT = 400


def read_stage(data: dict) -> dict:
    """Validate stage fields and return the writable allowlist."""
    form = Form(data)
    values = {
        "name": form.text("name", "A stage name", min_len=3, max_len=80),
        "sequence": form.integer("sequence", "A stage number", minimum=1, maximum=99),
        "description": form.text("description", "A short description", min_len=10, max_len=LONG_TEXT),
        "accessibility_notes": form.text(
            "accessibility_notes", "Accessibility notes", min_len=10, max_len=LONG_TEXT
        ),
    }
    form.raise_if_invalid("Check the stage details before saving.")
    return values


def read_sculpture(data: dict) -> dict:
    """Validate sculpture fields and return the writable allowlist."""
    form = Form(data)
    values = {
        "title": form.text("title", "A title", min_len=2, max_len=SHORT_TEXT),
        "artist": form.text("artist", "An artist name", min_len=2, max_len=SHORT_TEXT),
        "material": form.text("material", "A material", min_len=2, max_len=SHORT_TEXT),
        "description": form.text("description", "A description", min_len=20, max_len=1000),
        "lat": form.number("lat", "Latitude", minimum=-90, maximum=90),
        "lng": form.number("lng", "Longitude", minimum=-180, maximum=180),
        "stage_id": form.integer("stage_id", "A trail stage", minimum=1, maximum=2**31),
    }
    form.raise_if_invalid("Check the sculpture details before saving.")
    return values


@bp.post("/stages")
async def create_stage(request: Request):
    auth.require_curator(request)
    values = read_stage(await json_body(request))
    async with db.connect() as conn:
        if await repo.get_stage_by_name(conn, values["name"]) is not None:
            raise invalid({"name": "A stage with that name already exists."})
        stage_id = await repo.create_stage(conn, created_at=auth.utc_timestamp(), **values)
        stage = await repo.get_stage(conn, stage_id)
    return json({"stage": stage_payload(stage)}, status=201)


@bp.patch("/stages/<stage_id:int>")
async def update_stage(request: Request, stage_id: int):
    auth.require_curator(request)
    incoming = await json_body(request)
    async with db.connect() as conn:
        existing = await repo.get_stage(conn, stage_id)
        if existing is None:
            raise not_found("That trail stage could not be found.")
        merged = {
            "name": existing["name"],
            "sequence": existing["sequence"],
            "description": existing["description"],
            "accessibility_notes": existing["accessibility_notes"],
        }
        merged.update({key: value for key, value in incoming.items() if value is not None})
        values = read_stage(merged)
        duplicate = await repo.get_stage_by_name(conn, values["name"])
        if duplicate is not None and int(duplicate["id"]) != stage_id:
            raise invalid({"name": "A stage with that name already exists."})
        await repo.update_stage(conn, stage_id, **values)
        stage = await repo.get_stage(conn, stage_id)
    return json({"stage": stage_payload(stage)})


@bp.delete("/stages/<stage_id:int>")
async def delete_stage(request: Request, stage_id: int):
    auth.require_curator(request)
    async with db.connect() as conn:
        stage = await repo.get_stage(conn, stage_id)
        if stage is None:
            raise not_found("That trail stage could not be found.")
        assigned = await repo.count_sculptures_in_stage(conn, stage_id)
        if assigned:
            raise conflict(
                f"{stage['name']} still has {assigned} sculpture"
                f"{'' if assigned == 1 else 's'} assigned. Move or delete them first."
            )
        await repo.delete_stage(conn, stage_id)
    return json({"deleted": True, "stage_id": stage_id})


@bp.post("/sculptures")
async def create_sculpture(request: Request):
    auth.require_curator(request)
    values = read_sculpture(await json_body(request))
    async with db.connect() as conn:
        if await repo.get_stage(conn, values["stage_id"]) is None:
            raise invalid({"stage_id": "Choose an existing trail stage."})
        if await repo.get_sculpture_by_title(conn, values["title"]) is not None:
            raise invalid({"title": "A sculpture with that title already exists."})
        try:
            sculpture_id = await repo.create_sculpture(
                conn, created_at=auth.utc_timestamp(), **values
            )
        except aiosqlite.IntegrityError as exc:
            raise invalid({"title": "A sculpture with that title already exists."}) from exc
        row = await repo.get_sculpture(conn, sculpture_id)
    return json({"sculpture": sculpture_payload(row)}, status=201)


@bp.patch("/sculptures/<sculpture_id:int>")
async def update_sculpture(request: Request, sculpture_id: int):
    auth.require_curator(request)
    incoming = await json_body(request)
    async with db.connect() as conn:
        existing = await repo.get_sculpture(conn, sculpture_id)
        if existing is None:
            raise not_found("That sculpture could not be found.")
        merged = {
            "title": existing["title"],
            "artist": existing["artist"],
            "material": existing["material"],
            "description": existing["description"],
            "lat": existing["lat"],
            "lng": existing["lng"],
            "stage_id": existing["stage_id"],
        }
        merged.update({key: value for key, value in incoming.items() if value is not None})
        values = read_sculpture(merged)
        if await repo.get_stage(conn, values["stage_id"]) is None:
            raise invalid({"stage_id": "Choose an existing trail stage."})
        duplicate = await repo.get_sculpture_by_title(conn, values["title"])
        if duplicate is not None and int(duplicate["id"]) != sculpture_id:
            raise invalid({"title": "A sculpture with that title already exists."})
        await repo.update_sculpture(conn, sculpture_id, **values)
        row = await repo.get_sculpture(conn, sculpture_id)
    return json({"sculpture": sculpture_payload(row)})


@bp.delete("/sculptures/<sculpture_id:int>")
async def delete_sculpture(request: Request, sculpture_id: int):
    auth.require_curator(request)
    async with db.connect() as conn:
        if await repo.get_sculpture(conn, sculpture_id) is None:
            raise not_found("That sculpture could not be found.")
        await repo.delete_sculpture(conn, sculpture_id)
    return json({"deleted": True, "sculpture_id": sculpture_id})
