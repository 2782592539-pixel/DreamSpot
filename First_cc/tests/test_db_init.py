"""Tests for DB initialization."""
from backend.db.connection import get_connection
from backend.db.init_db import init_db


def test_init_db_creates_all_tables(temp_data_dir):
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    names = {r["name"] for r in rows}
    expected = {"tasks", "runs", "sessions", "users", "audit_log", "outbox"}
    assert expected.issubset(names), f"Missing tables: {expected - names}"


def test_init_db_is_idempotent(temp_data_dir):
    init_db()
    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT COUNT(*) AS c FROM tasks").fetchone()
    assert rows["c"] == 0
