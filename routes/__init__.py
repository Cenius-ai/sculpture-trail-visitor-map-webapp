"""Route registration for the Sculpture Trail Visitor Map."""

from __future__ import annotations

from sanic import Sanic

from routes import auth as auth_routes
from routes import content as content_routes
from routes import curator as curator_routes
from routes import feedback as feedback_routes
from routes import pages as page_routes


def register(app: Sanic) -> None:
    app.blueprint(auth_routes.bp)
    app.blueprint(content_routes.bp)
    app.blueprint(feedback_routes.bp)
    app.blueprint(curator_routes.bp)
    app.blueprint(page_routes.bp)
