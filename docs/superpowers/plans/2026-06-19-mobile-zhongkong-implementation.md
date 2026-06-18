# Mobile Zhongkong (MZC) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a mobile control plane for Claude Code on a home Windows laptop, accessible from phone (web + Feishu) over the public internet via Cloudflare Tunnel + Access, with Feishu push notifications for scheduled task runs.

**Architecture:** Python FastAPI service on `127.0.0.1:8765` reads Claude Code's `scheduled_tasks.json` and re-schedules via APScheduler. Triggers `claude -p` for each task, captures output, persists to SQLite, pushes Feishu card. Exposed to internet via `cloudflared` tunnel protected by Cloudflare Access. Runs as Windows service via NSSM.

**Tech Stack:** Python 3.11+ · FastAPI · APScheduler · SQLite · httpx · python-dotenv · pytest · NSSM (Windows) · cloudflared · Cloudflare Tunnel + Access (free tier) · Feishu open platform (self-built app)

**Spec:** `docs/superpowers/specs/2026-06-19-mobile-zhongkong-design.md`

---

## Phasing Overview

This plan is split into **9 phases**. Each phase ends with a working, testable system increment.

| Phase | Name | What works after |
|-------|------|------------------|
| 0 | Bootstrap & Skeleton | FastAPI hello-world on `127.0.0.1:8765`, tests passing |
| 1 | Local Task Store & API | `GET /api/tasks` returns tasks from `scheduled_tasks.json` |
| 2 | Claude Code Runner | `POST /api/tasks/{id}/run` triggers `claude -p`, records to SQLite |
| 3 | APScheduler Auto-Trigger | Cron triggers fire automatically, no double-fire |
| 4 | Feishu Integration | Card pushed on task success/failure; webhook signature verified |
| 5 | Cloudflare Tunnel + Access | Service reachable from phone at public URL, login required |
| 6 | Windows Service (NSSM) | Service auto-starts on boot, auto-restarts on crash |
| 7 | Backup & Session History | DB backed up nightly; sessions readable via API |
| 8 | Web Frontend & Feishu Card | Mobile-friendly UI, Feishu card with buttons |
| 9 | Smoke Test & Docs | End-to-end verified, README complete |

**Per-phase time estimate:** 1-4 hours each. Total: ~2-3 weeks at 1-2 hours/day.

---

## File Structure

```
C:\Users\27825\Desktop\First_cc\
├─ backend/
│   ├─ __init__.py
│   ├─ main.py                      # FastAPI app factory + lifespan
│   ├─ config.py                    # Pydantic Settings (.env loader)
│   ├─ db/
│   │   ├─ __init__.py
│   │   ├─ connection.py            # SQLite connection + session
│   │   └─ init_db.py               # CREATE TABLE statements
│   ├─ models/
│   │   ├─ __init__.py
│   │   ├─ task.py                  # Task Pydantic model
│   │   └─ run.py                   # RunRecord Pydantic model
│   ├─ services/
│   │   ├─ __init__.py
│   │   ├─ task_store.py            # read/write scheduled_tasks.json
│   │   ├─ history_store.py         # SQLite runs CRUD
│   │   ├─ claude_runner.py         # subprocess `claude -p` wrapper
│   │   ├─ scheduler.py             # APScheduler setup + tick handler
│   │   ├─ feishu_client.py         # send card to Feishu webhook
│   │   └─ outbox.py                # retry queue for failed Feishu sends
│   ├─ auth/
│   │   ├─ __init__.py
│   │   ├─ cloudflare_access.py     # verify CF Access JWT
│   │   └─ feishu_signature.py      # verify X-Lark-Signature
│   └─ api/
│       ├─ __init__.py
│       ├─ tasks.py                 # /api/tasks routes
│       ├─ runs.py                  # /api/runs routes
│       ├─ sessions.py              # /api/sessions routes
│       ├─ chat.py                  # /api/chat routes
│       ├─ system.py                # /api/system routes
│       └─ feishu_webhook.py        # POST /feishu/webhook
├─ web/
│   └─ index.html                   # single-page mobile UI
├─ scripts/
│   ├─ install_services.bat         # NSSM registration
│   ├─ uninstall_services.bat
│   ├─ backup_db.ps1
│   ├─ disable_sleep.ps1
│   └─ cloudflared_setup.ps1
├─ tests/
│   ├─ conftest.py
│   ├─ test_task_store.py
│   ├─ test_history_store.py
│   ├─ test_claude_runner.py
│   ├─ test_feishu_client.py
│   ├─ test_feishu_signature.py
│   ├─ test_scheduler.py
│   ├─ test_api_tasks.py
│   └─ test_api_system.py
├─ data/                            # gitignored
│   └─ mzc.db
├─ logs/                            # gitignored
│   └─ mzc.log
├─ .env.example
├─ .gitignore
├─ requirements.txt
├─ pyproject.toml                   # pytest config
└─ README.md
```

---

# Phase 0: Bootstrap & Skeleton

**Outcome:** A FastAPI service runs on `127.0.0.1:8765`, returns `{"status": "ok"}` at `/api/system/status`, with a passing test suite. Project structure and dependency management in place.

---

## Task 0.1: Initialize project & git

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\.gitignore`
- Create: `C:\Users\27825\Desktop\First_cc\requirements.txt`
- Create: `C:\Users\27825\Desktop\First_cc\pyproject.toml`
- Create: `C:\Users\27825\Desktop\First_cc\.env.example`

- [ ] **Step 1: Create project directory and enter it**

```bash
cd /c/Users/27825/Desktop
mkdir -p First_cc
cd First_cc
```

- [ ] **Step 2: Initialize git (if not already)**

```bash
git init
git config user.email "H-yue@local"
git config user.name "H-yue"
```

Expected: "Initialized empty Git repository" or already-initialized message.

- [ ] **Step 3: Write `.gitignore`**

Write to `C:\Users\27825\Desktop\First_cc\.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
.pytest_cache/
.mypy_cache/

# Project
data/
logs/
*.db
*.db-journal
*.log

# Secrets
.env
.env.local
*.pem
*.key

# IDE
.vscode/
.idea/
*.swp
```

- [ ] **Step 4: Write `requirements.txt`**

Write to `C:\Users\27825\Desktop\First_cc\requirements.txt`:

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
pydantic==2.9.2
pydantic-settings==2.5.2
python-dotenv==1.0.1
apscheduler==3.10.4
httpx==0.27.2
python-jose[cryptography]==3.3.0
pytest==8.3.3
pytest-asyncio==0.24.0
```

- [ ] **Step 5: Write `pyproject.toml` (pytest config only)**

Write to `C:\Users\27825\Desktop\First_cc\pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"
pythonpath = ["."]
```

- [ ] **Step 6: Write `.env.example`**

Write to `C:\Users\27825\Desktop\First_cc\.env.example`:

```bash
# MZC Service
MZC_HOST=127.0.0.1
MZC_PORT=8765
MZC_LOG_LEVEL=INFO

# Paths
MZC_CLAUDE_HOME=C:\Users\27825
MZC_DB_PATH=C:\Users\27825\Desktop\First_cc\data\mzc.db
MZC_LOG_PATH=C:\Users\27825\Desktop\First_cc\logs\mzc.log

# Claude Code CLI
MZC_CLAUDE_CLI=claude

# Feishu (fill in after creating self-built app)
MZC_FEISHU_APP_ID=
MZC_FEISHU_APP_SECRET=
MZC_FEISHU_WEBHOOK_VERIFY_TOKEN=
MZC_FEISHU_WEBHOOK_ENCRYPT_KEY=

# Cloudflare Access (filled in Phase 5)
MZC_CF_ACCESS_AUD=
MZC_CF_ACCESS_TEAM_DOMAIN=
```

- [ ] **Step 7: Commit**

```bash
cd /c/Users/27825/Desktop/First_cc
git add .gitignore requirements.txt pyproject.toml .env.example
git commit -m "chore: bootstrap project (gitignore, deps, config templates)"
```

---

## Task 0.2: Set up Python venv & install deps

**Files:**
- Modify: `C:\Users\27825\Desktop\First_cc\` (creates `.venv/`)

- [ ] **Step 1: Create venv**

```bash
cd /c/Users/27825/Desktop/First_cc
python -m venv .venv
```

Expected: `.venv/` directory created, no errors.

- [ ] **Step 2: Activate and upgrade pip**

```bash
.venv/Scripts/python.exe -m pip install --upgrade pip
```

Expected: "Successfully installed pip-X.Y.Z".

- [ ] **Step 3: Install requirements**

```bash
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

Expected: All packages install successfully, ending with a summary line.

- [ ] **Step 4: Verify FastAPI imports**

```bash
.venv/Scripts/python.exe -c "import fastapi, uvicorn, apscheduler, httpx; print('ok')"
```

Expected: `ok`

---

## Task 0.3: Create FastAPI app factory with /api/system/status

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\backend\__init__.py`
- Create: `C:\Users\27825\Desktop\First_cc\backend\config.py`
- Create: `C:\Users\27825\Desktop\First_cc\backend\main.py`
- Create: `C:\Users\27825\Desktop\First_cc\backend\api\__init__.py`
- Create: `C:\Users\27825\Desktop\First_cc\backend\api\system.py`

- [ ] **Step 1: Create empty `__init__.py` files**

Write to each:
- `C:\Users\27825\Desktop\First_cc\backend\__init__.py` (empty)
- `C:\Users\27825\Desktop\First_cc\backend\api\__init__.py` (empty)

Content (both files):
```python

```

- [ ] **Step 2: Write `backend/config.py`**

Write to `C:\Users\27825\Desktop\First_cc\backend\config.py`:

```python
"""Configuration loaded from .env file."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MZC_",
        case_sensitive=False,
        extra="ignore",
    )

    # Service
    host: str = "127.0.0.1"
    port: int = 8765
    log_level: str = "INFO"

    # Paths
    claude_home: str = r"C:\Users\27825"
    db_path: str = r"C:\Users\27825\Desktop\First_cc\data\mzc.db"
    log_path: str = r"C:\Users\27825\Desktop\First_cc\logs\mzc.log"

    # Claude Code
    claude_cli: str = "claude"

    # Feishu
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_webhook_verify_token: str = ""
    feishu_webhook_encrypt_key: str = ""

    # Cloudflare Access
    cf_access_aud: str = ""
    cf_access_team_domain: str = ""

    @property
    def scheduled_tasks_path(self) -> Path:
        return Path(self.claude_home) / ".claude" / "scheduled_tasks.json"

    @property
    def projects_dir(self) -> Path:
        return Path(self.claude_home) / ".claude" / "projects"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
```

- [ ] **Step 3: Write `backend/api/system.py`**

Write to `C:\Users\27825\Desktop\First_cc\backend\api\system.py`:

```python
"""System status endpoint - health check."""
from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status")
def get_status() -> dict:
    """Return service health status."""
    return {
        "status": "ok",
        "service": "mzc",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
```

- [ ] **Step 4: Write `backend/main.py`**

Write to `C:\Users\27825\Desktop\First_cc\backend\main.py`:

```python
"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from backend.api import system
from backend.config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("MZC service starting (version=0.1.0)")
    yield
    logger.info("MZC service stopping")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Mobile Zhongkong",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(system.router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
```

- [ ] **Step 5: Copy `.env.example` to `.env`**

```bash
cd /c/Users/27825/Desktop/First_cc
cp .env.example .env
```

- [ ] **Step 6: Run the service in background and verify**

```bash
cd /c/Users/27825/Desktop/First_cc
.venv/Scripts/python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8765 &
sleep 3
curl http://127.0.0.1:8765/api/system/status
```

Expected output:
```json
{"status":"ok","service":"mzc","version":"0.1.0","timestamp":"2026-..."}
```

- [ ] **Step 7: Stop the service**

```bash
# Find and kill the uvicorn process
.venv/Scripts/python.exe -c "import psutil" 2>/dev/null || .venv/Scripts/python.exe -m pip install psutil
.venv/Scripts/python.exe -c "
import psutil, os, signal
for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    if 'uvicorn' in ' '.join(p.info.get('cmdline') or []):
        os.kill(p.info['pid'], signal.SIGTERM)
        print(f'killed {p.info[\"pid\"]}')
"
```

---

## Task 0.4: Write first failing test for /api/system/status

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\tests\__init__.py`
- Create: `C:\Users\27825\Desktop\First_cc\tests\conftest.py`
- Create: `C:\Users\27825\Desktop\First_cc\tests\test_api_system.py`

- [ ] **Step 1: Create empty `tests/__init__.py`**

Write to `C:\Users\27825\Desktop\First_cc\tests\__init__.py`:
```python

```

- [ ] **Step 2: Write `tests/conftest.py`**

Write to `C:\Users\27825\Desktop\First_cc\tests\conftest.py`:

```python
"""Pytest fixtures."""
import os
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient


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
    """FastAPI test client."""
    from backend.main import create_app
    app = create_app()
    return TestClient(app)
```

- [ ] **Step 3: Write `tests/test_api_system.py`**

Write to `C:\Users\27825\Desktop\First_cc\tests\test_api_system.py`:

```python
"""Tests for /api/system routes."""
def test_status_returns_ok(client):
    response = client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "mzc"
    assert "timestamp" in data


def test_status_includes_version(client):
    response = client.get("/api/system/status")
    assert response.json()["version"] == "0.1.0"
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
cd /c/Users/27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_api_system.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
cd /c/Users/27825/Desktop/First_cc
git add backend/ tests/
git commit -m "feat(phase-0): FastAPI skeleton with /api/system/status and tests"
```

---

# Phase 1: Local Task Store & API

**Outcome:** `GET /api/tasks` returns parsed tasks from `scheduled_tasks.json`. SQLite stores task metadata. `POST /api/tasks` creates new tasks via Claude Code CLI.

---

## Task 1.1: Create SQLite schema and init script

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\backend\db\__init__.py`
- Create: `C:\Users\27825\Desktop\First_cc\backend\db\connection.py`
- Create: `C:\Users\27825\Desktop\First_cc\backend\db\init_db.py`
- Create: `C:\Users\27825\Desktop\First_cc\tests\test_db_init.py`

- [ ] **Step 1: Create `backend/db/__init__.py`**

Write to `C:\Users\27825\Desktop\First_cc\backend\db\__init__.py`:
```python

```

- [ ] **Step 2: Write `backend/db/connection.py`**

Write to `C:\Users\27825\Desktop\First_cc\backend\db\connection.py`:

```python
"""SQLite connection management."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from backend.config import get_settings


