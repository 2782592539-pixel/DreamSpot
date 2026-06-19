"""Tests for task executor (tick handler)."""
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from backend.db.init_db import init_db
from backend.services.executor import TaskExecutor
from backend.services.claude_runner import ClaudeRunResult


def _write_task_file(temp_data_dir, task_id, last_run_iso=None):
    path = temp_data_dir / "fake_claude_home" / ".claude" / "scheduled_tasks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "version": 1,
        "tasks": [
            {
                "id": task_id,
                "name": "x",
                "prompt": "do it",
                "schedule": "0 9 * * *",
                "enabled": True,
                "created_at": "2026-06-19T08:00:00",
                "last_run": last_run_iso,
                "last_status": "never",
            }
        ],
    }))


def test_executor_runs_task_and_records(temp_data_dir):
    init_db()
    _write_task_file(temp_data_dir, "t_e1")

    with patch("backend.services.executor.ClaudeRunner") as MockRunner:
        mock_instance = MagicMock()
        mock_instance.run.return_value = ClaudeRunResult(
            exit_code=0, output="done", error="",
            started_at=datetime.now(),
            finished_at=datetime.now(),
            duration_sec=2,
        )
        MockRunner.return_value = mock_instance

        executor = TaskExecutor()
        executor.tick("t_e1", "do it")

        mock_instance.run.assert_called_once()
        from backend.db.connection import get_connection
        with get_connection() as conn:
            runs = conn.execute("SELECT * FROM runs WHERE task_id = 't_e1'").fetchall()
        assert len(runs) == 1
        assert runs[0]["status"] == "success"


def test_executor_skips_recently_run_task_p1(temp_data_dir):
    """Strategy P1: skip if last_run was within the cron interval.

    Daily task (24h), last_run was 1h ago -> skip (Claude Code likely ran it).
    """
    init_db()
    recent = (datetime.now() - timedelta(hours=1)).isoformat()
    _write_task_file(temp_data_dir, "t_skip", last_run_iso=recent)

    with patch("backend.services.executor.ClaudeRunner") as MockRunner:
        mock_instance = MagicMock()
        MockRunner.return_value = mock_instance
        executor = TaskExecutor()
        executor.tick("t_skip", "do it")
        mock_instance.run.assert_not_called()


def test_executor_runs_task_with_old_last_run_p1(temp_data_dir):
    """Daily task, last_run was 25h ago -> run (longer than interval)."""
    init_db()
    old = (datetime.now() - timedelta(hours=25)).isoformat()
    _write_task_file(temp_data_dir, "t_old", last_run_iso=old)

    with patch("backend.services.executor.ClaudeRunner") as MockRunner:
        mock_instance = MagicMock()
        mock_instance.run.return_value = ClaudeRunResult(
            exit_code=0, output="ok", error="",
            started_at=datetime.now(), finished_at=datetime.now(),
            duration_sec=1,
        )
        MockRunner.return_value = mock_instance
        executor = TaskExecutor()
        executor.tick("t_old", "do it")
        mock_instance.run.assert_called_once()


def test_executor_handles_missing_task_gracefully(temp_data_dir):
    init_db()
    _write_task_file(temp_data_dir, "t_real")
    executor = TaskExecutor()
    executor.tick("t_does_not_exist", "x")  # no crash


def test_executor_handles_timeout(temp_data_dir):
    """TimeoutError from ClaudeRunner should be recorded as status='timeout'."""
    init_db()
    _write_task_file(temp_data_dir, "t_to")

    with patch("backend.services.executor.ClaudeRunner") as MockRunner:
        mock_instance = MagicMock()
        mock_instance.run.side_effect = TimeoutError("Claude run timed out after 1s")
        MockRunner.return_value = mock_instance

        executor = TaskExecutor()
        executor.tick("t_to", "do it")

        from backend.db.connection import get_connection
        with get_connection() as conn:
            runs = conn.execute("SELECT * FROM runs WHERE task_id = 't_to'").fetchall()
        assert len(runs) == 1
        assert runs[0]["status"] == "timeout"
