"""Smoke tests for the Sculpture Trail Visitor Map.

Covers auth (register / login / logout), the seeded trail read API, sculpture
detail rendering, visitor feedback, curator CRUD with role checks, and that
user text is escaped in server-rendered HTML.
"""

from __future__ import annotations

import uuid

CURATOR = {"email": "cenius@cenius.ai", "password": "cenius"}
VISITOR = {"email": "visitor@example.com", "password": "trail1234"}


async def sign_in(client, credentials=CURATOR):
    request, response = await client.post("/api/auth/login", json=credentials)
    assert response.status == 200, response.text
    return response.json["user"]


async def sign_out(client):
    request, response = await client.post("/api/auth/logout")
    assert response.status == 200
    client.cookies.clear()


# --- basics ---------------------------------------------------------------


async def test_health_and_public_pages(client):
    request, response = await client.get("/health")
    assert response.status == 200
    assert response.text == "ok"

    request, response = await client.get("/")
    assert response.status == 302
    assert response.headers["location"].startswith("/login")

    request, response = await client.get("/login")
    assert response.status == 200
    assert "cenius@cenius.ai" in response.text
    assert "cenius" in response.text

    request, response = await client.get("/signup")
    assert response.status == 200
    assert "Create your visitor account" in response.text


async def test_protected_pages_redirect_to_login(client):
    for path in ("/", "/curator", "/stages/1", "/sculptures/1"):
        request, response = await client.get(path)
        assert response.status == 302, path
        assert response.headers["location"].startswith("/login"), path


# --- auth -----------------------------------------------------------------


async def test_register_then_me_then_logout(client):
    email = f"walker-{uuid.uuid4().hex[:8]}@example.com"
    request, response = await client.post(
        "/api/auth/register",
        json={
            "display_name": "Wren Ashby",
            "email": email,
            "password": "headland-trail",
            "password_confirm": "headland-trail",
        },
    )
    assert response.status == 201, response.text
    assert response.json["user"]["display_name"] == "Wren Ashby"
    assert response.json["user"]["is_curator"] is False

    request, response = await client.get("/api/auth/me")
    assert response.status == 200
    assert response.json["user"]["email"] == email

    request, response = await client.get("/")
    assert response.status == 200
    assert "Wren Ashby" in response.text

    request, response = await client.post("/api/auth/logout")
    assert response.status == 200
    request, response = await client.get("/api/auth/me")
    assert response.status == 401


async def test_login_rejects_bad_credentials_without_enumerating(client):
    request, wrong_password = await client.post(
        "/api/auth/login", json={"email": "cenius@cenius.ai", "password": "wrong-password"}
    )
    request, unknown_user = await client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": "wrong-password"}
    )
    assert wrong_password.status == 401
    assert unknown_user.status == 401
    assert (
        wrong_password.json["error"]["message"] == unknown_user.json["error"]["message"]
    )


async def test_login_requires_both_fields(client):
    request, response = await client.post("/api/auth/login", json={"email": "", "password": ""})
    assert response.status == 400
    assert set(response.json["error"]["fields"]) == {"email", "password"}


async def test_register_rejects_mismatched_passwords(client):
    request, response = await client.post(
        "/api/auth/register",
        json={
            "display_name": "Ivy Plume",
            "email": f"ivy-{uuid.uuid4().hex[:6]}@example.com",
            "password": "longenough1",
            "password_confirm": "longenough2",
        },
    )
    assert response.status == 400
    assert "password_confirm" in response.json["error"]["fields"]


# --- seeded trail ---------------------------------------------------------


async def test_seeded_trail_read_api(client):
    await sign_in(client, VISITOR)

    request, response = await client.get("/api/stages")
    assert response.status == 200
    stages = response.json["stages"]
    assert len(stages) >= 3
    assert [stage["sequence"] for stage in stages] == sorted(stage["sequence"] for stage in stages)
    assert all(stage["accessibility_notes"] for stage in stages)

    request, response = await client.get("/api/sculptures")
    assert response.status == 200
    sculptures = response.json["sculptures"]
    assert response.json["count"] == len(sculptures)
    assert len(sculptures) >= 8
    for sculpture in sculptures:
        assert sculpture["title"] and sculpture["artist"] and sculpture["material"]
        assert -90 <= sculpture["lat"] <= 90
        assert -180 <= sculpture["lng"] <= 180
        assert sculpture["stage"]["name"]

    corten = next(item for item in sculptures if item["title"] == "Corten Arc")
    assert corten["artist"] == "Mara Ellison"
    assert corten["material"] == "Weathering steel"