def get_db_path() -> Path:
    return Path(get_settings().db_path)


@contextmanager
def get_connection():
    """Yield a SQLite connection with row factory and WAL mode."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(db_path),
        detect_types=sqlite3.PARSE_DECLTYPES,
        isolation_level=None,  # autocommit; we use explicit BEGIN
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()
```

- [ ] **Step 3: Write `backend/db/init_db.py`**

Write to `C:\Users\27825\Desktop\First_cc\backend\db\init_db.py`:

```python
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
```

- [ ] **Step 4: Write `tests/test_db_init.py`**

Write to `C:\Users\27825\Desktop\First_cc\tests\test_db_init.py`:

```python
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
    init_db()  # should not raise
    with get_connection() as conn:
        rows = conn.execute("SELECT COUNT(*) AS c FROM tasks").fetchone()
    assert rows["c"] == 0
```

- [ ] **Step 5: Run tests**

```bash
cd /c/Users/27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_db_init.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Run init_db to create actual local DB**

```bash
cd /c/Users\27825/Desktop/First_cc
mkdir -p data logs
.venv/Scripts/python.exe -m backend.db.init_db
```

Expected: "Database schema initialized" and `data/mzc.db` created.

- [ ] **Step 7: Commit**

```bash
cd /c/Users/27825/Desktop/First_cc
git add backend/db/ tests/test_db_init.py
git commit -m "feat(phase-1): SQLite schema with 6 tables (tasks, runs, sessions, users, audit_log, outbox)"
```

---

## Task 1.2: Task Pydantic model

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\backend\models\__init__.py`
- Create: `C:\Users\27825\Desktop\First_cc\backend\models\task.py`
- Create: `C:\Users\27825\Desktop\First_cc\tests\test_task_model.py`

- [ ] **Step 1: Create `backend/models/__init__.py`**

Write to `C:\Users\27825\Desktop\First_cc\backend\models\__init__.py`:
```python

```

- [ ] **Step 2: Write `backend/models/task.py`**

Write to `C:\Users\27825\Desktop\First_cc\backend\models\task.py`:

```python
"""Task Pydantic model - mirrors Claude Code's scheduled_tasks.json format."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class Task(BaseModel):
    """A scheduled task. Matches Claude Code's JSON schema."""
    id: str
    name: str
    prompt: str
    schedule: str  # cron expression
    enabled: bool = True
    created_at: datetime
    last_run: datetime | None = None
    last_status: Literal["success", "failed", "timeout", "running", "never"] = "never"

    # MZC extensions (not in Claude Code's JSON, but in our SQLite mirror)
    created_by: str | None = None
    tags: list[str] = Field(default_factory=list)
    next_run_at: datetime | None = None
    synced_at: datetime | None = None

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v) if v else []
        return v

    def to_json_dict(self) -> dict:
        """Serialize for scheduled_tasks.json (only CC fields)."""
        return {
            "id": self.id,
            "name": self.name,
            "prompt": self.prompt,
            "schedule": self.schedule,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_status": self.last_status,
        }
```

- [ ] **Step 3: Write `tests/test_task_model.py`**

Write to `C:\Users\27825\Desktop\First_cc\tests\test_task_model.py`:

```python
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
        tags='["a","b"]',  # JSON string
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
```

- [ ] **Step 4: Run tests**

```bash
cd /c/Users/27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_task_model.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git add backend/models/ tests/test_task_model.py
git commit -m "feat(phase-1): Task Pydantic model with MZC extension fields"
```

---

## Task 1.3: task_store service - read & write scheduled_tasks.json

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\backend\services\__init__.py`
- Create: `C:\Users\27825\Desktop\First_cc\backend\services\task_store.py`
- Create: `C:\Users\27825\Desktop\First_cc\tests\test_task_store.py`

- [ ] **Step 1: Create `backend/services/__init__.py`**

Write to `C:\Users\27825\Desktop\First_cc\backend\services\__init__.py`:
```python

```

- [ ] **Step 2: Write `tests/test_task_store.py` first (TDD)**

Write to `C:\Users\27825\Desktop\First_cc\tests\test_task_store.py`:

```python
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

    # Re-read file
    data = json.loads(sample_json.read_text(encoding="utf-8"))
    ids = {t["id"] for t in data["tasks"]}
    assert "t_new" in ids
    assert "t_abc" in ids  # original preserved


def test_update_last_run(sample_json):
    store = TaskStore()
    store.update_last_run("t_abc", datetime(2026, 6, 19, 9, 0), "success")

    data = json.loads(sample_json.read_text(encoding="utf-8"))
    task = next(t for t in data["tasks"] if t["id"] == "t_abc")
    assert task["last_run"] is not None
    assert task["last_status"] == "success"


def test_update_last_run_missing_task_no_error(sample_json):
    store = TaskStore()
    # Should not raise
    store.update_last_run("t_nonexistent", datetime.now(), "success")
```

- [ ] **Step 3: Run tests, verify they fail**

```bash
cd /c/Users/27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_task_store.py -v
```

Expected: All 6 tests FAIL with "ModuleNotFoundError: backend.services.task_store".

- [ ] **Step 4: Write `backend/services/task_store.py`**

Write to `C:\Users\27825\Desktop\First_cc\backend\services\task_store.py`:

```python
"""Read/write Claude Code's scheduled_tasks.json file."""
import json
import logging
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from backend.config import get_settings
from backend.models.task import Task

logger = logging.getLogger(__name__)


class TaskStoreError(Exception):
    pass


class TaskStore:
    """Manages the on-disk JSON file used by Claude Code's CronCreate."""

    def __init__(self, path: Path | None = None):
        self.path = path or get_settings().scheduled_tasks_path

    def _read_raw(self) -> dict:
        if not self.path.exists():
            return {"version": 1, "tasks": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise TaskStoreError(f"Corrupt JSON at {self.path}: {e}") from e

    def _write_raw_atomic(self, data: dict) -> None:
        """Write atomically: temp file + replace, to avoid corruption on crash."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Write to temp file in same dir (for atomic os.replace)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.path.parent,
            delete=False,
            suffix=".tmp",
        ) as tmp:
            json.dump(data, tmp, indent=2, ensure_ascii=False)
            tmp_path = Path(tmp.name)
        shutil.move(str(tmp_path), str(self.path))

    def load_all(self) -> list[Task]:
        """Load all tasks from the JSON file."""
        data = self._read_raw()
        tasks = []
        for raw in data.get("tasks", []):
            # Parse ISO datetime strings
            created = raw.get("created_at")
            if isinstance(created, str):
                raw["created_at"] = datetime.fromisoformat(created.replace("Z", "+00:00"))
            last_run = raw.get("last_run")
            if isinstance(last_run, str):
                raw["last_run"] = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
            tasks.append(Task(**raw))
        return tasks

    def add(self, task: Task) -> None:
        """Append a new task to the JSON file."""
        data = self._read_raw()
        data["tasks"].append(task.to_json_dict())
        self._write_raw_atomic(data)
        logger.info(f"Added task {task.id} to {self.path}")

    def update_last_run(
        self, task_id: str, last_run: datetime, status: str
    ) -> None:
        """Update last_run and last_status for a task. No-op if task missing."""
        data = self._read_raw()
        for t in data["tasks"]:
            if t["id"] == task_id:
                t["last_run"] = last_run.isoformat()
                t["last_status"] = status
                self._write_raw_atomic(data)
                logger.debug(f"Updated last_run for {task_id}: {status}")
                return
        logger.warning(f"Task {task_id} not found in JSON; cannot update last_run")
```

- [ ] **Step 5: Run tests, verify they pass**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_task_store.py -v
```

Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git add backend/services/task_store.py tests/test_task_store.py
git commit -m "feat(phase-1): task_store service (read/write scheduled_tasks.json atomically)"
```

---

## Task 1.4: history_store service - SQLite runs CRUD

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\backend\services\history_store.py`
- Create: `C:\Users\27825\Desktop\First_cc\tests\test_history_store.py`

- [ ] **Step 1: Write `tests/test_history_store.py` first**

Write to `C:\Users\27825\Desktop\First_cc\tests\test_history_store.py`:

```python
"""Tests for history_store - SQLite runs CRUD."""
import pytest
from datetime import datetime
from backend.db.init_db import init_db
from backend.services.history_store import HistoryStore, RunRecord


@pytest.fixture
def store(temp_data_dir):
    init_db()
    return HistoryStore()


def test_insert_and_get_run(store):
    record = RunRecord(
        task_id="t_1",
        started_at=datetime(2026, 6, 19, 9, 0),
        finished_at=datetime(2026, 6, 19, 9, 5),
        status="success",
        exit_code=0,
        output="all good",
        output_summary="all good",
        duration_sec=300,
        trigger_source="cron",
    )
    run_id = store.insert(record)
    assert run_id > 0

    fetched = store.get(run_id)
    assert fetched is not None
    assert fetched.task_id == "t_1"
    assert fetched.status == "success"
    assert fetched.duration_sec == 300


def test_list_runs_by_task(store):
    for i in range(3):
        store.insert(RunRecord(
            task_id="t_a",
            started_at=datetime(2026, 6, 19, 9, i),
            status="success",
            trigger_source="cron",
        ))
    store.insert(RunRecord(
        task_id="t_b",
        started_at=datetime(2026, 6, 19, 10, 0),
        status="failed",
        trigger_source="manual_web",
    ))

    runs_a = store.list_by_task("t_a")
    assert len(runs_a) == 3

    runs_b = store.list_by_task("t_b")
    assert len(runs_b) == 1
    assert runs_b[0].status == "failed"


def test_set_feishu_msg_id(store):
    rec = RunRecord(
        task_id="t_1",
        started_at=datetime.now(),
        status="success",
        trigger_source="cron",
    )
    run_id = store.insert(rec)
    store.set_feishu_msg_id(run_id, "om_xyz123")

    fetched = store.get(run_id)
    assert fetched.feishu_msg_id == "om_xyz123"
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
cd /c/Users/27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_history_store.py -v
```

Expected: FAIL with "ModuleNotFoundError: backend.services.history_store".

- [ ] **Step 3: Write `backend/services/history_store.py`**

Write to `C:\Users\27825\Desktop\First_cc\backend\services\history_store.py`:

```python
"""SQLite-backed run history."""
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Literal

from backend.db.connection import get_connection

logger = logging.getLogger(__name__)

RunStatus = Literal["running", "success", "failed", "timeout"]
TriggerSource = Literal["cron", "manual_web", "manual_feishu"]


@dataclass
class RunRecord:
    task_id: str
    started_at: datetime
    finished_at: datetime | None = None
    status: RunStatus = "running"
    exit_code: int | None = None
    output: str | None = None
    output_summary: str | None = None
    duration_sec: int | None = None
    trigger_source: TriggerSource = "cron"
    feishu_msg_id: str | None = None
    id: int | None = None

    def to_row(self) -> dict:
        d = asdict(self)
        d.pop("id", None)
        return d


