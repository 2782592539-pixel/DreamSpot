"""Pytest fixtures."""
import os
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _reset_settings_cache(monkeypatch):
    """Reset backend.config._settings between tests so monkeypatched env vars take effect."""
    import backend.config
    backend.config._settings = None
    yield
    backend.config._settings = None


@pytest.fixture
def temp_data_dir(monkeypatch, tmp_path):
    """Redirect DB and log paths to a temp dir for tests."""
    data_dir = tmp_path / "data"
    logs_dir = tmp_path / "logs"
    data_dir.mkdir()
    logs_dir.mkdir()
    monkeypatch.setenv("MZC_DB_PATH", str(data_dir / "test.db"))
    monkeypatch.setenv("MZC_LOG_PATH", str(logs_dir / "test.log"))
    monkeypatch.setenv("MZC_CLAUDE_HOME", str(tmp_path / "fake_claude_home"))
    (tmp_path / "fake_claude_home" / ".claude").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def client(temp_data_dir):
    """FastAPI test client with lifespan startup/shutdown."""
    from backend.main import create_app
    app = create_app()
    with TestClient(app) as c:
        yield c
