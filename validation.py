"""Boundary validation for request bodies.

Each helper records a field-level error and returns a safe empty value, so a
handler can collect every problem at once and then raise a single 400 with the
whole error map. Nothing off-spec ever reaches SQL or the response.
"""

from __future__ import annotations

import re
from typing import Any

from errors import ApiError, invalid

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")
USERNAME_RE = re.compile(r"[^a-z0-9_]+")


async def json_body(request) -> dict[str, Any]:
    """Parse a JSON object body, rejecting anything else with a 400."""
    try:
        payload = request.json
    except Exception as exc:  # malformed JSON from the client
        raise invalid({}, "Send a valid JSON object.") from exc
    if not isinstance(payload, dict):
        raise invalid({}, "Send a JSON object body.")
    return payload


class Form:
    """Collect field errors while reading a JSON body."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.errors: dict[str, str] = {}

    def text(
        self,
        name: str,
        label: str,
        *,
        min_len: int = 1,
        max_len: int = 200,
        required: bool = True,
    ) -> str:
        raw = self.data.get(name, "")
        if raw is None:
            raw = ""
        if not isinstance(raw, str):
            self.errors[name] = f"{label} must be text."
            return ""
        value = " ".join(raw.split()) if name != "comment" else raw.strip()
        if required and not value:
            self.errors[name] = f"Enter {label[0].lower()}{label[1:]}."
            return ""
        if value and len(value) < min_len:
            self.errors[name] = f"{label} needs at least {min_len} characters."
            return ""
        if len(value) > max_len:
            self.errors[name] = f"{label} must be {max_len} characters or fewer."
            return ""
        return value

    def email(self, name: str = "email", label: str = "Email") -> str:
        value = self.text(name, label, max_len=254)
        if not value:
            return ""
        if not EMAIL_RE.match(value):
            self.errors[name] = "Enter an email address like name@example.com."
            return ""
        return value.lower()

    def integer(
        self,
        name: str,
        label: str,
        *,
        minimum: int,
        maximum: int,
        required: bool = True,
    ) -> int:
        raw = self.data.get(name)
        if raw is None or raw == "":
            if required:
                self.errors[name] = f"Enter {label[0].lower()}{label[1:]}."
            return minimum
        try:
            value = int(str(raw).strip())
        except (TypeError, ValueError):
            self.errors[name] = f"{label} must be a whole number."
            return minimum
        if value < minimum or value > maximum:
            self.errors[name] = f"{label} must be between {minimum} and {maximum}."
            return minimum
        return value

    def number(
        self,
        name: str,
        label: str,
        *,
        minimum: float,
        maximum: float,
        required: bool = True,
    ) -> float:
        raw = self.data.get(name)
        if raw is None or raw == "":
            if required:
                self.errors[name] = f"Enter {label[0].lower()}{label[1:]}."
            return minimum
        try:
            value = float(str(raw).strip())
        except (TypeError, ValueError):
            self.errors[name] = f"{label} must be a number."
            return minimum
        if value < minimum or value > maximum:
            self.errors[name] = f"{label} must be between {minimum:g} and {maximum:g}."
            return minimum
        return value

    def raise_if_invalid(self, message: str = "Please check the highlighted fields.") -> None:
        if self.errors:
            raise invalid(self.errors, message)


def slug_username(email: str) -> str:
    """Derive a username from an email local part."""
    local = (email.split("@", 1)[0] or "").lower()
    slug = USERNAME_RE.sub("_", local).strip("_")[:20]
    return slug or "visitor"


def validate_password_matches(password: str, confirmation: str, form: Form) -> None:
    if not password:
        form.errors.setdefault("password", "Choose a password of at least 8 characters.")
    elif len(password) < 8:
        form.errors["password"] = "Use at least 8 characters for your password."
    if confirmation != password:
        form.errors["password_confirm"] = "The two passwords do not match."


def as_api_error(exc: ApiError) -> dict[str, Any]:
    return exc.to_dict()
