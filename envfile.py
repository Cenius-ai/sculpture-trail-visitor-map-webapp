"""Minimal .env loader (standard library only).

`install.sh` writes a generated session secret into `.env`; this loader makes
that file effective without pulling in a dotenv dependency. Real environment
variables always win, so operators can override anything. When `.env` is
absent (a fresh checkout) every setting falls back to its in-code dev default
and the app still boots.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def load_environment(path: str | Path | None = None) -> None:
    env_path = Path(path) if path else BASE_DIR / ".env"
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
