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
