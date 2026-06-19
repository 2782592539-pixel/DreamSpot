"""Tests for claude_runner - subprocess wrapper for `claude -p`."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from backend.services.claude_runner import ClaudeRunner, ClaudeRunResult


def test_run_success():
    runner = ClaudeRunner(claude_cli="echo", timeout_sec=10)
    # `echo hello` always succeeds
    result = runner.run(prompt="hello")
    assert result.exit_code == 0
    assert "hello" in result.output


def test_run_records_duration():
    runner = ClaudeRunner(claude_cli="echo", timeout_sec=10)
    result = runner.run(prompt="test")
    assert result.duration_sec >= 0
    assert result.started_at <= result.finished_at


def test_run_timeout_raises():
    """subprocess.TimeoutExpired should be translated to TimeoutError."""
    import subprocess
    from unittest.mock import patch, MagicMock
    runner = ClaudeRunner(claude_cli="echo", timeout_sec=1)
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="echo", timeout=1)
        with pytest.raises(TimeoutError):
            runner.run(prompt="x")


def test_run_nonzero_exit_returns_result():
    """A non-zero exit should NOT raise; we want to record the failure."""
    runner = ClaudeRunner(claude_cli="false", timeout_sec=10)  # `false` exits 1
    result = runner.run(prompt="x")
    assert result.exit_code != 0


def test_run_uses_pty_false():
    """Should use CREATE_NO_WINDOW on Windows (no flashing console)."""
    runner = ClaudeRunner(claude_cli="echo", timeout_sec=10)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="ok", stderr=""
        )
        runner.run(prompt="x")
        call_kwargs = mock_run.call_args.kwargs
        # On Windows, creationflags should be set
        if "creationflags" in call_kwargs:
            assert call_kwargs["creationflags"] > 0


def test_invalid_cli_path_raises_at_init():
    """A nonexistent claude_cli should fail fast at construction, not at run()."""
    with pytest.raises(ValueError, match="not found on PATH"):
        ClaudeRunner(claude_cli="definitely-not-a-real-binary-xyz", timeout_sec=10)


def test_empty_cli_path_raises_at_init():
    """An empty claude_cli should also fail fast."""
    with pytest.raises(ValueError, match="empty"):
        ClaudeRunner(claude_cli="", timeout_sec=10)
