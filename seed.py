"""Idempotent demo seed for the Sculpture Trail Visitor Map.

Runs on the normal boot path (so a fresh clone boots populated) and as its own
command (``python3 seed.py``) which exits without starting the HTTP server.
Re-running it never duplicates rows and always leaves the documented demo
credentials working.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from envfile import load_environment

load_environment()

import auth  # noqa: E402  (imported after .env is loaded)
import db
import repo

DEMO_PASSWORD = "cenius"
VISITOR_PASSWORD = "trail1234"

SEED_USERS = [
    {
        "email": "cenius@cenius.ai",
        "username": "cenius",
        "display_name": "Cenius Trail Office",
        "password": DEMO_PASSWORD,
        "is_curator": True,
    },
    {
        "email": "curator@example.com",
        "username": "mara",
        "display_name": "Mara Whitfield",
        "password": VISITOR_PASSWORD,
        "is_curator": True,
    },
    {
        "email": "visitor@example.com",
        "username": "rowan",
        "display_name": "Rowan Hale",
        "password": VISITOR_PASSWORD,
        "is_curator": False,
    },
    {
        "email": "jules@example.com",
        "username": "jules",
        "display_name": "Jules Abernathy",
        "password": VISITOR_PASSWORD,
        "is_curator": False,
    },
    {
        "email": "nadia@example.com",
        "username": "nadia",
        "display_name": "Nadia Osei",
        "password": VISITOR_PASSWORD,
        "is_curator": False,
    },
    {
        "email": "ted@example.com",
        "username": "ted",
        "display_name": "Ted Lindqvist",
        "password": VISITOR_PASSWORD,
        "is_curator": False,
    },
]

SEED_STAGES = [
    {
        "name": "Gatehouse Approach",
        "sequence": 1,
        "description": (
            "The first easy half-mile of rolled gravel from the visitor hut to the old "
            "gatehouse, where three pieces frame the estuary mouth."
        ),
        "accessibility_notes": (
            "Level rolled gravel with a 1:14 gradient over the final 120 m. Two benches and a "
            "wheelchair turning circle sit at the gatehouse. The 2.0 m gateway takes scooters "
            "and double buggies but not mobility scooters wider than 1.1 m."
        ),
        "days_ago": 210,
    },
    {
        "name": "Meadow Loop",
        "sequence": 2,
        "description": (
            "A single-track loop through the hay meadow that opens onto the headland, with "
            "three pieces spaced along the cut path."
        ),
        "accessibility_notes": (
            "Short-mown grass over a firm sub-base, 1.2 m clear at the meadow gate. Expect "
            "40 mm of standing water after heavy rain. Wheelchairs stop at the gate: the ridge "
            "viewing point overlooks two of the three meadow pieces from a level platform."
        ),
        "days_ago": 205,
    },
    {
        "name": "Quarry Ridge",
        "sequence": 3,
        "description": (
            "The climb to the disused flagstone quarry, the longest and steepest stage, with "
            "slate and limestone pieces set among the spoil heaps."
        ),
        "accessibility_notes": (
            "Steep stone-pitched path with a 1:6 section over 60 m and a handrail on the uphill "
            "side only. Not suitable for wheelchairs or buggies. Two resting ledges on the way "
            "up; the ridge platform is 1.4 m wide with a 1.1 m guard rail."
        ),
        "days_ago": 198,
    },
]

SEED_SCULPTURES = [
    {
        "title": "Corten Arc",
        "artist": "Mara Ellison",
        "material": "Weathering steel",
        "stage": "Gatehouse Approach",
        "lat": 53.3422,
        "lng": -1.8391,
        "description": (
            "A four-metre arc of 12 mm weathering steel that rusts through a decade of salt air. "
            "Stand beneath it at low tide and the curve frames the estuary mouth exactly."
        ),
        "days_ago": 200,
    },
    {
        "title": "Lantern Field",
        "artist": "Priya Raman",
        "material": "Cast glass, oak and brass",
        "stage": "Gatehouse Approach",
        "lat": 53.3431,
        "lng": -1.8364,
        "description": (
            "Forty small cast-glass lanterns strung on oak staves. They glow at dusk without "
            "power, and the staves are replaced every four years by the artist's workshop."
        ),
        "days_ago": 196,
    },
    {
        "title": "Tally Stone",
        "artist": "Dougal MacBride",
        "material": "Granite and bronze",
        "stage": "Gatehouse Approach",
        "lat": 53.3440,
        "lng": -1.8338,
        "description": (
            "A quarried granite block carved with 1,014 tally marks, one for every visitor in "
            "the trail's first logbook, with the final mark cast in bronze."
        ),
        "days_ago": 191,
    },
    {
        "title": "Paper Birch Chorus",
        "artist": "Ade Okonjo",
        "material": "Anodised aluminium",
        "stage": "Meadow Loop",
        "lat": 53.3470,
        "lng": -1.8295,
        "description": (
            "Seven aluminium trunks lean into the wind at the angle the coastal birches take. "
            "Each tube rings a single note once the wind reaches force four."
        ),
        "days_ago": 186,
    },
    {
        "title": "Hollow Bell",
        "artist": "Saskia Lind",
        "material": "Bronze and hemp rope",
        "stage": "Meadow Loop",
        "lat": 53.3488,
        "lng": -1.8268,
        "description": (
            "A cast bronze bell with no clapper, hung from a hemp-rope tripod. Visitors strike "
            "the rim with the rubber mallet that hangs beside it — the note lasts nine seconds."
        ),
        "days_ago": 180,
    },
    {
        "title": "Reed Measure",
        "artist": "Ines Kowalski",
        "material": "Stainless steel rod",
        "stage": "Meadow Loop",
        "lat": 53.3504,
        "lng": -1.8239,
        "description": (
            "Two hundred stainless rods set to the seasonal heights of the marsh reed, so the "
            "piece reads as a wave in wind and as a ruler when the air is still."
        ),
        "days_ago": 172,
    },
    {
        "title": "Slate Loom",
        "artist": "Nils Haugen",
        "material": "Split slate",
        "stage": "Quarry Ridge",
        "lat": 53.3531,
        "lng": -1.8211,
        "description": (
            "Split slate shards threaded onto stainless cable and woven into the shape of a "
            "loom that never stops. The slate came from the spoil at the artist's feet."
        ),
        "days_ago": 165,
    },
    {
        "title": "Quarry Choir",
        "artist": "Tomás Reyes",
        "material": "Limestone",
        "stage": "Quarry Ridge",
        "lat": 53.3552,
        "lng": -1.8192,
        "description": (
            "Five limestone figures cut from blocks left in the quarry when it closed in 1938, "
            "arranged so the wind funnels between them and carries a low hum up the ridge."
        ),
        "days_ago": 158,
    },
]

SEED_FEEDBACK = [
    {
        "sculpture": "Corten Arc",
        "email": "visitor@example.com",
        "rating": 5,
        "days_ago": 12,
        "comment": (
            "Walked the whole trail in one go and came back to this one twice. The way the rust "
            "takes the light at four in the afternoon is the best thing on the headland."
        ),
    },
    {
        "sculpture": "Corten Arc",
        "email": "jules@example.com",
        "rating": 4,
        "days_ago": 26,
        "comment": "Beautiful and simple. I would love a bench on the seaward side to sit and watch it.",
    },
    {
        "sculpture": "Corten Arc",
        "email": "nadia@example.com",
        "rating": 5,
        "days_ago": 41,
        "comment": "Brought my dad, who uses a walking frame. The rolled gravel path made this the easiest stage for him.",
    },
    {
        "sculpture": "Lantern Field",
        "email": "jules@example.com",
        "rating": 4,
        "days_ago": 9,
        "comment": "Come at dusk. In full sun the glass looks plain; once the light drops it turns into a field of lamps.",
    },
    {
        "sculpture": "Tally Stone",
        "email": "ted@example.com",
        "rating": 3,
        "days_ago": 18,
        "comment": (
            "The story is wonderful but the bronze mark is hard to find. A small plaque at eye "
            "height would make it much clearer."
        ),
    },
    {
        "sculpture": "Paper Birch Chorus",
        "email": "nadia@example.com",
        "rating": 5,
        "days_ago": 6,
        "comment": "It was blowing a gale and the tubes were humming all around us. My kids refused to leave.",
    },
    {
        "sculpture": "Paper Birch Chorus",
        "email": "visitor@example.com",
        "rating": 4,
        "days_ago": 33,
        "comment": "Clever, quiet piece. The meadow gate is tight with a buggy but we got through.",
    },
    {
        "sculpture": "Hollow Bell",
        "email": "ted@example.com",
        "rating": 5,
        "days_ago": 15,
        "comment": "Rang it four times. Could hear it from the far side of the meadow — that is the point, I think.",
    },
    {
        "sculpture": "Reed Measure",
        "email": "jules@example.com",
        "rating": 3,
        "days_ago": 22,
        "comment": (
            "Lovely in wind, slightly lost in calm air. Worth the walk but do it on a breezy day."
        ),
    },
    {
        "sculpture": "Slate Loom",
        "email": "nadia@example.com",
        "rating": 5,
        "days_ago": 4,
        "comment": (
            "My favourite of the eight. The slate is the same stone under your feet, which makes "
            "the whole ridge feel like part of the piece."
        ),
    },
    {
        "sculpture": "Slate Loom",
        "email": "ted@example.com",
        "rating": 4,
        "days_ago": 30,
        "comment": "Steep climb for these knees, but the handrail helps. Take the ridge slowly.",
    },
    {
        "sculpture": "Quarry Choir",
        "email": "visitor@example.com",
        "rating": 4,
        "days_ago": 11,
        "comment": "The hum is real — we stood between the third and fourth figure and felt it more than heard it.",
    },
    {
        "sculpture": "Quarry Choir",
        "email": "jules@example.com",
        "rating": 5,
        "days_ago": 37,
        "comment": "The light at the top of the quarry at sunset is worth the climb by itself.",
    },
    {
        "sculpture": "Tally Stone",
        "email": "nadia@example.com",
        "rating": 4,
        "days_ago": 44,
        "comment": "Great first stop while you read the trail map. The gatehouse shelter is a good place for a flask.",
    },
]


def _timestamp(days_ago: int, hours: int = 10) -> str:
    moment = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return (moment.replace(hour=hours, minute=15, second=0, microsecond=0)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


async def _seed_users(conn) -> dict[str, dict]:
    users: dict[str, dict] = {}
    for spec in SEED_USERS:
        existing = await repo.get_user_by_email(conn, spec["email"])
        if existing is None:
            await repo.create_user(
                conn,
                email=spec["email"],
                username=spec["username"],
                display_name=spec["display_name"],
                password_hash=auth.hash_password(spec["password"]),
                is_curator=spec["is_curator"],
                created_at=_timestamp(240),
            )
            existing = await repo.get_user_by_email(conn, spec["email"])
        elif not auth.verify_password(existing["password_hash"], spec["password"]):
            # Keep the documented demo credentials working across re-seeds.
            await repo.update_user_password(
                conn, existing["id"], auth.hash_password(spec["password"])
            )
            existing = await repo.get_user_by_email(conn, spec["email"])
        if existing is not None:
            users[spec["email"]] = existing
    return users


async def _seed_stages(conn) -> dict[str, dict]:
    stages: dict[str, dict] = {}
    for spec in SEED_STAGES:
        existing = await repo.get_stage_by_name(conn, spec["name"])
        if existing is None:
            stage_id = await repo.create_stage(
                conn,
                name=spec["name"],
                sequence=spec["sequence"],
                description=spec["description"],
                accessibility_notes=spec["accessibility_notes"],
                created_at=_timestamp(spec["days_ago"]),
            )
            existing = await repo.get_stage(conn, stage_id)
        if existing is not None:
            stages[spec["name"]] = existing
    return stages


async def _seed_sculptures(conn, stages: dict[str, dict]) -> dict[str, dict]:
    sculptures: dict[str, dict] = {}
    for spec in SEED_SCULPTURES:
        stage = stages.get(spec["stage"])
        if stage is None:
            raise RuntimeError(f"seed stage missing before sculpture {spec['title']!r}")
        existing = await repo.get_sculpture_by_title(conn, spec["title"])
        if existing is None:
            sculpture_id = await repo.create_sculpture(
                conn,
                title=spec["title"],
                artist=spec["artist"],
                material=spec["material"],
                description=spec["description"],
                lat=spec["lat"],
                lng=spec["lng"],
                stage_id=int(stage["id"]),
                created_at=_timestamp(spec["days_ago"]),
            )
            existing = await repo.get_sculpture(conn, sculpture_id)
        if existing is not None:
            sculptures[spec["title"]] = existing
    return sculptures


async def _seed_feedback(conn, users: dict[str, dict], sculptures: dict[str, dict]) -> int:
    inserted = 0
    for spec in SEED_FEEDBACK:
        sculpture = sculptures.get(spec["sculpture"])
        user = users.get(spec["email"])
        if sculpture is None or user is None:
            continue
        already = await db.fetch_one(
            conn,
            "SELECT id FROM feedback WHERE sculpture_id = ? AND user_id = ? AND comment = ?",
            (int(sculpture["id"]), int(user["id"]), spec["comment"]),
        )
        if already is not None:
            continue
        await repo.create_feedback(
            conn,
            sculpture_id=int(sculpture["id"]),
            user_id=int(user["id"]),
            rating=spec["rating"],
            comment=spec["comment"],
            created_at=_timestamp(spec["days_ago"], hours=9 + (spec["days_ago"] % 8)),
        )
        inserted += 1
    return inserted


async def ensure_seed() -> dict[str, int]:
    """Insert any missing demo rows. Safe to call on every boot."""
    await db.init_db()
    async with db.connect() as conn:
        users = await _seed_users(conn)
        stages = await _seed_stages(conn)
        sculptures = await _seed_sculptures(conn, stages)
        new_feedback = await _seed_feedback(conn, users, sculptures)
        stats = await repo.trail_stats(conn)
    return {
        "users": len(users),
        "stages": len(stages),
        "sculptures": len(sculptures),
        "feedback_added": new_feedback,
        "feedback_total": int(stats.get("feedback_count") or 0),
    }


async def _main() -> None:
    summary = await ensure_seed()
    print(
        "Seeded database {path}: {users} demo accounts, {stages} stages, "
        "{sculptures} sculptures, {feedback_total} feedback entries "
        "({feedback_added} added).".format(path=db.DB_PATH, **summary)
    )
    print("Demo accounts are printed on the sign-in page and in README.md.")


if __name__ == "__main__":
    asyncio.run(_main())
