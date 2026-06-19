"""Tests for APScheduler service."""
import json
from backend.db.init_db import init_db
from backend.services.scheduler import MzcScheduler


def test_scheduler_starts_empty(temp_data_dir):
    init_db()
    sched = MzcScheduler()
    sched.start()
    try:
        assert sched.get_jobs() == []
    finally:
        sched.shutdown()


def test_scheduler_loads_tasks_from_json(temp_data_dir):
    init_db()
    path = temp_data_dir / "fake_claude_home" / ".claude" / "scheduled_tasks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "version": 1,
        "tasks": [
            {
                "id": "t_1",
                "name": "test",
                "prompt": "x",
                "schedule": "0 9 * * *",
                "enabled": True,
                "created_at": "2026-06-19T08:00:00",
                "last_run": None,
                "last_status": "never",
            }
        ],
    }))

    sched = MzcScheduler()
    sched.start()
    try:
        sched.reload_tasks()
        jobs = sched.get_jobs()
        assert len(jobs) == 1
        assert jobs[0]["id"] == "t_1"
        assert jobs[0]["next_run"] is not None
    finally:
        sched.shutdown()


def test_scheduler_skips_disabled_tasks(temp_data_dir):
    init_db()
    path = temp_data_dir / "fake_claude_home" / ".claude" / "scheduled_tasks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "version": 1,
        "tasks": [
            {
                "id": "t_off",
                "name": "off",
                "prompt": "x",
                "schedule": "0 9 * * *",
                "enabled": False,
                "created_at": "2026-06-19T08:00:00",
                "last_run": None,
                "last_status": "never",
            }
        ],
    }))

    sched = MzcScheduler()
    sched.start()
    try:
        sched.reload_tasks()
        assert sched.get_jobs() == []
    finally:
        sched.shutdown()