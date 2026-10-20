"""Visitor feedback per sculpture: read the list, submit a rating and comment."""

from __future__ import annotations

from sanic import Blueprint, Request
from sanic.response import json

import auth
import db
import repo
from errors import not_found
from validation import Form, json_body

bp = Blueprint("feedback", url_prefix="/api")


def feedback_payload(row: dict) -> dict:
    return {
        "id": int(row["id"]),
        "sculpture_id": int(row["sculpture_id"]),
        "rating": int(row["rating"]),
        "comment": row["comment"],
        "created_at": row["created_at"],
        "author": row["author"],
    }


def stats_payload(stats: dict) -> dict:
    return {
        "count": int(stats["count"]),
        "average": float(stats["average"]) if stats["average"] is not None else None,
    }


@bp.get("/sculptures/<sculpture_id:int>/feedback")
async def list_feedback(request: Request, sculpture_id: int):
    auth.require_user(request)
    async with db.connect() as conn:
        if await repo.get_sculpture(conn, sculpture_id) is None:
            raise not_found("That sculpture could not be found.")
        rows = await repo.list_feedback(conn, sculpture_id)
        stats = await repo.feedback_stats(conn, sculpture_id)
    return json(
        {
            "feedback": [feedback_payload(row) for row in rows],
            "stats": stats_payload(stats),
        }
    )


@bp.post("/sculptures/<sculpture_id:int>/feedback")
async def create_feedback(request: Request, sculpture_id: int):
    user = auth.require_user(request)
    data = await json_body(request)
    form = Form(data)
    rating = form.integer("rating", "A star rating", minimum=1, maximum=5)
    comment = form.text("comment", "A comment", min_len=3, max_len=1000)
    form.raise_if_invalid("Choose a rating and add a comment before submitting.")

    async with db.connect() as conn:
        if await repo.get_sculpture(conn, sculpture_id) is None:
            raise not_found("That sculpture could not be found.")
        feedback_id = await repo.create_feedback(
            conn,
            sculpture_id=sculpture_id,
            user_id=int(user["id"]),
            rating=rating,
            comment=comment,
            created_at=auth.utc_timestamp(),
        )
        row = await repo.get_feedback(conn, feedback_id)
        stats = await repo.feedback_stats(conn, sculpture_id)
    return json(
        {"feedback": feedback_payload(row), "stats": stats_payload(stats)}, status=201
    )
