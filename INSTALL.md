# Install guide — Sculpture Trail Visitor Map

This app is a single Python service. There is exactly one package manager for it: **pip**,
driven by `requirements.txt` at the project root. There is no Node, Ruby, or system package
step, and nothing is downloaded at runtime.

## 1. Prerequisites (install these yourself, once)

| Requirement | Why | Check |
| --- | --- | --- |
| Python 3.11+ | Runs Sanic and the standard-library `sqlite3` | `python3 --version` |
| pip | Installs the pinned dependencies | `python3 -m pip --version` |
| A POSIX shell | Runs `install.sh` and the server | `bash --version` |

No compiler, no database server, no `apt`/`brew` packages: SQLite is embedded in Python, and
every front-end asset (CSS, JS, the Lexend woff2, the favicon) ships in `web/static`.

## 2. Dependencies

```bash
pip install -r requirements.txt
```

Pinned versions: Sanic 24.6.0, aiosqlite 0.20.0, Jinja2 3.1.4, and — for the test suite —
pytest 8.3.3, pytest-asyncio 0.24.0, sanic-testing 24.6.0, httpx 0.28.1.

## 3. Configuration (optional)

The app boots with **no** configuration. To override defaults:

```bash
cp .env.example .env
```

| Variable | Default | Meaning |
| --- | --- | --- |
| `SESSION_SECRET` | in-code dev fallback | Keys the session token digest. `install.sh` generates a strong value into `.env`. |
| `SCULPTURE_DB_PATH` | `./trail.db` | SQLite file, relative to the project root. |
| `PORT` | `8000` | HTTP port. The server always binds `0.0.0.0`. |
| `SESSION_COOKIE_SECURE` | `false` | Set `true` only when serving over HTTPS. |

## 4. Create the database and seed demo data

```bash
python3 seed.py
```

This creates `schema.sql`'s tables (idempotent `CREATE ... IF NOT EXISTS`), enables WAL, and
inserts the demo users, three trail stages, eight sculptures and fourteen feedback entries if
they are missing. Re-running it is safe. **It exits without starting the server** — the server
is a separate command. The same seeding also runs automatically on the normal boot path, so
skipping this step still produces a populated app.

## 5. Run

```bash
python3 app.py
```

Expected first line: `Sculpture Trail Visitor Map listening on 0.0.0.0:8000`.
Open <http://localhost:8000> and sign in with `cenius@cenius.ai` / `cenius`.

## 6. Verify

```bash
python3 -m pytest        # 19 smoke tests, no network required
```

`bash install.sh` performs steps 2–4 in one go and then exits.
