"""Typed API errors with one consistent JSON envelope.

Every API failure answers with::

    {"error": {"code": "...", "message": "...", "fields": {...}}}

Client-facing messages are generic; full detail is logged server-side by the
app-level error handler.
"""

from __future__ import annotations

from typing import Any

from sanic.exceptions import SanicException


class ApiError(SanicException):
    """Raised by handlers to fail closed with a safe, structured response."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        fields: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message, status_code=status_code)
        self.code = code
        self.message = message
        self.fields: dict[str, str] = fields or {}

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.fields:
            body["fields"] = self.fields
        return {"error": body}


def unauthorized(message: str = "Please sign in to continue.") -> ApiError:
    return ApiError(401, "unauthorized", message)


def forbidden(message: str = "You do not have access to this action.") -> ApiError:
    return ApiError(403, "forbidden", message)


def not_found(message: str = "That record could not be found.") -> ApiError:
    return ApiError(404, "not_found", message)


def invalid(fields: dict[str, str], message: str = "Please check the highlighted fields.") -> ApiError:
    return ApiError(400, "invalid_input", message, fields)


def conflict(message: str) -> ApiError:
    return ApiError(409, "conflict", message)