class HistoryStore:
    def insert(self, record: RunRecord) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                """INSERT INTO runs
                   (task_id, started_at, finished_at, status, exit_code,
                    output, output_summary, duration_sec, trigger_source,
                    feishu_msg_id)
                   VALUES (:task_id, :started_at, :finished_at, :status,
                           :exit_code, :output, :output_summary,
                           :duration_sec, :trigger_source, :feishu_msg_id)""",
                record.to_row(),
            )
            return cur.lastrowid

    def get(self, run_id: int) -> RunRecord | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM runs WHERE id = ?", (run_id,)
            ).fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def list_by_task(self, task_id: str, limit: int = 50) -> list[RunRecord]:
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM runs WHERE task_id = ?
                   ORDER BY started_at DESC LIMIT ?""",
                (task_id, limit),
            ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def set_feishu_msg_id(self, run_id: int, msg_id: str) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE runs SET feishu_msg_id = ? WHERE id = ?",
                (msg_id, run_id),
            )

    def _row_to_record(self, row) -> RunRecord:
        return RunRecord(
            id=row["id"],
            task_id=row["task_id"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            status=row["status"],
            exit_code=row["exit_code"],
            output=row["output"],
            output_summary=row["output_summary"],
            duration_sec=row["duration_sec"],
            trigger_source=row["trigger_source"],
            feishu_msg_id=row["feishu_msg_id"],
        )
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_history_store.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git add backend/services/history_store.py tests/test_history_store.py
git commit -m "feat(phase-1): history_store with RunRecord dataclass and SQLite CRUD"
```

---

## Task 1.5: Sync tasks from JSON to SQLite on startup

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\backend\services\sync.py`
- Create: `C:\Users\27825\Desktop\First_cc\tests\test_sync.py`
- Modify: `C:\Users\27825\Desktop\First_cc\backend\main.py`

- [ ] **Step 1: Write `tests/test_sync.py` first**

Write to `C:\Users\27825\Desktop\First_cc\tests\test_sync.py`:

```python
"""Tests for task sync from JSON to SQLite."""
import json
from datetime import datetime
from backend.db.connection import get_connection
from backend.db.init_db import init_db
from backend.services.sync import sync_tasks_from_json
from backend.services.task_store import TaskStore


def test_sync_creates_missing_tasks(temp_data_dir):
    init_db()
    # Write JSON
    claude_home = temp_data_dir / "fake_claude_home"
    path = claude_home / ".claude" / "scheduled_tasks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": 1,
        "tasks": [
            {
                "id": "t_x",
                "name": "test",
                "prompt": "do it",
                "schedule": "0 9 * * *",
                "enabled": True,
                "created_at": "2026-06-19T08:00:00Z",
                "last_run": None,
                "last_status": "never",
            }
        ],
    }
    path.write_text(json.dumps(data))

    sync_tasks_from_json()
    with get_connection() as conn:
        rows = conn.execute("SELECT id, name, prompt FROM tasks").fetchall()
    assert len(rows) == 1
    assert rows[0]["id"] == "t_x"


def test_sync_preserves_mzc_extensions(temp_data_dir):
    init_db()
    # Pre-populate SQLite with MZC extension data
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO tasks (id, name, prompt, schedule, enabled,
               created_at, created_by, tags, synced_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("t_y", "Manual edit", "p", "0 9 * * *", 1,
             "2026-06-19T08:00:00", "H-yue", '["daily"]',
             "2026-06-19T07:00:00"),
        )

    # JSON has the same task but no MZC extensions
    claude_home = temp_data_dir / "fake_claude_home"
    path = claude_home / ".claude" / "scheduled_tasks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": 1,
        "tasks": [
            {
                "id": "t_y",
                "name": "test",
                "prompt": "do it",
                "schedule": "0 9 * * *",
                "enabled": True,
                "created_at": "2026-06-19T08:00:00Z",
                "last_run": None,
                "last_status": "never",
            }
        ],
    }
    path.write_text(json.dumps(data))

    sync_tasks_from_json()
    with get_connection() as conn:
        row = conn.execute("SELECT created_by, tags FROM tasks WHERE id = 't_y'").fetchone()
    assert row["created_by"] == "H-yue"  # preserved
    assert row["tags"] == '["daily"]'  # preserved


def test_sync_removes_deleted_tasks(temp_data_dir):
    init_db()
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO tasks (id, name, prompt, schedule, enabled,
               created_at, synced_at) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("t_z", "Will be deleted", "p", "0 9 * * *", 1,
             "2026-06-19T08:00:00", "2026-06-19T07:00:00"),
        )

    # JSON is empty
    claude_home = temp_data_dir / "fake_claude_home"
    path = claude_home / ".claude" / "scheduled_tasks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"version": 1, "tasks": []}')

    sync_tasks_from_json()
    with get_connection() as conn:
        rows = conn.execute("SELECT id FROM tasks").fetchall()
    assert len(rows) == 0
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_sync.py -v
```

Expected: FAIL with "ModuleNotFoundError: backend.services.sync".

- [ ] **Step 3: Write `backend/services/sync.py`**

Write to `C:\Users\27825\Desktop\First_cc\backend\services\sync.py`:

```python
"""Sync tasks from scheduled_tasks.json into SQLite mirror table."""
import json
import logging
from datetime import datetime

from backend.db.connection import get_connection
from backend.services.task_store import TaskStore

logger = logging.getLogger(__name__)


def sync_tasks_from_json() -> int:
    """Mirror scheduled_tasks.json into the tasks table.

    Strategy:
    - For each task in JSON: upsert into SQLite
    - For each task in SQLite not in JSON: delete (it was removed via Claude Code)
    - Preserve MZC extension fields (created_by, tags) on update

    Returns: number of tasks synced.
    """
    store = TaskStore()
    tasks = store.load_all()
    json_ids = {t.id for t in tasks}
    now = datetime.utcnow().isoformat()

    with get_connection() as conn:
        existing = conn.execute("SELECT id, created_by, tags FROM tasks").fetchall()
        existing_map = {r["id"]: dict(r) for r in existing}

        for task in tasks:
            ext = existing_map.get(task.id, {})
            conn.execute(
                """INSERT INTO tasks
                   (id, name, prompt, schedule, enabled, created_at,
                    created_by, tags, synced_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                     name=excluded.name,
                     prompt=excluded.prompt,
                     schedule=excluded.schedule,
                     enabled=excluded.enabled,
                     synced_at=excluded.synced_at""",
                (
                    task.id,
                    task.name,
                    task.prompt,
                    task.schedule,
                    int(task.enabled),
                    task.created_at.isoformat() if isinstance(task.created_at, datetime) else task.created_at,
                    ext.get("created_by"),
                    json.dumps(ext.get("tags") or task.tags),
                    now,
                ),
            )

        # Delete tasks in SQLite that are no longer in JSON
        for existing_id in existing_map:
            if existing_id not in json_ids:
                conn.execute("DELETE FROM tasks WHERE id = ?", (existing_id,))
                logger.info(f"Removed task {existing_id} (no longer in JSON)")

    logger.info(f"Synced {len(tasks)} tasks from JSON to SQLite")
    return len(tasks)
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_sync.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git add backend/services/sync.py tests/test_sync.py
git commit -m "feat(phase-1): sync tasks from JSON to SQLite, preserving MZC extensions"
```

---

## Task 1.6: GET /api/tasks endpoint

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\backend\api\tasks.py`
- Create: `C:\Users\27825\Desktop\First_cc\tests\test_api_tasks.py`
- Modify: `C:\Users\27825\Desktop\First_cc\backend\main.py`

- [ ] **Step 1: Write `tests/test_api_tasks.py` first**

Write to `C:\Users\27825\Desktop\First_cc\tests\test_api_tasks.py`:

```python
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
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_api_tasks.py -v
```

Expected: FAIL with 404 (route not found).

- [ ] **Step 3: Write `backend/api/tasks.py`**

Write to `C:\Users\27825\Desktop\First_cc\backend\api\tasks.py`:

```python
"""Task CRUD endpoints."""
import json
import logging
from fastapi import APIRouter, HTTPException

from backend.db.connection import get_connection
from backend.services.sync import sync_tasks_from_json
from backend.services.task_store import TaskStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("")
def list_tasks() -> list[dict]:
    """List all tasks, synced from JSON on each call (cheap)."""
    sync_tasks_from_json()
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT id, name, prompt, schedule, enabled, created_at,
                      created_by, tags, next_run_at, last_run_at
               FROM tasks ORDER BY name"""
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


@router.get("/{task_id}")
def get_task(task_id: str) -> dict:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return _row_to_dict(row)


def _row_to_dict(row) -> dict:
    d = dict(row)
    # tags is stored as JSON string
    if isinstance(d.get("tags"), str):
        try:
            d["tags"] = json.loads(d["tags"])
        except json.JSONDecodeError:
            d["tags"] = []
    return d
```

- [ ] **Step 4: Wire router into `backend/main.py`**

Edit `C:\Users\27825\Desktop\First_cc\backend\main.py`. Find the import line:

```python
from backend.api import system
```

Replace with:

```python
from backend.api import system, tasks
```

Then find the `app.include_router(system.router)` line and add after it:

```python
    app.include_router(tasks.router)
```

- [ ] **Step 5: Run tests, verify they pass**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_api_tasks.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Run full test suite**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest -v
```

Expected: All previous tests still pass + 2 new ones.

- [ ] **Step 7: Commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git add backend/api/tasks.py backend/main.py tests/test_api_tasks.py
git commit -m "feat(phase-1): GET /api/tasks endpoint with auto-sync from JSON"
```

---

# Phase 2: Claude Code Runner

**Outcome:** `POST /api/tasks/{id}/run` invokes `claude -p` for the task, captures output, records a `runs` row. `GET /api/runs/{task_id}` shows history.

---

## Task 2.1: claude_runner service with subprocess wrapper

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\backend\services\claude_runner.py`
- Create: `C:\Users\27825\Desktop\First_cc\tests\test_claude_runner.py`

- [ ] **Step 1: Write `tests/test_claude_runner.py` first**

Write to `C:\Users\27825\Desktop\First_cc\tests\test_claude_runner.py`:

```python
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


def test_run_timeout_raises(monkeypatch):
    runner = ClaudeRunner(claude_cli="sleep", timeout_sec=1)
    with pytest.raises(TimeoutError):
        runner.run(prompt="5")  # sleep 5 seconds


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
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_claude_runner.py -v
```

Expected: FAIL with "ModuleNotFoundError: backend.services.claude_runner".

- [ ] **Step 3: Write `backend/services/claude_runner.py`**

Write to `C:\Users\27825\Desktop\First_cc\backend\services\claude_runner.py`:

```python
"""Wrapper around `claude -p` subprocess for one-shot task execution."""
import logging
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from backend.config import get_settings

logger = logging.getLogger(__name__)

# 10 minutes per spec §6.4
DEFAULT_TIMEOUT_SEC = 600


@dataclass
class ClaudeRunResult:
    exit_code: int
    output: str
    error: str
    started_at: datetime
    finished_at: datetime
    duration_sec: int

    @property
    def status(self) -> str:
        if self.exit_code == 0:
            return "success"
        return "failed"


class ClaudeRunner:
    def __init__(self, claude_cli: str | None = None, timeout_sec: int = DEFAULT_TIMEOUT_SEC):
        self.claude_cli = claude_cli or get_settings().claude_cli
        self.timeout_sec = timeout_sec

    def run(self, prompt: str, working_dir: Path | None = None) -> ClaudeRunResult:
        """Run `claude -p "<prompt>"` and return result."""
        started = datetime.utcnow()
        cmd = [self.claude_cli, "-p", prompt, "--output-format", "json"]
        logger.info(f"Running: {' '.join(cmd[:2])} <prompt len={len(prompt)}>")

        kwargs = {
            "capture_output": True,
            "text": True,
            "timeout": self.timeout_sec,
        }
        if working_dir:
            kwargs["cwd"] = str(working_dir)
        if sys.platform == "win32":
            # Suppress console window flash
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        try:
            proc = subprocess.run(cmd, **kwargs)
        except subprocess.TimeoutExpired as e:
            finished = datetime.utcnow()
            logger.error(f"Claude run timed out after {self.timeout_sec}s")
            return ClaudeRunResult(
                exit_code=-1,
                output=(e.stdout or b"").decode("utf-8", errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or ""),
                error=f"Timeout after {self.timeout_sec}s",
                started_at=started,
                finished_at=finished,
                duration_sec=int((finished - started).total_seconds()),
            )

        finished = datetime.utcnow()
        return ClaudeRunResult(
            exit_code=proc.returncode,
            output=proc.stdout,
            error=proc.stderr,
            started_at=started,
            finished_at=finished,
            duration_sec=int((finished - started).total_seconds()),
        )
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_claude_runner.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git add backend/services/claude_runner.py tests/test_claude_runner.py
git commit -m "feat(phase-2): claude_runner subprocess wrapper with timeout + CREATE_NO_WINDOW"
```

---

## Task 2.2: Wire POST /api/tasks/{id}/run endpoint

**Files:**
- Modify: `C:\Users\27825\Desktop\First_cc\backend\api\tasks.py`
- Modify: `C:\Users\27825\Desktop\First_cc\tests\test_api_tasks.py`

- [ ] **Step 1: Add failing test to `tests/test_api_tasks.py`**

Append to `C:\Users\27825\Desktop\First_cc\tests\test_api_tasks.py`:

```python


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
    response = client.post("/api/tasks/t_nope/run")
    assert response.status_code == 404
```

- [ ] **Step 2: Run new tests, verify they fail**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_api_tasks.py -v
```

Expected: 2 new tests FAIL with 405 (Method Not Allowed).

- [ ] **Step 3: Add run endpoint to `backend/api/tasks.py`**

Edit `C:\Users\27825\Desktop\First_cc\backend\api\tasks.py`. Add at the top (with other imports):

```python
from datetime import datetime
from backend.services.claude_runner import ClaudeRunner
from backend.services.history_store import HistoryStore, RunRecord
```

Then add this endpoint after the existing `@router.get("/{task_id}")`:

```python


@router.post("/{task_id}/run")
def run_task(task_id: str) -> dict:
    """Manually trigger a task and record the run."""
    # Ensure tasks are synced first
    sync_tasks_from_json()

    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, prompt, name FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Record as running
    record = RunRecord(
        task_id=task_id,
        started_at=datetime.utcnow(),
        status="running",
        trigger_source="manual_web",
    )
    run_id = HistoryStore().insert(record)

    # Execute
    runner = ClaudeRunner()
    result = runner.run(prompt=row["prompt"])

    # Update record
    record.finished_at = result.finished_at
    record.status = "success" if result.exit_code == 0 else "failed"
    record.exit_code = result.exit_code
    record.output = _truncate_output(result.output, max_bytes=1_000_000)
    record.output_summary = result.output[:500]
    record.duration_sec = result.duration_sec
    record.id = run_id
    HistoryStore()._update(record)  # noqa: SLF001 (private update; we need to add it)

    # Update last_run in JSON
    TaskStore().update_last_run(task_id, result.finished_at, record.status)

    return {
        "id": run_id,
        "task_id": task_id,
        "status": record.status,
        "exit_code": result.exit_code,
        "duration_sec": result.duration_sec,
        "trigger_source": "manual_web",
        "started_at": result.started_at.isoformat(),
        "finished_at": result.finished_at.isoformat(),
    }


def _truncate_output(s: str, max_bytes: int) -> str:
    if len(s.encode("utf-8")) <= max_bytes:
        return s
    return s.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore") + "\n\n[... truncated ...]"
```

- [ ] **Step 4: Add `_update` method to `HistoryStore`**

Edit `C:\Users\27825\Desktop\First_cc\backend\services\history_store.py`. Add this method inside the `HistoryStore` class (after `set_feishu_msg_id`):

```python

    def _update(self, record: RunRecord) -> None:
        """Update an existing run record (by id)."""
        if record.id is None:
            raise ValueError("Cannot update record without id")
        with get_connection() as conn:
            conn.execute(
                """UPDATE runs SET
                   finished_at = :finished_at,
                   status = :status,
                   exit_code = :exit_code,
                   output = :output,
                   output_summary = :output_summary,
                   duration_sec = :duration_sec
                   WHERE id = :id""",
                {**record.to_row(), "id": record.id},
            )
```

- [ ] **Step 5: Run tests**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_api_tasks.py -v
```

Expected: All 4 tests pass.

- [ ] **Step 6: Commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git add backend/api/tasks.py backend/services/history_store.py tests/test_api_tasks.py
git commit -m "feat(phase-2): POST /api/tasks/{id}/run with output capture + run record"
```

---

# Phase 3: APScheduler Auto-Trigger

**Outcome:** Tasks in `scheduled_tasks.json` are loaded into APScheduler on startup. Cron triggers fire automatically, executing `claude -p` and recording runs. Strategy P1 (skip if `last_run` is recent) prevents double-firing when Claude Code is also running.

---

## Task 3.1: scheduler service skeleton

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\backend\services\scheduler.py`
- Create: `C:\Users\27825\Desktop\First_cc\tests\test_scheduler.py`

- [ ] **Step 1: Write `tests/test_scheduler.py` first**

Write to `C:\Users\27825\Desktop\First_cc\tests\test_scheduler.py`:

```python
"""Tests for APScheduler service."""
import json
from datetime import datetime
from unittest.mock import patch, MagicMock
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
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_scheduler.py -v
```

Expected: FAIL with "ModuleNotFoundError: backend.services.scheduler".

- [ ] **Step 3: Write `backend/services/scheduler.py`**

Write to `C:\Users\27825\Desktop\First_cc\backend\services\scheduler.py`:

```python
"""APScheduler-based cron trigger for MZC tasks."""
import logging
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.services.task_store import TaskStore

logger = logging.getLogger(__name__)


class MzcScheduler:
    """Manages scheduled task execution.

    On reload_tasks():
    - Reads scheduled_tasks.json
    - Adds a cron job for each enabled task
    - Tick handler is set in Task 3.2 (anti-dual + execute)
    """

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._tick_handler = None  # set by set_tick_handler

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    def set_tick_handler(self, handler) -> None:
        """Set the function called when a task fires.

        handler signature: handler(task_id: str, prompt: str) -> None
        """
        self._tick_handler = handler

    def reload_tasks(self) -> int:
        """Re-read JSON and rebuild all jobs. Returns count loaded."""
        # Remove all existing MZC jobs (by job id prefix)
        for job in list(self.scheduler.get_jobs()):
            if job.id.startswith("mzc:"):
                self.scheduler.remove_job(job.id)

        store = TaskStore()
        tasks = store.load_all()
        loaded = 0
        for task in tasks:
            if not task.enabled:
                continue
            try:
                trigger = CronTrigger.from_crontab(task.schedule)
            except Exception as e:
                logger.error(f"Invalid cron '{task.schedule}' for {task.id}: {e}")
                continue

            self.scheduler.add_job(
                self._on_tick,
                trigger=trigger,
                id=f"mzc:{task.id}",
                args=[task.id, task.prompt],
                replace_existing=True,
                max_instances=1,
                coalesce=True,
            )
            loaded += 1

        logger.info(f"Loaded {loaded} tasks into scheduler")
        return loaded

    def _on_tick(self, task_id: str, prompt: str) -> None:
        if self._tick_handler is None:
            logger.warning(f"Tick for {task_id} but no handler set; skipping")
            return
        try:
            self._tick_handler(task_id, prompt)
        except Exception:
            logger.exception(f"Tick handler error for {task_id}")

    def get_jobs(self) -> list[dict]:
        """Return list of {id, next_run, name} for inspection."""
        result = []
        for job in self.scheduler.get_jobs():
            result.append({
                "id": job.id.replace("mzc:", "", 1),
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "name": job.name,
            })
        return result
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_scheduler.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git add backend/services/scheduler.py tests/test_scheduler.py
git commit -m "feat(phase-3): APScheduler service loads tasks from JSON with cron triggers"
```

---

## Task 3.2: Tick handler with anti-dual-trigger (strategy P1) + run execution

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\backend\services\executor.py`
- Create: `C:\Users\27825\Desktop\First_cc\tests\test_executor.py`
- Modify: `C:\Users\27825\Desktop\First_cc\requirements.txt`

- [ ] **Step 1: Write `tests/test_executor.py` first**

Write to `C:\Users\27825\Desktop\First_cc\tests\test_executor.py`:

```python
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
    recent = (datetime.utcnow() - timedelta(hours=1)).isoformat()
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
    old = (datetime.utcnow() - timedelta(hours=25)).isoformat()
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
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_executor.py -v
```

Expected: FAIL with "ModuleNotFoundError: backend.services.executor".

- [ ] **Step 3: Write `backend/services/executor.py`**

Write to `C:\Users\27825\Desktop\First_cc\backend\services\executor.py`:

```python
"""Tick handler: executes a task via ClaudeRunner, records the run, updates last_run.

Strategy P1 (anti-dual-trigger): if a task was last_run within ~80% of the
cron interval, assume Claude Code already triggered it and skip.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from croniter import croniter

from backend.services.claude_runner import ClaudeRunner
from backend.services.history_store import HistoryStore, RunRecord
from backend.services.task_store import TaskStore

logger = logging.getLogger(__name__)

ANTI_DUAL_THRESHOLD = 0.8


class TaskExecutor:
    """Called by the scheduler when a task fires."""

    def tick(self, task_id: str, prompt: str) -> None:
        if not self._should_fire(task_id):
            logger.info(f"Skipping {task_id} (strategy P1: too soon after last_run)")
            return

        record = RunRecord(
            task_id=task_id,
            started_at=datetime.utcnow(),
            status="running",
            trigger_source="cron",
        )
        run_id = HistoryStore().insert(record)

        runner = ClaudeRunner()
        result = runner.run(prompt=prompt)

        record.finished_at = result.finished_at
        record.status = "success" if result.exit_code == 0 else "failed"
        record.exit_code = result.exit_code
        record.output = self._truncate(result.output, 1_000_000)
        record.output_summary = result.output[:500]
        record.duration_sec = result.duration_sec
        record.id = run_id
        HistoryStore()._update(record)

        TaskStore().update_last_run(task_id, result.finished_at, record.status)

        logger.info(
            f"Task {task_id} finished: {record.status} "
            f"(exit={result.exit_code}, dur={result.duration_sec}s)"
        )

    def _should_fire(self, task_id: str) -> bool:
        try:
            tasks = TaskStore().load_all()
            task = next((t for t in tasks if t.id == task_id), None)
            if task is None:
                return True
            if task.last_run is None:
                return True
            interval = self._estimate_interval(task.schedule)
            if interval is None:
                return True
            elapsed = datetime.utcnow() - task.last_run.replace(tzinfo=None)
            threshold = interval * ANTI_DUAL_THRESHOLD
            return elapsed > threshold
        except Exception:
            logger.exception(f"_should_fire error for {task_id}; defaulting to fire")
            return True

    @staticmethod
    def _estimate_interval(schedule: str) -> Optional[timedelta]:
        try:
            iter_obj = croniter(schedule, datetime.utcnow())
            t1 = iter_obj.get_next(datetime)
            t2 = iter_obj.get_next(datetime)
            avg = (t2 - t1) / 2
            return avg if avg.total_seconds() > 0 else None
        except Exception:
            return None

    @staticmethod
    def _truncate(s: str, max_bytes: int) -> str:
        if len(s.encode("utf-8")) <= max_bytes:
            return s
        return s.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore") + "\n\n[... truncated ...]"
```

- [ ] **Step 4: Add `croniter` to requirements**

Edit `C:\Users\27825\Desktop\First_cc\requirements.txt`. Add this line:

```
croniter==3.0.3
```

- [ ] **Step 5: Install new dep**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pip install croniter==3.0.3
```

- [ ] **Step 6: Run tests, verify they pass**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_executor.py -v
```

Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git add backend/services/executor.py tests/test_executor.py requirements.txt
git commit -m "feat(phase-3): TaskExecutor with strategy P1 anti-dual-trigger"
```

---

## Task 3.3: Wire scheduler + executor into FastAPI lifespan

**Files:**
- Modify: `C:\Users\27825\Desktop\First_cc\backend\main.py`
- Modify: `C:\Users\27825\Desktop\First_cc\backend\api\system.py`
- Modify: `C:\Users\27825\Desktop\First_cc\tests\test_api_system.py`

- [ ] **Step 1: Replace `backend/main.py`**

Write to `C:\Users\27825\Desktop\First_cc\backend\main.py` (full replacement):

```python
"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from backend.api import system, tasks
from backend.config import get_settings
from backend.db.init_db import init_db
from backend.services.scheduler import MzcScheduler
from backend.services.executor import TaskExecutor

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("MZC service starting (version=0.1.0)")
    init_db()

    executor = TaskExecutor()
    scheduler = MzcScheduler()
    scheduler.set_tick_handler(executor.tick)
    scheduler.start()
    scheduler.reload_tasks()
    app.state.scheduler = scheduler
    app.state.executor = executor

    try:
        yield
    finally:
        scheduler.shutdown()
        logger.info("MZC service stopping")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Mobile Zhongkong",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(system.router)
    app.include_router(tasks.router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
```

- [ ] **Step 2: Add /api/system/jobs endpoint**

Append to `C:\Users\27825\Desktop\First_cc\backend\api\system.py`:

```python


@router.get("/jobs")
def get_scheduled_jobs(request) -> list[dict]:
    """Return all currently scheduled APScheduler jobs."""
    scheduler = request.app.state.scheduler
    return scheduler.get_jobs()
```

- [ ] **Step 3: Add test for /api/system/jobs**

Append to `C:\Users\27825\Desktop\First_cc\tests\test_api_system.py`:

```python


def test_jobs_endpoint_empty(client):
    response = client.get("/api/system/jobs")
    assert response.status_code == 200
    assert response.json() == []
```

- [ ] **Step 4: Run all tests**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest -v
```

Expected: All previous tests pass + 1 new.

- [ ] **Step 5: Commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git add backend/main.py backend/api/system.py tests/test_api_system.py
git commit -m "feat(phase-3): wire scheduler into FastAPI lifespan; expose /api/system/jobs"
```

---

# Phase 4: Feishu Integration

**Outcome:** On task success/failure, push a Feishu interactive card with [查看详情] [再次执行] buttons. Webhook endpoint verifies Feishu signature and processes card callbacks. Failed sends queue in `outbox` for retry.

---

## Task 4.1: feishu_signature verifier

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\backend\auth\__init__.py`
- Create: `C:\Users\27825\Desktop\First_cc\backend\auth\feishu_signature.py`
- Create: `C:\Users\27825\Desktop\First_cc\tests\test_feishu_signature.py`

- [ ] **Step 1: Create `backend/auth/__init__.py`**

Write to `C:\Users\27825\Desktop\First_cc\backend\auth\__init__.py`:
```python

```

- [ ] **Step 2: Write `tests/test_feishu_signature.py` first**

Write to `C:\Users\27825\Desktop\First_cc\tests\test_feishu_signature.py`:

```python
"""Tests for Feishu webhook signature verification."""
import hashlib
import hmac
import base64
import time
from backend.auth.feishu_signature import verify_feishu_signature


def test_verify_valid_signature():
    timestamp = str(int(time.time()))
    encrypt_key = "test_key_123"
    body = '{"event":"test"}'

    string_to_sign = f"{timestamp}\n{encrypt_key}\n{body}"
    digest = hmac.new(
        encrypt_key.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    expected = base64.b64encode(digest).decode("utf-8")

    assert verify_feishu_signature(
        timestamp=timestamp,
        nonce="any",
        body=body,
        signature=expected,
        encrypt_key=encrypt_key,
    ) is True


def test_verify_invalid_signature_rejected():
    assert verify_feishu_signature(
        timestamp="1234",
        nonce="any",
        body='{"event":"x"}',
        signature="invalid_sig_xxx",
        encrypt_key="key",
    ) is False


def test_verify_old_timestamp_rejected():
    old_ts = str(int(time.time()) - 600)
    body = '{"x":1}'
    string_to_sign = f"{old_ts}\nkey\n{body}"
    digest = hmac.new(b"key", string_to_sign.encode(), hashlib.sha256).digest()
    sig = base64.b64encode(digest).decode("utf-8")

    assert verify_feishu_signature(
        timestamp=old_ts, nonce="n", body=body,
        signature=sig, encrypt_key="key",
    ) is False
```

- [ ] **Step 3: Run tests, verify they fail**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_feishu_signature.py -v
```

Expected: FAIL with "ModuleNotFoundError: backend.auth.feishu_signature".

- [ ] **Step 4: Write `backend/auth/feishu_signature.py`**

Write to `C:\Users\27825\Desktop\First_cc\backend\auth\feishu_signature.py`:

```python
"""Feishu webhook signature verification.

Algorithm: HMAC-SHA256 over "{timestamp}\n{encrypt_key}\n{body}", base64 encoded.
"""
import base64
import hashlib
import hmac
import time
from typing import Final

MAX_TIMESTAMP_AGE_SEC: Final = 300


def verify_feishu_signature(
    timestamp: str,
    nonce: str,
    body: str,
    signature: str,
    encrypt_key: str,
    max_age_sec: int = MAX_TIMESTAMP_AGE_SEC,
) -> bool:
    if not timestamp or not signature or not encrypt_key:
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    now = int(time.time())
    if abs(now - ts) > max_age_sec:
        return False
    string_to_sign = f"{timestamp}\n{encrypt_key}\n{body}"
    digest = hmac.new(
        encrypt_key.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)
```

- [ ] **Step 5: Run tests, verify they pass**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_feishu_signature.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git add backend/auth/ tests/test_feishu_signature.py
git commit -m "feat(phase-4): feishu_signature verifier with replay protection"
```

---

## Task 4.2: feishu_client - send interactive card

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\backend\services\feishu_client.py`
- Create: `C:\Users\27825\Desktop\First_cc\tests\test_feishu_client.py`

- [ ] **Step 1: Write `tests/test_feishu_client.py` first**

Write to `C:\Users\27825\Desktop\First_cc\tests\test_feishu_client.py`:

```python
"""Tests for Feishu client - sends interactive cards via webhook URL."""
import pytest
from unittest.mock import patch, AsyncMock
from backend.services.feishu_client import FeishuClient, FeishuCard


def test_build_task_card():
    client = FeishuClient(webhook_url="https://example.com/wh")
    card = client.build_task_card(
        task_name="Daily report",
        status="success",
        output_summary="Report generated successfully",
        task_id="t_1",
        run_id=42,
    )
    assert card.header["title"]["content"] == "✅ Daily report"
    assert "Report generated" in card.body["elements"][0]["text"]["content"]


def test_build_task_card_failure():
    client = FeishuClient(webhook_url="https://example.com/wh")
    card = client.build_task_card(
        task_name="Backup",
        status="failed",
        output_summary="Permission denied",
        task_id="t_2",
        run_id=43,
    )
    assert "❌" in card.header["title"]["content"]


@pytest.mark.asyncio
async def test_send_card_success():
    client = FeishuClient(webhook_url="https://example.com/wh")
    card = client.build_task_card(
        task_name="x", status="success", output_summary="ok",
        task_id="t_x", run_id=1,
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"code": 0, "msg": "ok"}
        result = await client.send(card)
    assert result is True


@pytest.mark.asyncio
async def test_send_card_rate_limited_returns_false():
    client = FeishuClient(webhook_url="https://example.com/wh")
    card = client.build_task_card(
        task_name="x", status="success", output_summary="ok",
        task_id="t_x", run_id=1,
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 429
        result = await client.send(card)
    assert result is False
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_feishu_client.py -v
```

Expected: FAIL with "ModuleNotFoundError: backend.services.feishu_client".

- [ ] **Step 3: Write `backend/services/feishu_client.py`**

Write to `C:\Users\27825\Desktop\First_cc\backend\services\feishu_client.py`:

```python
"""Feishu webhook client - sends interactive cards."""
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from backend.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class FeishuCard:
    header: dict = field(default_factory=dict)
    body: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "msg_type": "interactive",
            "card": {
                "header": self.header,
                "elements": self.body.get("elements", []),
            },
        }


class FeishuClient:
    def __init__(self, webhook_url: str | None = None, timeout_sec: float = 10.0):
        self.webhook_url = webhook_url or "https://open.feishu.cn/open-apis/im/v1/messages"
        self.timeout_sec = timeout_sec

    def build_task_card(
        self,
        task_name: str,
        status: str,
        output_summary: str,
        task_id: str,
        run_id: int,
    ) -> FeishuCard:
        emoji = "✅" if status == "success" else "❌"
        color = "green" if status == "success" else "red"
        header = {
            "title": {"tag": "plain_text", "content": f"{emoji} {task_name}"},
            "template": color,
        }
        body = {
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "plain_text",
                        "content": output_summary[:500] or "(无输出)",
                    },
                },
                {"tag": "hr"},
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "查看详情"},
                            "type": "primary",
                            "value": {
                                "action": "view_detail",
                                "task_id": task_id,
                                "run_id": run_id,
                            },
                        },
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "再次执行"},
                            "type": "default",
                            "value": {
                                "action": "rerun",
                                "task_id": task_id,
                            },
                        },
                    ],
                },
            ]
        }
        return FeishuCard(header=header, body=body)

    async def send(self, card: FeishuCard) -> bool:
        if not self.webhook_url:
            return False
        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                resp = await client.post(self.webhook_url, json=card.to_dict())
            if resp.status_code == 200 and resp.json().get("code") == 0:
                return True
            if resp.status_code == 429:
                logger.warning("Feishu rate limited (429)")
                return False
            logger.error(f"Feishu send failed: {resp.status_code} {resp.text[:200]}")
            return False
        except httpx.HTTPError:
            logger.exception("Feishu send network error")
            return False
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_feishu_client.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git add backend/services/feishu_client.py tests/test_feishu_client.py
git commit -m "feat(phase-4): feishu_client builds task cards and sends via webhook"
```

---

## Task 4.3: outbox - retry queue for failed Feishu sends

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\backend\services\outbox.py`
- Create: `C:\Users\27825\Desktop\First_cc\tests\test_outbox.py`

- [ ] **Step 1: Write `tests/test_outbox.py` first**

Write to `C:\Users\27825\Desktop\First_cc\tests\test_outbox.py`:

```python
"""Tests for outbox - retry queue for failed Feishu sends."""
from datetime import datetime, timedelta
from backend.db.init_db import init_db
from backend.services.outbox import Outbox, OutboxItem


def test_enqueue_creates_row(temp_data_dir):
    init_db()
    outbox = Outbox()
    item = OutboxItem(
        target_url="https://example.com/wh",
        payload='{"msg_type":"interactive","card":{}}',
    )
    item_id = outbox.enqueue(item)
    assert item_id > 0


def test_get_due_returns_only_due_items(temp_data_dir):
    init_db()
    outbox = Outbox()
    past_id = outbox.enqueue(OutboxItem(
        target_url="https://x", payload="{}",
        next_retry_at=(datetime.utcnow() - timedelta(minutes=1)).isoformat(),
    ))
    outbox.enqueue(OutboxItem(
        target_url="https://x", payload="{}",
        next_retry_at=(datetime.utcnow() + timedelta(minutes=10)).isoformat(),
    ))
    due = outbox.get_due(limit=10)
    ids = [item.id for item in due]
    assert past_id in ids


def test_mark_sent_removes_from_due(temp_data_dir):
    init_db()
    outbox = Outbox()
    item = OutboxItem(target_url="https://x", payload="{}")
    item_id = outbox.enqueue(item)
    outbox.mark_sent(item_id)
    due = outbox.get_due(limit=10)
    assert all(i.id != item_id for i in due)


def test_mark_failed_increments_and_reschedules(temp_data_dir):
    init_db()
    outbox = Outbox()
    item = OutboxItem(target_url="https://x", payload="{}")
    item_id = outbox.enqueue(item)
    outbox.mark_failed(item_id, error="timeout", backoff_sec=60)
    item_after = outbox.get(item_id)
    assert item_after.attempts == 1
    assert item_after.last_error == "timeout"
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_outbox.py -v
```

Expected: FAIL with "ModuleNotFoundError: backend.services.outbox".

- [ ] **Step 3: Write `backend/services/outbox.py`**

Write to `C:\Users\27825\Desktop\First_cc\backend\services\outbox.py`:

```python
"""Outbox pattern for Feishu sends that may fail and need retry."""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from backend.db.connection import get_connection

logger = logging.getLogger(__name__)


@dataclass
class OutboxItem:
    target_url: str
    payload: str
    attempts: int = 0
    last_error: Optional[str] = None
    next_retry_at: Optional[str] = None
    created_at: Optional[str] = None
    id: Optional[int] = None


class Outbox:
    def enqueue(self, item: OutboxItem) -> int:
        now = datetime.utcnow().isoformat()
        next_retry = item.next_retry_at or now
        with get_connection() as conn:
            cur = conn.execute(
                """INSERT INTO outbox
                   (payload, target_url, attempts, last_error,
                    next_retry_at, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (item.payload, item.target_url, item.attempts,
                 item.last_error, next_retry, now),
            )
            return cur.lastrowid

    def get_due(self, limit: int = 20) -> list[OutboxItem]:
        now = datetime.utcnow().isoformat()
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM outbox
                   WHERE sent_at IS NULL AND next_retry_at <= ?
                   ORDER BY next_retry_at LIMIT ?""",
                (now, limit),
            ).fetchall()
        return [self._row_to_item(r) for r in rows]

    def get(self, item_id: int) -> OutboxItem | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM outbox WHERE id = ?", (item_id,)
            ).fetchone()
        return self._row_to_item(row) if row else None

    def mark_sent(self, item_id: int) -> None:
        now = datetime.utcnow().isoformat()
        with get_connection() as conn:
            conn.execute(
                "UPDATE outbox SET sent_at = ? WHERE id = ?",
                (now, item_id),
            )

    def mark_failed(self, item_id: int, error: str, backoff_sec: int = 60) -> None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT attempts FROM outbox WHERE id = ?", (item_id,)
            ).fetchone()
            if row is None:
                return
            new_attempts = row["attempts"] + 1
            backoff = min(backoff_sec * (2 ** (new_attempts - 1)), 3600)
            next_retry = (
                datetime.utcnow() + timedelta(seconds=backoff)
            ).isoformat()
            conn.execute(
                """UPDATE outbox SET
                   attempts = ?, last_error = ?, next_retry_at = ?
                   WHERE id = ?""",
                (new_attempts, error, next_retry, item_id),
            )

    def _row_to_item(self, row) -> OutboxItem:
        return OutboxItem(
            id=row["id"],
            target_url=row["target_url"],
            payload=row["payload"],
            attempts=row["attempts"],
            last_error=row["last_error"],
            next_retry_at=row["next_retry_at"],
            created_at=row["created_at"],
        )
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_outbox.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git add backend/services/outbox.py tests/test_outbox.py
git commit -m "feat(phase-4): outbox with exponential backoff for failed Feishu sends"
```

---

## Task 4.4: Wire Feishu push into executor

**Files:**
- Modify: `C:\Users\27825\Desktop\First_cc\backend\services\executor.py`
- Modify: `C:\Users\27825\Desktop\First_cc\tests\test_executor.py`

- [ ] **Step 1: Add Feishu push at end of `tick` in executor.py**

Edit `C:\Users\27825\Desktop\First_cc\backend\services\executor.py`. Add at the top (after other imports):

```python
import json

import httpx

from backend.services.feishu_client import FeishuClient
from backend.services.outbox import Outbox, OutboxItem
```

Then in the `tick` method, find the line:

```python
        logger.info(
            f"Task {task_id} finished: {record.status} "
            f"(exit={result.exit_code}, dur={result.duration_sec}s)"
        )
```

Add AFTER it (still inside `tick`):

```python

        # Look up task name and push Feishu card
        self._push_feishu(task_id, prompt, record)
```

Then add a new private method at the end of the `TaskExecutor` class:

```python

    def _push_feishu(self, task_id: str, prompt: str, record: RunRecord) -> None:
        """Build a card and send via Feishu; on failure, enqueue to outbox."""
        try:
            tasks = TaskStore().load_all()
            task = next((t for t in tasks if t.id == task_id), None)
            task_name = task.name if task else task_id
        except Exception:
            task_name = task_id

        try:
            client = FeishuClient()
            card = client.build_task_card(
                task_name=task_name,
                status=record.status,
                output_summary=record.output_summary or "",
                task_id=task_id,
                run_id=record.id,
            )
            payload_dict = card.to_dict()
            try:
                resp = httpx.post(
                    client.webhook_url, json=payload_dict, timeout=10
                )
                if resp.status_code == 200 and resp.json().get("code") == 0:
                    HistoryStore().set_feishu_msg_id(record.id, str(record.id))
                    return
            except Exception as e:
                logger.warning(f"Feishu send failed; enqueueing: {e}")

            # Fallback: enqueue for retry
            Outbox().enqueue(OutboxItem(
                target_url=client.webhook_url or "https://open.feishu.cn/discard",
                payload=json.dumps(payload_dict, ensure_ascii=False),
            ))
        except Exception:
            logger.exception("Feishu push failed entirely")
```

- [ ] **Step 2: Add test for Feishu push in executor**

Append to `C:\Users\27825\Desktop\First_cc\tests\test_executor.py`:

```python


def test_executor_pushes_feishu_on_success(temp_data_dir):
    init_db()
    _write_task_file(temp_data_dir, "t_feishu")

    with patch("backend.services.executor.ClaudeRunner") as MockRunner, \
         patch("backend.services.executor.httpx.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"code": 0, "msg": "ok"}

        mock_instance = MagicMock()
        mock_instance.run.return_value = ClaudeRunResult(
            exit_code=0, output="done", error="",
            started_at=datetime.now(), finished_at=datetime.now(),
            duration_sec=1,
        )
        MockRunner.return_value = mock_instance

        executor = TaskExecutor()
        executor.tick("t_feishu", "do it")

        assert mock_post.called
```

- [ ] **Step 3: Run tests**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_executor.py -v
```

Expected: 5 passed.

- [ ] **Step 4: Commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git add backend/services/executor.py tests/test_executor.py
git commit -m "feat(phase-4): Feishu push wired into executor with outbox fallback"
```

---

# Phase 5: Cloudflare Tunnel + Access

**Outcome:** Service reachable from phone at public URL (e.g. `https://mzc.example.com`). CF Access requires email login. Unauthenticated requests are rejected with a 401.

---

## Task 5.1: cloudflared install + setup script

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\scripts\cloudflared_setup.ps1`

- [ ] **Step 1: Write `scripts/cloudflared_setup.ps1`**

Write to `C:\Users\27825\Desktop\First_cc\scripts\cloudflared_setup.ps1`:

```powershell
<#
.SYNOPSIS
  Install cloudflared and prepare for NSSM service registration.
.DESCRIPTION
  Downloads cloudflared to C:\Tools\cloudflared\, logs in to Cloudflare,
  creates a tunnel named 'mzc', and writes credentials to
  C:\Users\27825\.cloudflared\.
.NOTES
  Run this ONCE, manually, as the current user. Browser will open for auth.
#>

$ErrorActionPreference = "Stop"
$installDir = "C:\Tools\cloudflared"
$bin = "$installDir\cloudflared.exe"

# 1. Download cloudflared if missing
if (-not (Test-Path $bin)) {
    Write-Host "Downloading cloudflared..."
    New-Item -ItemType Directory -Force -Path $installDir | Out-Null
    Invoke-WebRequest `
        -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" `
        -OutFile $bin
}

# 2. Login (opens browser, interactive)
& $bin login

# 3. Create tunnel (idempotent)
& $bin tunnel create mzc 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Tunnel 'mzc' may already exist; continuing"
}

# 4. List tunnels
& $bin tunnel list

Write-Host ""
Write-Host "Setup complete. Next steps:"
Write-Host "  1. Note the Tunnel ID from the list above"
Write-Host "  2. Create C:\Users\27825\.cloudflared\config.yml with:"
Write-Host "       tunnel: mzc"
Write-Host "       credentials-file: C:\Users\27825\.cloudflared\<TUNNEL_ID>.json"
Write-Host "       ingress:"
Write-Host "         - hostname: mzc.yourdomain.com"
Write-Host "           service: http://127.0.0.1:8765"
Write-Host "         - service: http_status:404"
Write-Host "  3. Run: cloudflared tunnel route dns mzc mzc.yourdomain.com"
Write-Host "  4. Configure Cloudflare Access in the Zero Trust dashboard"
Write-Host "  5. Run scripts\install_services.bat to register cloudflared as a service"
```

- [ ] **Step 2: Verify script syntax (parse only)**

```bash
cd /c/Users/27825/Desktop/First_cc
powershell -NoProfile -Command "[scriptblock]::Create((Get-Content -Raw ./scripts/cloudflared_setup.ps1)) | Out-Null; 'syntax ok'" 2>&1 | head -5
```

Expected: prints "syntax ok".

- [ ] **Step 3: Commit (don't actually run)**

```bash
cd /c/Users\27825/Desktop/First_cc
git add scripts/cloudflared_setup.ps1
git commit -m "feat(phase-5): cloudflared install + setup script (manual one-time run)"
```

> **Note:** This script runs ONCE manually. NSSM service registration is in Phase 6.

---

## Task 5.2: CF Access JWT verifier

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\backend\auth\cloudflare_access.py`
- Create: `C:\Users\27825\Desktop\First_cc\tests\test_cf_access.py`
- Modify: `C:\Users\27825\Desktop\First_cc\requirements.txt`

- [ ] **Step 1: Write `tests/test_cf_access.py` first**

Write to `C:\Users\27825\Desktop\First_cc\tests\test_cf_access.py`:

```python
"""Tests for Cloudflare Access JWT verification."""
import time
import pytest
from backend.auth.cloudflare_access import verify_cf_access_jwt

TEST_AUD = "test-aud-1234567890abcdef"
TEST_TEAM = "testteam"


def _make_token(email: str = "user@example.com", exp_offset: int = 3600,
                audience: str = TEST_AUD) -> str:
    import jwt
    payload = {
        "email": email,
        "aud": [audience],
        "iss": f"https://{TEST_TEAM}.cloudflareaccess.com",
        "sub": "user-sub-id-123",
        "exp": int(time.time()) + exp_offset,
        "iat": int(time.time()),
    }
    return jwt.encode(payload, "secret", algorithm="HS256")


def test_verify_valid_token():
    token = _make_token()
    result = verify_cf_access_jwt(
        token=token,
        team_domain=TEST_TEAM,
        audience=TEST_AUD,
        public_key=None,
    )
    assert result is not None
    assert result["email"] == "user@example.com"


def test_verify_expired_token():
    token = _make_token(exp_offset=-3600)
    result = verify_cf_access_jwt(
        token=token,
        team_domain=TEST_TEAM,
        audience=TEST_AUD,
        public_key=None,
    )
    assert result is None


def test_verify_wrong_audience():
    token = _make_token()
    result = verify_cf_access_jwt(
        token=token,
        team_domain=TEST_TEAM,
        audience="wrong-aud",
        public_key=None,
    )
    assert result is None


def test_verify_malformed_token():
    result = verify_cf_access_jwt(
        token="not.a.valid.jwt",
        team_domain=TEST_TEAM,
        audience=TEST_AUD,
        public_key=None,
    )
    assert result is None
```

- [ ] **Step 2: Add PyJWT to requirements**

Edit `C:\Users\27825\Desktop\First_cc\requirements.txt`. Add:

```
pyjwt==2.9.0
```

Then install:

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pip install pyjwt==2.9.0
```

- [ ] **Step 3: Run tests, verify they fail**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_cf_access.py -v
```

Expected: FAIL with "ModuleNotFoundError: backend.auth.cloudflare_access".

- [ ] **Step 4: Write `backend/auth/cloudflare_access.py`**

Write to `C:\Users\27825\Desktop\First_cc\backend\auth\cloudflare_access.py`:

```python
"""Cloudflare Access JWT verification.

Verifies the Cf-Access-Jwt-Assertion header set by Cloudflare Access.
In production, uses RS256 with the public key from CF's certs endpoint.
For dev/test, pass public_key=None to skip signature verification.
"""
import logging
from typing import Any

import httpx
import jwt

logger = logging.getLogger(__name__)


def get_public_keys(team_domain: str) -> dict:
    """Fetch CF Access public keys."""
    url = f"https://{team_domain}.cloudflareaccess.com/cdn-cgi/access/certs"
    resp = httpx.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def verify_cf_access_jwt(
    token: str,
    team_domain: str,
    audience: str,
    public_key: str | None = None,
) -> dict[str, Any] | None:
    if not token:
        return None
    try:
        options = {
            "verify_aud": True,
            "verify_iss": True,
            "verify_exp": True,
        }
        decode_kwargs = {
            "audience": audience,
            "issuer": f"https://{team_domain}.cloudflareaccess.com",
            "algorithms": ["RS256", "HS256"],
            "options": options,
        }
        if public_key is not None:
            decode_kwargs["key"] = public_key
        else:
            decode_kwargs["options"] = {**options, "verify_signature": False}

        claims = jwt.decode(token, **decode_kwargs)
        if not claims.get("email"):
            return None
        return claims
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid CF Access JWT: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error verifying CF Access JWT: {e}")
        return None
```

- [ ] **Step 5: Run tests, verify they pass**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_cf_access.py -v
```

Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git add backend/auth/cloudflare_access.py tests/test_cf_access.py requirements.txt
git commit -m "feat(phase-5): CF Access JWT verifier with test mode bypass"
```

---

## Task 5.3: Apply CF Access middleware to /api/* (skip /feishu/*)

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\backend\auth\middleware.py`
- Modify: `C:\Users\27825\Desktop\First_cc\backend\main.py`
- Modify: `C:\Users\27825\Desktop\First_cc\tests\test_api_system.py`

- [ ] **Step 1: Write `backend/auth/middleware.py`**

Write to `C:\Users\27825\Desktop\First_cc\backend\auth\middleware.py`:

```python
"""FastAPI middleware: verify CF Access JWT on /api/* paths (except /feishu/*)."""
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.auth.cloudflare_access import verify_cf_access_jwt
from backend.config import get_settings

logger = logging.getLogger(__name__)


class CFAccessMiddleware(BaseHTTPMiddleware):
    PROTECTED_PREFIXES = ("/api/",)
    EXEMPT_PREFIXES = ("/feishu/",)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not any(path.startswith(p) for p in self.PROTECTED_PREFIXES):
            return await call_next(request)
        if any(path.startswith(p) for p in self.EXEMPT_PREFIXES):
            return await call_next(request)

        settings = get_settings()
        if not settings.cf_access_aud or not settings.cf_access_team_domain:
            return await call_next(request)

        token = request.headers.get("Cf-Access-Jwt-Assertion", "")
        if not token:
            return JSONResponse(
                {"detail": "Missing CF Access token"}, status_code=401
            )

        claims = verify_cf_access_jwt(
            token=token,
            team_domain=settings.cf_access_team_domain,
            audience=settings.cf_access_aud,
        )
        if claims is None:
            return JSONResponse(
                {"detail": "Invalid CF Access token"}, status_code=401
            )

        request.state.user_email = claims.get("email")
        return await call_next(request)
```

- [ ] **Step 2: Wire middleware into `main.py`**

Edit `C:\Users\27825\Desktop\First_cc\backend\main.py`. Add to imports:

```python
from backend.auth.middleware import CFAccessMiddleware
```

In `create_app`, add right after `app = FastAPI(...)`:

```python
    app.add_middleware(CFAccessMiddleware)
```

- [ ] **Step 3: Add middleware test**

Append to `C:\Users\27825\Desktop\First_cc\tests\test_api_system.py`:

```python


def test_api_blocks_without_cf_token_when_configured(monkeypatch, temp_data_dir):
    """When CF Access is configured, missing token returns 401."""
    monkeypatch.setenv("MZC_CF_ACCESS_AUD", "test-aud")
    monkeypatch.setenv("MZC_CF_ACCESS_TEAM_DOMAIN", "testteam")

    from backend.main import create_app
    from fastapi.testclient import TestClient
    app = create_app()
    test_client = TestClient(app)

    response = test_client.get("/api/system/status")
    assert response.status_code == 401
```

- [ ] **Step 4: Run all tests**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest -v
```

Expected: All previous tests pass + 1 new.

- [ ] **Step 5: Commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git add backend/auth/middleware.py backend/main.py tests/test_api_system.py
git commit -m "feat(phase-5): CFAccessMiddleware on /api/* (skips /feishu/*)"
```

---

# Phase 6: Windows Service (NSSM)

**Outcome:** MZC service auto-starts on user login, auto-restarts on crash. cloudflared runs as a separate service.

---

## Task 6.1: install_services.bat

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\scripts\install_services.bat`

- [ ] **Step 1: Write `scripts/install_services.bat`**

Write to `C:\Users\27825\Desktop\First_cc\scripts\install_services.bat`:

```batch
@echo off
REM Register MZC service and cloudflared as Windows services via NSSM.
REM
REM Prereqs:
REM   1. NSSM installed at C:\Tools\nssm\nssm.exe (download from https://nssm.cc)
REM   2. cloudflared installed at C:\Tools\cloudflared\cloudflared.exe
REM   3. scripts\cloudflared_setup.ps1 has been run (tunnel + config.yml exist)
REM   4. Python venv created at %~dp0..\.venv

setlocal
set "PROJECT_DIR=%~dp0.."
set "NSSM=C:\Tools\nssm\nssm.exe"
set "CLOUDFLARED=C:\Tools\cloudflared\cloudflared.exe"
set "PYTHON=%PROJECT_DIR%\.venv\Scripts\python.exe"
set "LOG_DIR=%PROJECT_DIR%\logs"

if not exist "%NSSM%" (
    echo ERROR: NSSM not found at %NSSM%
    exit /b 1
)
if not exist "%CLOUDFLARED%" (
    echo ERROR: cloudflared not found at %CLOUDFLARED%
    exit /b 1
)
if not exist "%PYTHON%" (
    echo ERROR: Python venv not found at %PYTHON%
    exit /b 1
)
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM --- MzcControl ---
echo Registering MzcControl service...
"%NSSM%" install MzcControl "%PYTHON%" "-m uvicorn backend.main:app --host 127.0.0.1 --port 8765 --log-level info"
"%NSSM%" set MzcControl AppDirectory "%PROJECT_DIR%"
"%NSSM%" set MzcControl DisplayName "MZC Control Service"
"%NSSM%" set MzcControl Description "Mobile Zhongkong - remote control for Claude Code"
"%NSSM%" set MzcControl Start SERVICE_AUTO_START
"%NSSM%" set MzcControl AppStdout "%LOG_DIR%\mzc.out.log"
"%NSSM%" set MzcControl AppStderr "%LOG_DIR%\mzc.err.log"
"%NSSM%" set MzcControl AppRotateFiles 1
"%NSSM%" set MzcControl AppRotateBytes 10485760
"%NSSM%" set MzcControl AppEnvironmentExtra "PYTHONUNBUFFERED=1"
"%NSSM%" set MzcControl AppThrottle 5000
"%NSSM%" set MzcControl AppRestartDelay 5000
"%NSSM%" set MzcControl AppStdoutCreationDisposition 4
"%NSSM%" set MzcControl AppStderrCreationDisposition 4

REM --- MzcTunnel ---
echo Registering MzcTunnel service...
"%NSSM%" install MzcTunnel "%CLOUDFLARED%" "tunnel run mzc"
"%NSSM%" set MzcTunnel AppDirectory "C:\Users\%USERNAME%\.cloudflared"
"%NSSM%" set MzcTunnel DisplayName "MZC Cloudflare Tunnel"
"%NSSM%" set MzcTunnel Description "Cloudflare tunnel for MZC public access"
"%NSSM%" set MzcTunnel Start SERVICE_AUTO_START
"%NSSM%" set MzcTunnel AppStdout "%LOG_DIR%\tunnel.out.log"
"%NSSM%" set MzcTunnel AppStderr "%LOG_DIR%\tunnel.err.log"
"%NSSM%" set MzcTunnel AppRotateFiles 1
"%NSSM%" set MzcTunnel AppRotateBytes 10485760
"%NSSM%" set MzcTunnel AppThrottle 5000
"%NSSM%" set MzcTunnel AppRestartDelay 5000
"%NSSM%" set MzcTunnel AppStdoutCreationDisposition 4
"%NSSM%" set MzcTunnel AppStderrCreationDisposition 4
"%NSSM%" set MzcTunnel DependOnService MzcControl

REM --- Start services ---
echo Starting MzcControl...
"%NSSM%" start MzcControl
timeout /t 3 /nobreak > nul

echo Starting MzcTunnel...
"%NSSM%" start MzcTunnel
timeout /t 3 /nobreak > nul

echo.
echo === Service Status ===
"%NSSM%" status MzcControl
"%NSSM%" status MzcTunnel

echo.
echo === Local Test ===
curl -s http://127.0.0.1:8765/api/system/status
echo.

echo.
echo Done. Verify public URL: https://mzc.yourdomain.com/api/system/status
```

- [ ] **Step 2: Commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git add scripts/install_services.bat
git commit -m "feat(phase-6): NSSM install script for MzcControl + MzcTunnel services"
```

---

## Task 6.2: uninstall_services.bat

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\scripts\uninstall_services.bat`

- [ ] **Step 1: Write `scripts/uninstall_services.bat`**

Write to `C:\Users\27825\Desktop\First_cc\scripts\uninstall_services.bat`:

```batch
@echo off
REM Stop and remove MZC services.
setlocal
set "NSSM=C:\Tools\nssm\nssm.exe"

if not exist "%NSSM%" (
    echo NSSM not found; nothing to do.
    exit /b 0
)

for %%S in (MzcTunnel MzcControl) do (
    echo Stopping %%S...
    "%NSSM%" stop %%S
    timeout /t 2 /nobreak > nul
    echo Removing %%S...
    "%NSSM%" remove %%S confirm
)

echo Done.
```

- [ ] **Step 2: Commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git add scripts/uninstall_services.bat
git commit -m "feat(phase-6): uninstall script for MZC services"
```

---

## Task 6.3: disable_sleep.ps1

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\scripts\disable_sleep.ps1`

- [ ] **Step 1: Write `scripts/disable_sleep.ps1`**

Write to `C:\Users\27825\Desktop\First_cc\scripts\disable_sleep.ps1`:

```powershell
<#
.SYNOPSIS
  Disable Windows auto-sleep so MZC services can run unattended.
#>

powercfg /change standby-timeout-ac 0
powercfg /hibernate off

# Enable wake timers (so Task Scheduler can wake the machine)
powercfg /setacvalueindex SCHEME_CURRENT 238C9FA8-0AAD-41ED-83F4-97BE242C8F20 29f55cea-bcf3-48a8-9f2b-a4f5b6c7c4d1 1

Write-Host "Sleep disabled. Verify: powercfg /q"
```

- [ ] **Step 2: Commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git add scripts/disable_sleep.ps1
git commit -m "feat(phase-6): disable_sleep.ps1 to prevent auto-sleep on AC power"
```

---

# Phase 7: Backup & Session History

**Outcome:** SQLite DB is backed up nightly. Claude Code session history is readable via API.

---

## Task 7.1: backup_db.ps1

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\scripts\backup_db.ps1`

- [ ] **Step 1: Write `scripts/backup_db.ps1`**

Write to `C:\Users\27825\Desktop\First_cc\scripts\backup_db.ps1`:

```powershell
<#
.SYNOPSIS
  Backup the MZC SQLite database to a dated file. Retain 30 days.
#>

param(
    [string]$SourceDb = "$PSScriptRoot\..\data\mzc.db",
    [string]$BackupRoot = "D:\backups\mzc",
    [int]$RetentionDays = 30
)

$ErrorActionPreference = "Stop"
$date = Get-Date -Format "yyyy-MM-dd"
$dest = Join-Path $BackupRoot "$date.db"

if (-not (Test-Path $SourceDb)) {
    Write-Error "Source DB not found: $SourceDb"
    exit 1
}
if (-not (Test-Path $BackupRoot)) {
    New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
}

$sqliteExe = (Get-Command sqlite3.exe -ErrorAction SilentlyContinue)
if ($sqliteExe) {
    Write-Host "Backing up via sqlite3 .backup..."
    & sqlite3.exe $SourceDb ".backup '$dest'"
} else {
    Write-Host "sqlite3 not found; using file copy"
    Copy-Item $SourceDb $dest -Force
}

$cutoff = (Get-Date).AddDays(-$RetentionDays)
Get-ChildItem $BackupRoot -Filter "*.db" -File | Where-Object {
    $_.LastWriteTime -lt $cutoff
} | ForEach-Object {
    Write-Host "Removing old backup: $($_.Name)"
    Remove-Item $_.FullName
}

Write-Host "Backup complete: $dest"
```

- [ ] **Step 2: Commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git add scripts/backup_db.ps1
git commit -m "feat(phase-7): backup_db.ps1 with 30-day retention"
```

---

## Task 7.2: register_backup_task.ps1

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\scripts\register_backup_task.ps1`

- [ ] **Step 1: Write `scripts/register_backup_task.ps1`**

Write to `C:\Users\27825\Desktop\First_cc\scripts\register_backup_task.ps1`:

```powershell
<#
.SYNOPSIS
  Register a Windows scheduled task that runs backup_db.ps1 nightly at 3 AM.
#>

$taskName = "MzcNightlyBackup"
$scriptPath = "$PSScriptRoot\backup_db.ps1"

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""

$trigger = New-ScheduledTaskTrigger -Daily -At "03:00"

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Register-ScheduledTask -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Nightly backup of MZC SQLite database"

Write-Host "Scheduled task '$taskName' registered. Runs daily at 03:00."
```

- [ ] **Step 2: Commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git add scripts/register_backup_task.ps1
git commit -m "feat(phase-7): register nightly backup scheduled task"
```

---

## Task 7.3: Session history API

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\backend\services\session_store.py`
- Create: `C:\Users\27825\Desktop\First_cc\backend\api\sessions.py`
- Create: `C:\Users\27825\Desktop\First_cc\tests\test_session_store.py`
- Modify: `C:\Users\27825\Desktop\First_cc\backend\main.py`

- [ ] **Step 1: Write `tests/test_session_store.py` first**

Write to `C:\Users\27825\Desktop\First_cc\tests\test_session_store.py`:

```python
"""Tests for session_store - reads Claude Code's JSONL session files."""
import json
from backend.services.session_store import SessionStore


def _write_jsonl(path, messages):
    with open(path, "w", encoding="utf-8") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")


def test_list_sessions_finds_jsonl_files(temp_data_dir):
    projects = temp_data_dir / "fake_claude_home" / ".claude" / "projects"
    project = projects / "myproject"
    project.mkdir(parents=True)
    _write_jsonl(project / "session1.jsonl", [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ])

    store = SessionStore()
    sessions = store.list_sessions()
    assert len(sessions) == 1
    assert sessions[0].id == "session1"
    assert sessions[0].message_count == 2


def test_get_session_messages(temp_data_dir):
    projects = temp_data_dir / "fake_claude_home" / ".claude" / "projects"
    project = projects / "myproject"
    project.mkdir(parents=True)
    _write_jsonl(project / "s1.jsonl", [
        {"role": "user", "content": "msg1"},
        {"role": "assistant", "content": "reply1"},
    ])

    store = SessionStore()
    msgs = store.get_messages("s1")
    assert len(msgs) == 2
    assert msgs[0]["content"] == "msg1"


def test_get_session_first_message_truncated(temp_data_dir):
    projects = temp_data_dir / "fake_claude_home" / ".claude" / "projects"
    project = projects / "myproject"
    project.mkdir(parents=True)
    long_text = "x" * 500
    _write_jsonl(project / "long.jsonl", [
        {"role": "user", "content": long_text},
    ])
    store = SessionStore()
    sessions = store.list_sessions()
    assert len(sessions[0].first_message) == 200
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_session_store.py -v
```

Expected: FAIL with "ModuleNotFoundError: backend.services.session_store".

- [ ] **Step 3: Write `backend/services/session_store.py`**

Write to `C:\Users\27825\Desktop\First_cc\backend\services\session_store.py`:

```python
"""Read Claude Code's session history from JSONL files.

Claude Code stores sessions at:
  ~/.claude/projects/<encoded-path>/<session-id>.jsonl
"""
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from backend.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class Session:
    id: str
    project_path: str
    message_count: int
    first_message: str
    last_active_at: str


class SessionStore:
    def __init__(self):
        self.projects_dir = get_settings().projects_dir

    def list_sessions(self, limit: int = 50) -> list[Session]:
        if not self.projects_dir.exists():
            return []
        sessions = []
        for jsonl in self.projects_dir.rglob("*.jsonl"):
            try:
                session = self._read_session_meta(jsonl)
                if session:
                    sessions.append(session)
            except Exception:
                logger.exception(f"Error reading {jsonl}")
        sessions.sort(key=lambda s: s.last_active_at, reverse=True)
        return sessions[:limit]

    def get_messages(self, session_id: str) -> list[dict]:
        path = self._find_session_file(session_id)
        if path is None:
            return []
        messages = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return messages

    def _find_session_file(self, session_id: str) -> Path | None:
        for jsonl in self.projects_dir.rglob(f"{session_id}.jsonl"):
            return jsonl
        return None

    def _read_session_meta(self, path: Path) -> Session | None:
        session_id = path.stem
        project_path = str(path.parent)
        messages = []
        first_message = ""
        last_mtime = path.stat().st_mtime
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    messages.append(msg)
                    if not first_message and msg.get("content"):
                        first_message = str(msg["content"])[:200]
                except json.JSONDecodeError:
                    continue
        return Session(
            id=session_id,
            project_path=project_path,
            message_count=len(messages),
            first_message=first_message,
            last_active_at=datetime.fromtimestamp(last_mtime).isoformat(),
        )
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_session_store.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Write `backend/api/sessions.py`**

Write to `C:\Users\27825\Desktop\First_cc\backend\api\sessions.py`:

```python
"""Session history endpoints."""
from fastapi import APIRouter, HTTPException

from backend.services.session_store import SessionStore

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("")
def list_sessions() -> list[dict]:
    store = SessionStore()
    sessions = store.list_sessions()
    return [
        {
            "id": s.id,
            "project_path": s.project_path,
            "message_count": s.message_count,
            "first_message": s.first_message,
            "last_active_at": s.last_active_at,
        }
        for s in sessions
    ]


@router.get("/{session_id}/messages")
def get_session_messages(session_id: str) -> list[dict]:
    store = SessionStore()
    msgs = store.get_messages(session_id)
    if not msgs:
        raise HTTPException(status_code=404, detail="Session not found or empty")
    return msgs
```

- [ ] **Step 6: Wire into main.py**

Edit `C:\Users\27825\Desktop\First_cc\backend\main.py`. Add to imports:

```python
from backend.api import system, tasks, sessions
```

In `create_app`, add after `app.include_router(tasks.router)`:

```python
    app.include_router(sessions.router)
```

- [ ] **Step 7: Run all tests**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest -v
```

Expected: All previous tests pass + 3 new.

- [ ] **Step 8: Commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git add backend/services/session_store.py backend/api/sessions.py backend/main.py tests/test_session_store.py
git commit -m "feat(phase-7): session history from Claude Code JSONL files"
```

---

# Phase 8: Web Frontend & Feishu Webhook

**Outcome:** Mobile-friendly single-page UI shows tasks, runs, sessions. Feishu webhook endpoint verifies signatures and processes button callbacks.

---

## Task 8.1: Static web index.html with task list

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\web\index.html`
- Modify: `C:\Users\27825\Desktop\First_cc\backend\main.py` (serve static)

- [ ] **Step 1: Write `web/index.html`**

Write to `C:\Users\27825\Desktop\First_cc\web\index.html`:

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>MZC 控制台</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif;
      background: #f5f5f7;
      color: #1d1d1f;
      padding: 12px;
      max-width: 800px;
      margin: 0 auto;
    }
    h1 { font-size: 20px; margin-bottom: 12px; }
    h2 { font-size: 16px; margin: 16px 0 8px; color: #6e6e73; }
    .card {
      background: white;
      border-radius: 12px;
      padding: 12px;
      margin-bottom: 8px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .card-row { display: flex; justify-content: space-between; align-items: center; }
    .task-name { font-weight: 600; font-size: 15px; }
    .task-meta { color: #6e6e73; font-size: 12px; margin-top: 4px; }
    .btn {
      background: #007aff;
      color: white;
      border: none;
      border-radius: 8px;
      padding: 8px 16px;
      font-size: 14px;
      cursor: pointer;
    }
    .btn:active { background: #0051d5; }
    .btn-secondary { background: #e5e5ea; color: #007aff; }
    .status-success { color: #34c759; }
    .status-failed { color: #ff3b30; }
    .status-pending { color: #8e8e93; }
    .badge {
      display: inline-block;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 11px;
      background: #e5e5ea;
      color: #1d1d1f;
      margin-right: 4px;
    }
    .empty { text-align: center; color: #8e8e93; padding: 24px; }
    .loading { text-align: center; color: #8e8e93; padding: 12px; }
    pre {
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 12px;
      background: #f5f5f7;
      padding: 8px;
      border-radius: 6px;
      max-height: 200px;
      overflow-y: auto;
    }
  </style>
</head>
<body>
  <h1>📱 MZC 控制台</h1>

  <h2>定时任务</h2>
  <div id="tasks" class="loading">加载中…</div>

  <h2>系统状态</h2>
  <div id="system" class="card">加载中…</div>

  <h2>近期会话</h2>
  <div id="sessions" class="loading">加载中…</div>

  <script>
    async function api(path) {
      const r = await fetch(path, { credentials: 'include' });
      if (!r.ok) throw new Error(`${path}: ${r.status}`);
      return r.json();
    }

    function renderTasks(tasks) {
      if (!tasks.length) return '<div class="empty">暂无任务</div>';
      return tasks.map(t => `
        <div class="card">
          <div class="card-row">
            <div>
              <div class="task-name">${escapeHtml(t.name)}</div>
              <div class="task-meta">
                <span class="badge">${escapeHtml(t.schedule)}</span>
                ${t.tags ? t.tags.map(tag => `<span class="badge">${escapeHtml(tag)}</span>`).join('') : ''}
              </div>
              <div class="task-meta">
                上次运行: ${t.last_run || '从未'} ·
                状态: <span class="status-${t.last_status === 'success' ? 'success' : t.last_status === 'failed' ? 'failed' : 'pending'}">${t.last_status || 'never'}</span>
              </div>
            </div>
            <button class="btn" onclick="runTask('${t.id}')">运行</button>
          </div>
        </div>
      `).join('');
    }

    function renderSystem(s) {
      return `
        <div>服务: ${s.service} v${s.version}</div>
        <div class="task-meta">状态: <span class="status-success">${s.status}</span></div>
        <div class="task-meta">时间: ${s.timestamp}</div>
      `;
    }

    function renderSessions(sessions) {
      if (!sessions.length) return '<div class="empty">暂无会话</div>';
      return sessions.slice(0, 5).map(s => `
        <div class="card">
          <div class="task-name">${escapeHtml(s.id.substring(0, 20))}</div>
          <div class="task-meta">${s.message_count} 条消息</div>
          <div class="task-meta">${escapeHtml((s.first_message || '').substring(0, 100))}</div>
        </div>
      `).join('');
    }

    function escapeHtml(s) {
      if (!s) return '';
      return String(s).replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
      }[c]));
    }

    async function runTask(id) {
      if (!confirm('确认手动运行此任务?')) return;
      try {
        const r = await fetch(`/api/tasks/${id}/run`, { method: 'POST', credentials: 'include' });
        const data = await r.json();
        alert(`任务已触发: ${data.status} (${data.duration_sec}秒)`);
        loadAll();
      } catch (e) {
        alert('运行失败: ' + e.message);
      }
    }

    async function loadAll() {
      try {
        const [tasks, sys, sessions] = await Promise.all([
          api('/api/tasks'),
          api('/api/system/status'),
          api('/api/sessions'),
        ]);
        document.getElementById('tasks').innerHTML = renderTasks(tasks);
        document.getElementById('system').innerHTML = renderSystem(sys);
        document.getElementById('sessions').innerHTML = renderSessions(sessions);
      } catch (e) {
        document.getElementById('tasks').innerHTML = `<div class="empty">加载失败: ${e.message}</div>`;
      }
    }

    loadAll();
    setInterval(loadAll, 30000);  // Refresh every 30s
  </script>
</body>
</html>
```

- [ ] **Step 2: Serve static files from FastAPI**

Edit `C:\Users\27825\Desktop\First_cc\backend\main.py`. Add to imports:

```python
from fastapi.staticfiles import StaticFiles
from pathlib import Path
```

In `create_app`, add after the `app.include_router(sessions.router)` line:

```python
    web_dir = Path(__file__).parent.parent / "web"
    if web_dir.exists():
        app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")
```

- [ ] **Step 3: Test it serves**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8765 &
sleep 3
curl -s http://127.0.0.1:8765/ | head -10
```

Expected: HTML content with `<title>MZC 控制台</title>`.

Stop the server:

```bash
.venv/Scripts/python.exe -c "
import psutil, os, signal
for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    if 'uvicorn' in ' '.join(p.info.get('cmdline') or []):
        os.kill(p.info['pid'], signal.SIGTERM)
"
```

- [ ] **Step 4: Commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git add web/index.html backend/main.py
git commit -m "feat(phase-8): mobile-friendly single-page web UI"
```

---

## Task 8.2: Feishu webhook endpoint

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\backend\api\feishu_webhook.py`
- Create: `C:\Users\27825\Desktop\First_cc\tests\test_feishu_webhook.py`
- Modify: `C:\Users\27825\Desktop\First_cc\backend\main.py`

- [ ] **Step 1: Write `tests/test_feishu_webhook.py` first**

Write to `C:\Users\27825\Desktop\First_cc\tests\test_feishu_webhook.py`:

```python
"""Tests for Feishu webhook receiver."""
import hashlib
import hmac
import base64
import json
import time
from unittest.mock import patch, MagicMock
from backend.db.init_db import init_db


def _sign(encrypt_key: str, timestamp: str, body: str) -> str:
    string_to_sign = f"{timestamp}\n{encrypt_key}\n{body}"
    digest = hmac.new(
        encrypt_key.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def test_webhook_rejects_invalid_signature(client, temp_data_dir):
    init_db()
    body = json.dumps({"event": {"type": "test"}})
    response = client.post(
        "/feishu/webhook",
        content=body,
        headers={
            "X-Lark-Request-Timestamp": str(int(time.time())),
            "X-Lark-Request-Nonce": "abc",
            "X-Lark-Signature": "invalid",
        },
    )
    # Either 401 (signature check) or 400 (missing config) - both indicate not-accepted
    assert response.status_code in (400, 401)


def test_webhook_accepts_valid_signature(client, temp_data_dir, monkeypatch):
    init_db()
    monkeypatch.setenv("MZC_FEISHU_WEBHOOK_ENCRYPT_KEY", "test_key")
    monkeypatch.setenv("MZC_FEISHU_WEBHOOK_VERIFY_TOKEN", "test_token")

    from backend.main import create_app
    from fastapi.testclient import TestClient
    app = create_app()
    test_client = TestClient(app)

    body = json.dumps({"event": {"type": "test"}, "type": "event_callback"})
    ts = str(int(time.time()))
    sig = _sign("test_key", ts, body)

    response = test_client.post(
        "/feishu/webhook",
        content=body,
        headers={
            "X-Lark-Request-Timestamp": ts,
            "X-Lark-Request-Nonce": "abc",
            "X-Lark-Signature": sig,
        },
    )
    # Should not be 401 (signature is valid)
    assert response.status_code != 401
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_feishu_webhook.py -v
```

Expected: FAIL with 404 (route not found).

- [ ] **Step 3: Write `backend/api/feishu_webhook.py`**

Write to `C:\Users\27825\Desktop\First_cc\backend\api\feishu_webhook.py`:

```python
"""Feishu webhook receiver for card callbacks and URL verification."""
import json
import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.auth.feishu_signature import verify_feishu_signature
from backend.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feishu", tags=["feishu"])


@router.post("/webhook")
async def feishu_webhook(request: Request):
    """Receive Feishu events. Verifies signature, dispatches by event type.

    Handles:
    - URL verification challenge
    - Card button click callbacks (action: view_detail, rerun)
    """
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8")
    headers = request.headers

    settings = get_settings()
    encrypt_key = settings.feishu_webhook_encrypt_key
    verify_token = settings.feishu_webhook_verify_token

    if not encrypt_key:
        logger.warning("Feishu webhook called but encrypt_key not configured")
        return JSONResponse({"detail": "not configured"}, status_code=400)

    sig = headers.get("X-Lark-Signature", "")
    ts = headers.get("X-Lark-Request-Timestamp", "")
    nonce = headers.get("X-Lark-Request-Nonce", "")

    if not verify_feishu_signature(
        timestamp=ts, nonce=nonce, body=body_str,
        signature=sig, encrypt_key=encrypt_key,
    ):
        logger.warning("Feishu webhook signature verification failed")
        return JSONResponse({"detail": "invalid signature"}, status_code=401)

    try:
        payload = json.loads(body_str)
    except json.JSONDecodeError:
        return JSONResponse({"detail": "invalid json"}, status_code=400)

    # URL verification challenge
    if payload.get("type") == "url_verification":
        return JSONResponse({"challenge": payload.get("challenge", "")})

    # Card action callback
    if payload.get("type") == "event_callback":
        event = payload.get("event", {})
        action = event.get("action", {})
        action_value = action.get("value", {})

        if action_value.get("action") == "view_detail":
            task_id = action_value.get("task_id")
            run_id = action_value.get("run_id")
            logger.info(f"Feishu card: view_detail task={task_id} run={run_id}")
            return JSONResponse({
                "card": {
                    "header": {"title": {"tag": "plain_text", "content": "📄 详情"}},
                    "elements": [{"tag": "plain_text", "content": f"任务 {task_id} 的运行 #{run_id} - 详细查看请打开 Web"}],
                }
            })

        if action_value.get("action") == "rerun":
            task_id = action_value.get("task_id")
            logger.info(f"Feishu card: rerun task={task_id}")
            # Trigger a run (same as POST /api/tasks/{id}/run but async)
            from backend.services.claude_runner import ClaudeRunner
            from backend.services.task_store import TaskStore
            try:
                tasks = TaskStore().load_all()
                task = next((t for t in tasks if t.id == task_id), None)
                if task is None:
                    return JSONResponse({"detail": "task not found"}, status_code=404)
                # Note: in production, this should go through the executor for proper recording
                ClaudeRunner().run(prompt=task.prompt)
            except Exception as e:
                logger.exception(f"Feishu rerun failed: {e}")
                return JSONResponse({"detail": "rerun failed"}, status_code=500)
            return JSONResponse({
                "card": {
                    "header": {"title": {"tag": "plain_text", "content": "🔄 已重新执行"}},
                    "elements": [{"tag": "plain_text", "content": f"任务 {task_id} 已开始执行"}],
                }
            })

    # Default ack
    return JSONResponse({"status": "ok"})
```

- [ ] **Step 4: Wire into main.py**

Edit `C:\Users\27825\Desktop\First_cc\backend\main.py`. Add to imports:

```python
from backend.api import system, tasks, sessions, feishu_webhook
```

In `create_app`, add after `app.include_router(sessions.router)`:

```python
    app.include_router(feishu_webhook.router)
```

- [ ] **Step 5: Run all tests**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest -v
```

Expected: All tests pass + 2 new.

- [ ] **Step 6: Commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git add backend/api/feishu_webhook.py backend/main.py tests/test_feishu_webhook.py
git commit -m "feat(phase-8): Feishu webhook receiver with signature verification and card actions"
```

---

# Phase 9: Smoke Test & Documentation

**Outcome:** End-to-end test that proves the system works. README is complete with setup, usage, troubleshooting.

---

## Task 9.1: End-to-end smoke test script

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\smoke_test.py`
- Create: `C:\Users\27825\Desktop\First_cc\tests\test_smoke.py`

- [ ] **Step 1: Write `tests/test_smoke.py`**

Write to `C:\Users\27825\Desktop\First_cc\tests\test_smoke.py`:

```python
"""End-to-end smoke test: start a test app, hit all endpoints, verify responses."""
import json
from datetime import datetime
from unittest.mock import patch
from backend.db.init_db import init_db


def test_full_workflow(client, temp_data_dir):
    """Simulate: list tasks -> run a task -> check run was recorded."""
    init_db()

    # 1. Setup: write a task
    path = temp_data_dir / "fake_claude_home" / ".claude" / "scheduled_tasks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "version": 1,
        "tasks": [
            {
                "id": "smoke_1",
                "name": "Smoke test",
                "prompt": "do x",
                "schedule": "0 9 * * *",
                "enabled": True,
                "created_at": "2026-06-19T08:00:00",
                "last_run": None,
                "last_status": "never",
            }
        ],
    }))

    # 2. List tasks
    r = client.get("/api/tasks")
    assert r.status_code == 200
    tasks = r.json()
    assert len(tasks) == 1
    assert tasks[0]["id"] == "smoke_1"

    # 3. System status
    r = client.get("/api/system/status")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    # 4. System jobs
    r = client.get("/api/system/jobs")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["id"] == "smoke_1"

    # 5. Run the task (with mocked ClaudeRunner)
    with patch("backend.api.tasks.ClaudeRunner") as MockRunner:
        from backend.services.claude_runner import ClaudeRunResult
        mock_instance = MockRunner.return_value
        mock_instance.run.return_value = ClaudeRunResult(
            exit_code=0, output="smoke ok", error="",
            started_at=datetime.now(), finished_at=datetime.now(),
            duration_sec=1,
        )
        r = client.post("/api/tasks/smoke_1/run")

    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert data["task_id"] == "smoke_1"

    # 6. Verify last_run was updated in JSON
    updated = json.loads(path.read_text())
    task = next(t for t in updated["tasks"] if t["id"] == "smoke_1")
    assert task["last_run"] is not None
    assert task["last_status"] == "success"
```

- [ ] **Step 2: Run smoke test**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv/Scripts/python.exe -m pytest tests/test_smoke.py -v
```

Expected: 1 passed.

- [ ] **Step 3: Commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git add tests/test_smoke.py
git commit -m "test(phase-9): end-to-end smoke test covering list/run/last_run update"
```

---

## Task 9.2: README.md

**Files:**
- Create: `C:\Users\27825\Desktop\First_cc\README.md`

- [ ] **Step 1: Write `README.md`**

Write to `C:\Users\27825\Desktop\First_cc\README.md`:

````markdown
# Mobile Zhongkong (MZC)

Control your home Windows laptop's Claude Code from your phone via web + Feishu.

## What it does

- 📋 View all your `CronCreate` scheduled tasks on your phone
- ▶️ Manually trigger any task from your phone
- 📜 Read Claude Code's session history
- 🔔 Get Feishu notifications with [查看详情] [再次执行] buttons when tasks finish
- 🌐 Public access via Cloudflare Tunnel + Access (no port forwarding needed)

## Architecture

```
Phone (Feishu / Browser)
   ↓ Cloudflare Access (email login)
   ↓ Cloudflare Tunnel
Windows Laptop
   ├─ FastAPI service (127.0.0.1:8765)
   ├─ Claude Code (CLI)
   └─ SQLite + scheduled_tasks.json
```

## Setup (one-time)

### Prerequisites

- Windows 11
- Python 3.11+
- Claude Code installed and authenticated (`claude login`)
- NSSM (download from https://nssm.cc)
- Cloudflare account (free tier)
- Feishu self-built app (free)

### Install

1. Clone this repo to `C:\Users\27825\Desktop\First_cc\`
2. Run setup:
   ```bash
   cd First_cc
   python -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   copy .env.example .env
   notepad .env   # fill in values
   ```
3. Install cloudflared: run `scripts\cloudflared_setup.ps1` (one-time, interactive)
4. Install services: run `scripts\install_services.bat` (requires NSSM)
5. Configure Cloudflare Access in the Zero Trust dashboard
6. Configure Feishu webhook URL in your Feishu app config

## Usage

### View tasks on phone
Open `https://mzc.yourdomain.com` in phone browser. Log in via CF Access.

### Feishu notifications
When any task runs (cron or manual), a card is pushed to Feishu with:
- ✅/❌ status header
- Output summary (first 500 chars)
- [查看详情] button (opens web UI)
- [再次执行] button (triggers re-run)

### View sessions
- Web UI: tap any session card
- API: `GET /api/sessions/{id}/messages`

### Manual run
- Web UI: tap [运行] on a task
- API: `POST /api/tasks/{id}/run`
- Feishu: tap [再次执行] on a card

## Development

### Run tests
```bash
.venv\Scripts\python.exe -m pytest -v
```

### Run locally (dev mode)
```bash
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8765 --reload
```

### View logs
```bash
Get-Content logs\mzc.out.log -Wait
```

## Operations

### Restart services
```bash
nssm restart MzcControl
nssm restart MzcTunnel
```

### Backup database
Manual:
```bash
powershell -File scripts\backup_db.ps1
```
Scheduled (auto): `scripts\register_backup_task.ps1` (runs at 03:00).

### Restore database
Stop service, replace `data\mzc.db` with backup, start service.

### Troubleshoot
See [docs/troubleshooting.md](docs/troubleshooting.md) (or read spec §7.5).

## Project Structure

```
First_cc/
├─ backend/         # FastAPI service
│  ├─ api/         # HTTP endpoints
│  ├─ services/    # Business logic
│  ├─ auth/        # CF Access + Feishu sig
│  └─ db/          # SQLite layer
├─ web/            # Mobile-friendly HTML
├─ scripts/        # Windows install/ops scripts
├─ tests/          # Pytest suite
└─ docs/           # Specs and plans
```

## Tech Stack

- Python 3.11+ / FastAPI / APScheduler
- SQLite (single-user, zero-ops)
- Cloudflare Tunnel + Access (free tier)
- Feishu open platform (free)
- NSSM (Windows service hosting)

## License

Personal use only.
````

- [ ] **Step 2: Commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git add README.md
git commit -m "docs(phase-9): README with setup, usage, and ops instructions"
```

---

## Task 9.3: Run final full test suite

- [ ] **Step 1: Run all tests**

```bash
cd /c/Users\27825/Desktop/First_cc
.venv\Scripts\python.exe -m pytest -v
```

Expected: All tests pass (~30 tests across all modules).

- [ ] **Step 2: Verify no regressions in test count**

Count tests in each file:
```bash
cd /c/Users\27825/Desktop/First_cc
.venv\Scripts\python.exe -m pytest --collect-only -q 2>&1 | tail -1
```

Expected: Should show "X tests collected" where X is the total of all test files.

- [ ] **Step 3: Final commit**

```bash
cd /c/Users\27825/Desktop/First_cc
git log --oneline | head -20
```

Expected: See all phase commits in order.

---

# Final Checklist

After completing all phases, the system should have:

- [x] **Phase 0:** FastAPI service running locally with `/api/system/status`
- [x] **Phase 1:** `GET /api/tasks` returning tasks from Claude Code's JSON
- [x] **Phase 2:** `POST /api/tasks/{id}/run` executing Claude Code CLI
- [x] **Phase 3:** APScheduler auto-triggering tasks with anti-dual strategy
- [x] **Phase 4:** Feishu cards pushed on task completion with [查看详情] [再次执行]
- [x] **Phase 5:** Cloudflare Tunnel + Access protecting the service
- [x] **Phase 6:** MZC + cloudflared running as Windows services
- [x] **Phase 7:** Nightly DB backups + session history API
- [x] **Phase 8:** Mobile web UI + Feishu webhook receiver
- [x] **Phase 9:** End-to-end smoke test + README

Total tasks: **~35 tasks**, each with 3-7 steps. Estimated total: **2-3 weeks** at 1-2 hours/day.

---

# Open Questions (carry into execution)

1. Does Claude Code's CronCreate actually respect `last_run` for skip logic? (Phase 3.2)
   - If not, switch to strategy P2 (delete-and-rewrite JSON).
2. Does Feishu's free tier allow webhook URL verification on self-built apps? (Phase 4.2)
   - May need to use test-mode app or apply for production approval.
3. Will Cloudflare Access work with feishu's IP range, or do we need a separate ingress? (Phase 5.3)
   - Likely fine since /feishu/* is exempt from CF Access middleware.

These are validation tasks to be done during execution, not blockers for starting.

---

*Plan version: v0.1 · Created 2026-06-19 · Ready for execution*

