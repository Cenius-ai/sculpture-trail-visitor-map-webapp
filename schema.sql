-- Sculpture Trail Visitor Map - SQLite schema.
-- Applied idempotently on every boot (CREATE ... IF NOT EXISTS), so a fresh
-- clone with no database file still boots into a working, seeded app.

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
    username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    display_name  TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    is_curator    INTEGER NOT NULL DEFAULT 0 CHECK (is_curator IN (0, 1)),
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trail_stages (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    name                 TEXT NOT NULL UNIQUE,
    sequence             INTEGER NOT NULL CHECK (sequence > 0),
    description          TEXT NOT NULL,
    accessibility_notes  TEXT NOT NULL,
    created_at           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sculptures (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL UNIQUE,
    artist      TEXT NOT NULL,
    material    TEXT NOT NULL,
    description TEXT NOT NULL,
    lat         REAL NOT NULL CHECK (lat BETWEEN -90 AND 90),
    lng         REAL NOT NULL CHECK (lng BETWEEN -180 AND 180),
    stage_id    INTEGER NOT NULL REFERENCES trail_stages(id) ON DELETE RESTRICT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    sculpture_id  INTEGER NOT NULL REFERENCES sculptures(id) ON DELETE CASCADE,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating        INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment       TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS ix_sculptures_stage ON sculptures(stage_id);
CREATE INDEX IF NOT EXISTS ix_feedback_sculpture ON feedback(sculpture_id);
CREATE INDEX IF NOT EXISTS ix_feedback_user ON feedback(user_id);
CREATE INDEX IF NOT EXISTS ix_stages_sequence ON trail_stages(sequence);
