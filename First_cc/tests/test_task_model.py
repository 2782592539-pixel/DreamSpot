"""Tests for Task model."""
import json
from datetime import datetime
from backend.models.task import Task


def test_task_to_json_dict_excludes_mzc_fields():
    task = Task(
        id="t_1",
        name="test",
        prompt="do something",
        schedule="0 9 * * *",
        created_at=datetime(2026, 6, 19, 8, 0),
        created_by="H-yue",
        tags=["daily"],
    )
    d = task.to_json_dict()
    assert "created_by" not in d
    assert "tags" not in d
    assert d["name"] == "test"
    assert d["last_status"] == "never"


def test_task_parses_tags_from_json_string():
    task = Task(
        id="t_2",
        name="x",
        prompt="y",
        schedule="* * * * *",
        created_at=datetime.now(),
        tags='["a","b"]',
    )
    assert task.tags == ["a", "b"]


def test_task_default_status_is_never():
    task = Task(
        id="t_3",
        name="x",
        prompt="y",
        schedule="* * * * *",
        created_at=datetime.now(),
    )
    assert task.last_status == "never"
    assert task.enabled is True
    assert task.tags == []