async def test_sculpture_detail_api_and_feedback(client):
    await sign_in(client, VISITOR)

    request, response = await client.get("/api/sculptures/1")
    assert response.status == 200
    sculpture = response.json["sculpture"]
    assert sculpture["title"] == "Corten Arc"
    assert sculpture["stage"]["accessibility_notes"]
    assert sculpture["average_rating"] is not None

    request, response = await client.get("/api/sculptures/1/feedback")
    assert response.status == 200
    assert response.json["stats"]["count"] >= 1
    assert all(item["author"] for item in response.json["feedback"])


async def test_stage_filter_narrows_sculptures(client):
    await sign_in(client, VISITOR)

    request, response = await client.get("/api/stages")
    meadow = next(stage for stage in response.json["stages"] if stage["name"] == "Meadow Loop")

    request, response = await client.get(f"/api/sculptures?stage_id={meadow['id']}")
    assert response.status == 200
    assert response.json["count"] >= 1
    assert all(item["stage"]["id"] == meadow["id"] for item in response.json["sculptures"])

    request, response = await client.get("/api/sculptures?stage_id=not-a-number")
    assert response.status == 400


async def test_sculpture_detail_page_renders_server_side(client):
    await sign_in(client, VISITOR)

    request, response = await client.get("/sculptures/1")
    assert response.status == 200
    body = response.text
    assert "Corten Arc" in body
    assert "Mara Ellison" in body
    assert "Weathering steel" in body
    assert "Level rolled gravel" in body  # the stage accessibility note
    assert "Feedback" in body


async def test_stage_page_lists_only_that_stage(client):
    await sign_in(client, VISITOR)

    request, response = await client.get("/stages/2")
    assert response.status == 200
    body = response.text
    assert "Meadow Loop" in body
    assert "Paper Birch Chorus" in body
    assert "Hollow Bell" in body
    assert "Reed Measure" in body
    # The stage plan only plots this stage's three sculptures.
    assert body.count('data-sculpture-id="') == 3


async def test_missing_records_return_404(client):
    await sign_in(client, VISITOR)
    request, response = await client.get("/sculptures/99999")
    assert response.status == 404
    assert "not on the trail" in response.text
    request, response = await client.get("/api/sculptures/99999")
    assert response.status == 404


# --- feedback -------------------------------------------------------------


async def test_feedback_create_persists_and_updates_average(client):
    await sign_in(client, VISITOR)
    comment = f"The salt air has already started on the bronze ({uuid.uuid4().hex[:6]})."

    request, before = await client.get("/api/sculptures/5/feedback")
    prior_count = before.json["stats"]["count"]

    request, response = await client.post(
        "/api/sculptures/5/feedback", json={"rating": 4, "comment": comment}
    )
    assert response.status == 201, response.text
    assert response.json["feedback"]["author"] == "Rowan Hale"
    assert response.json["stats"]["count"] == prior_count + 1

    request, response = await client.get("/api/sculptures/5/feedback")
    assert any(item["comment"] == comment for item in response.json["feedback"])

    request, response = await client.get("/sculptures/5")
    assert comment in response.text


async def test_feedback_validation_and_auth(client):
    request, response = await client.post(
        "/api/sculptures/1/feedback", json={"rating": 3, "comment": "Anonymous note"}
    )
    assert response.status == 401

    await sign_in(client, VISITOR)
    request, response = await client.post("/api/sculptures/1/feedback", json={})
    assert response.status == 400
    assert set(response.json["error"]["fields"]) == {"rating", "comment"}

    request, response = await client.post(
        "/api/sculptures/1/feedback", json={"rating": 9, "comment": "Too many stars"}
    )
    assert response.status == 400
    assert "rating" in response.json["error"]["fields"]


async def test_user_text_is_escaped_in_pages(client):
    await sign_in(client, VISITOR)
    payload = '<script>alert("xss")</script>'
    request, response = await client.post(
        "/api/sculptures/3/feedback", json={"rating": 2, "comment": payload}
    )
    assert response.status == 201
    request, response = await client.get("/sculptures/3")
    assert "<script>alert(" not in response.text
    assert "&lt;script&gt;" in response.text


# --- curator CRUD and roles ----------------------------------------------


