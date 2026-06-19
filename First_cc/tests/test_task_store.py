"""Tests for task_store service - reads/writes scheduled_tasks.json."""
import json
import pytest
from datetime import datetime
from backend.services.task_store import TaskStore, TaskStoreError
from backend.models.task import Task


@pytest.fixture
def sample_json(temp_data_dir):
    """Write a sample scheduled_tasks.json."""
    claude_home = temp_data_dir / "fake_claude_home"
    cc_dir = claude_home / ".claude"
    cc_dir.mkdir(parents=True, exist_ok=True)
    path = cc_dir / "scheduled_tasks.json"
    data = {
        "version": 1,
        "tasks": [
            {
                "id": "t_abc",
                "name": "Daily report",
                "prompt": "Generate today's report",
                "schedule": "0 9 * * *",
                "enabled": True,
                "created_at": "2026-06-19T08:00:00Z",
                "last_run": None,
                "last_status": "never",
            }
        ],
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_load_returns_list_of_tasks(sample_json):
    store = TaskStore()
    tasks = store.load_all()
    assert len(tasks) == 1
    assert tasks[0].id == "t_abc"
    assert tasks[0].name == "Daily report"
    assert tasks[0].enabled is True


def test_load_handles_missing_file(temp_data_dir):
    store = TaskStore()
    tasks = store.load_all()
    assert tasks == []


def test_load_handles_corrupt_file_raises(temp_data_dir):
    claude_home = temp_data_dir / "fake_claude_home"
    cc_dir = claude_home / ".claude"
    cc_dir.mkdir(parents=True, exist_ok=True)
    path = cc_dir / "scheduled_tasks.json"
    path.write_text("not valid json{{{", encoding="utf-8")

    store = TaskStore()
    with pytest.raises(TaskStoreError):
        store.load_all()


def test_add_task_writes_to_file(sample_json):
    store = TaskStore()
    new_task = Task(
        id="t_new",
        name="New task",
        prompt="do x",
        schedule="*/5 * * * *",
        created_at=datetime(2026, 6, 19, 10, 0),
    )
    store.add(new_task)

    data = json.loads(sample_json.read_text(encoding="utf-8"))
    ids = {t["id"] for t in data["tasks"]}
    assert "t_new" in ids
    assert "t_abc" in ids


def test_update_last_run(sample_json):
    store = TaskStore()
    store.update_last_run("t_abc", datetime(2026, 6, 19, 9, 0), "success")

    data = json.loads(sample_json.read_text(encoding="utf-8"))
    task = next(t for t in data["tasks"] if t["id"] == "t_abc")
    assert task["last_run"] is not None
    assert task["last_status"] == "success"


def test_update_last_run_missing_task_no_error(sample_json):
    store = TaskStore()
    store.update_last_run("t_nonexistent", datetime.now(), "success")
