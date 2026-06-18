"""Initialize SQLite database schema. Idempotent."""
import logging
from backend.db.connection import get_connection

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    prompt          TEXT NOT NULL,
    schedule        TEXT NOT NULL,
    enabled         INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL,
    created_by      TEXT,
    tags            TEXT,
    next_run_at     TEXT,
    synced_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id         TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    status          TEXT NOT NULL,
    exit_code       INTEGER,
    output          TEXT,
    output_summary  TEXT,
    duration_sec    INTEGER,
    trigger_source  TEXT NOT NULL,
    feishu_msg_id   TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_runs_task_id ON runs(task_id);
CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at);

CREATE TABLE IF NOT EXISTS sessions (
    id              TEXT PRIMARY KEY,
    project_path    TEXT NOT NULL,
    title           TEXT,
    first_message   TEXT,
    message_count   INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL,
    last_active_at  TEXT NOT NULL,
    is_pinned       INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS users (
    id              TEXT PRIMARY KEY,
    name            TEXT,
    feishu_token    TEXT,
    created_at      TEXT NOT NULL,
    last_seen_at    TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    user_id         TEXT,
    action          TEXT NOT NULL,
    target          TEXT,
    details         TEXT,
    ip              TEXT
);

CREATE TABLE IF NOT EXISTS outbox (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    payload         TEXT NOT NULL,
    target_url      TEXT NOT NULL,
    attempts        INTEGER NOT NULL DEFAULT 0,
    last_error      TEXT,
    next_retry_at   TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    sent_at         TEXT
);
CREATE INDEX IF NOT EXISTS idx_outbox_next_retry ON outbox(next_retry_at);
"""


def init_db() -> None:
    """Create all tables if they don't exist."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)
    logger.info("Database schema initialized")


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    init_db()
    print(f"DB initialized at {get_connection.__module__}")
