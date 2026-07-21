-- Master Plan v2, Section 9. Per Decision 10: nothing beyond these two
-- tables - rating is a live column on users, updated in place, never
-- archived; no games/rooms/rating_changes history tables.

CREATE TABLE IF NOT EXISTS users (
    user_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    password_salt   TEXT,
    rating          INTEGER NOT NULL DEFAULT 1200,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    token           TEXT PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(user_id),
    issued_at       TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