async def test_curator_sculpture_and_stage_lifecycle(client):
    await sign_in(client, CURATOR)
    suffix = uuid.uuid4().hex[:6]
    stage_name = f"Harbour Wall {suffix}"
    title = f"Tide Gauge {suffix}"

    request, response = await client.post(
        "/api/stages",
        json={
            "name": stage_name,
            "sequence": 7,
            "description": "A short harbour-wall walk for the winter programme.",
            "accessibility_notes": "Level promenade with tactile paving and two benches.",
        },
    )
    assert response.status == 201, response.text
    stage_id = response.json["stage"]["id"]

    request, response = await client.post(
        "/api/sculptures",
        json={
            "title": title,
            "artist": "Ines Kowalski",
            "material": "Brass and oak",
            "description": "A brass tide gauge set into an oak frame against the harbour wall.",
            "lat": 53.3488,
            "lng": -1.8302,
            "stage_id": stage_id,
        },
    )
    assert response.status == 201, response.text
    sculpture_id = response.json["sculpture"]["id"]
    assert response.json["sculpture"]["stage"]["id"] == stage_id

    request, response = await client.patch(
        f"/api/sculptures/{sculpture_id}", json={"material": "Cast bronze"}
    )
    assert response.status == 200
    assert response.json["sculpture"]["material"] == "Cast bronze"

    request, response = await client.get(f"/api/sculptures/{sculpture_id}")
    assert response.json["sculpture"]["material"] == "Cast bronze"

    request, response = await client.get("/")
    assert title in response.text

    # A stage with sculptures assigned cannot be deleted.
    request, response = await client.delete(f"/api/stages/{stage_id}")
    assert response.status == 409
    assert "still has 1 sculpture" in response.json["error"]["message"]

    request, response = await client.delete(f"/api/sculptures/{sculpture_id}")
    assert response.status == 200
    request, response = await client.get(f"/api/sculptures/{sculpture_id}")
    assert response.status == 404

    request, response = await client.delete(f"/api/stages/{stage_id}")
    assert response.status == 200


async def test_curator_validation_rejects_bad_coordinates(client):
    await sign_in(client, CURATOR)
    request, response = await client.post(
        "/api/sculptures",
        json={
            "title": f"Off-grid {uuid.uuid4().hex[:6]}",
            "artist": "Nobody",
            "material": "Slate",
            "description": "A description that is definitely long enough to pass validation.",
            "lat": 999,
            "lng": -1.8,
            "stage_id": 1,
        },
    )
    assert response.status == 400
    assert "lat" in response.json["error"]["fields"]


async def test_visitor_cannot_write_trail_content(client):
    await sign_in(client, VISITOR)

    request, response = await client.post(
        "/api/sculptures",
        json={
            "title": "Visitor Piece",
            "artist": "Visitor",
            "material": "Chalk",
            "description": "A description that is definitely long enough to pass validation.",
            "lat": 53.34,
            "lng": -1.83,
            "stage_id": 1,
        },
    )
    assert response.status == 403

    request, response = await client.patch("/api/stages/1", json={"name": "Renamed by a visitor"})
    assert response.status == 403

    request, response = await client.delete("/api/sculptures/1")
    assert response.status == 403

    request, response = await client.get("/api/stages/1")
    assert response.json["stage"]["name"] == "Gatehouse Approach"

    request, response = await client.get("/curator")
    assert response.status == 403
    assert "limited to trail curators" in response.text


async def test_curator_page_and_studio_forms_render(client):
    await sign_in(client, CURATOR)
    request, response = await client.get("/curator")
    assert response.status == 200
    body = response.text
    assert "Add a sculpture" in body
    assert "Add a trail stage" in body
    assert "data-delete-sculpture" in body
    assert "Delete this record?" in body


async def test_form_login_and_logout_fallbacks(client):
    """The sign-in form also works as a plain form post (no JavaScript)."""
    request, response = await client.post(
        "/login",
        data={"email": "cenius@cenius.ai", "password": "cenius"},
        follow_redirects=False,
    )
    assert response.status == 302
    assert response.headers["location"] == "/"
    assert "trail_session" in client.cookies

    request, me = await client.get("/api/auth/me")
    assert me.status == 200
    assert me.json["user"]["is_curator"] is True

    request, response = await client.post("/logout", follow_redirects=False)
    assert response.status == 302
    assert response.headers["location"] == "/login"
    client.cookies.clear()
    request, me = await client.get("/api/auth/me")
    assert me.status == 401


async def test_form_login_error_keeps_email(client):
    request, response = await client.post(
        "/login",
        data={"email": "cenius@cenius.ai", "password": "wrong-password"},
        follow_redirects=False,
    )
    assert response.status == 401
    assert "do not match an account" in response.text
    assert 'value="cenius@cenius.ai"' in response.text


async def test_dashboard_page_shell_after_login(client):
    await sign_in(client, CURATOR)
    request, response = await client.get("/")
    assert response.status_code == 200
    body = response.text
    assert 'id="map"' in body
    assert 'data-map-pins' in body
    assert 'id="trail-data"' in body
    assert "Corten Arc" in body
    assert "Gatehouse Approach" in body
    assert 'id="stage-filter"' in body
    assert 'id="palette"' in body
    assert "Sign out" in body
    assert 'href="/curator"' in body
