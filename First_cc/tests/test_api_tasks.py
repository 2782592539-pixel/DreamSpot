"""Tests for /api/tasks routes."""
import json
from backend.db.init_db import init_db


def test_list_tasks_empty(client):
    init_db()
    response = client.get("/api/tasks")
    assert response.status_code == 200
    assert response.json() == []


def test_list_tasks_returns_json_tasks(client, temp_data_dir):
    init_db()
    path = temp_data_dir / "fake_claude_home" / ".claude" / "scheduled_tasks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "version": 1,
        "tasks": [
            {
                "id": "t_1",
                "name": "Daily",
                "prompt": "x",
                "schedule": "0 9 * * *",
                "enabled": True,
                "created_at": "2026-06-19T08:00:00",
                "last_run": None,
                "last_status": "never",
            }
        ],
    }))

    response = client.get("/api/tasks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "t_1"
    assert data[0]["name"] == "Daily"


def test_run_task_creates_run_record(client, temp_data_dir):
    """POST /api/tasks/{id}/run should execute claude and record a run."""
    import json
    from backend.db.init_db import init_db
    from unittest.mock import patch

    init_db()
    path = temp_data_dir / "fake_claude_home" / ".claude" / "scheduled_tasks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "version": 1,
        "tasks": [
            {
                "id": "t_run",
                "name": "Test",
                "prompt": "echo hi",
                "schedule": "0 9 * * *",
                "enabled": True,
                "created_at": "2026-06-19T08:00:00",
                "last_run": None,
                "last_status": "never",
            }
        ],
    }))

    # First sync, then run
    with patch("backend.services.claude_runner.ClaudeRunner.run") as mock_run:
        from backend.services.claude_runner import ClaudeRunResult
        from datetime import datetime
        mock_run.return_value = ClaudeRunResult(
            exit_code=0, output="hi", error="",
            started_at=datetime.now(), finished_at=datetime.now(),
            duration_sec=1,
        )
        response = client.post("/api/tasks/t_run/run")
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "t_run"
    assert data["status"] == "success"
    assert data["trigger_source"] == "manual_web"
    assert data["id"] > 0


def test_run_unknown_task_returns_404(client):
    from backend.db.init_db import init_db
    init_db()
    response = client.post("/api/tasks/t_nope/run")
    assert response.status_code == 404


def test_run_task_timeout_records_timeout_status(client, temp_data_dir):
    """If ClaudeRunner.run() raises TimeoutError, record status='timeout'."""
    import json
    from backend.db.init_db import init_db
    from unittest.mock import patch

    init_db()
    path = temp_data_dir / "fake_claude_home" / ".claude" / "scheduled_tasks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "version": 1,
        "tasks": [
            {
                "id": "t_slow",
                "name": "Slow",
                "prompt": "x",
                "schedule": "0 9 * * *",
                "enabled": True,
                "created_at": "2026-06-19T08:00:00",
                "last_run": None,
                "last_status": "never",
            }
        ],
    }))

    with patch("backend.services.claude_runner.ClaudeRunner.run") as mock_run:
        mock_run.side_effect = TimeoutError("Claude run timed out after 1s")
        response = client.post("/api/tasks/t_slow/run")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "timeout"
    assert data["task_id"] == "t_slow"
