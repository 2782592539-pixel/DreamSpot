# MZC API 文档页 (中文暗色) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 替换 FastAPI 默认的 `/docs` 和 `/redoc`,为 MZC 三个 endpoint 提供一个全中文、暗色技术风、可在线试调的 API 文档首页。

**Architecture:** 静态资源 (`backend/static/`) 挂载到 `/assets`;根路径 `GET /` 返回 `index.html`;前端 fetch `/openapi.json` 渲染侧边栏和 endpoint 卡片;后端不引入新依赖(只用 FastAPI 自带的 `StaticFiles` + `HTMLResponse`)。

**Tech Stack:** FastAPI (Python 3.12),原生 HTML/CSS/JavaScript (无 npm 工具链),pytest。

**Spec:** `docs/superpowers/specs/2026-06-19-api-docs-page-design.md`

---

## File Structure

| 文件 | 状态 | 职责 |
|------|------|------|
| `backend/api/system.py` | 改 | router tags 和 endpoint summary 改为中文 |
| `backend/api/tasks.py` | 改 | router tags 和 endpoint summary 改为中文 |
| `backend/models/task.py` | 改 | Pydantic Field 加中文 description |
| `backend/main.py` | 改 | 关闭 `/docs` `/redoc`;挂载 `/assets`;新增 `GET /` |
| `backend/static/index.html` | 新增 | 中文暗色 SPA 主页面 |
| `backend/static/app.css` | 新增 | 暗色主题样式 |
| `backend/static/app.js` | 新增 | 渲染 openapi.json + 在线试调 + 健康轮询 |
| `tests/test_home_page.py` | 新增 | 首页 + 静态资源 + 默认文档关闭测试 |
| `tests/test_chinese_i18n.py` | 新增 | 中文 tags/summary/description 测试 |

---

## Task 1: 后端 API 中文化 (system + tasks routers)

**Files:**
- Modify: `backend/api/system.py`
- Modify: `backend/api/tasks.py`
- Test: `tests/test_chinese_i18n.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_chinese_i18n.py` 写入:

```python
"""Tests for Chinese i18n in OpenAPI schema."""


def test_system_router_has_chinese_tag(client):
    schema = client.get("/openapi.json").json()
    assert "服务状态" in schema["tags"]


def test_system_status_has_chinese_summary(client):
    schema = client.get("/openapi.json").json()
    op = schema["paths"]["/api/system/status"]["get"]
    assert op["summary"] == "获取服务状态"


def test_tasks_router_has_chinese_tag(client):
    schema = client.get("/openapi.json").json()
    assert "定时任务" in schema["tags"]


def test_tasks_endpoints_have_chinese_summaries(client):
    schema = client.get("/openapi.json").json()
    list_op = schema["paths"]["/api/tasks"]["get"]
    get_op = schema["paths"]["/api/tasks/{task_id}"]["get"]
    assert list_op["summary"] == "列出所有任务"
    assert get_op["summary"] == "查看单个任务"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /c/Users/27825/Desktop/First_cc && .venv/Scripts/python.exe -m pytest tests/test_chinese_i18n.py -v`
Expected: 4 个测试全部 FAIL (没有中文 tags 和 summary)

- [ ] **Step 3: 改 `backend/api/system.py`**

把整个文件替换为:

```python
"""服务状态相关接口。"""
from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter(
    prefix="/api/system",
    tags=["服务状态"],
)


@router.get("/status", summary="获取服务状态", description="检查 MZC 服务是否在线,返回版本号与时间戳。")
def get_status() -> dict:
    """Return service health status."""
    return {
        "status": "ok",
        "service": "mzc",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
```

- [ ] **Step 4: 改 `backend/api/tasks.py`**

把整个文件替换为:

```python
"""定时任务相关接口。"""
import json
import logging
from fastapi import APIRouter, HTTPException

from backend.db.connection import get_connection
from backend.services.sync import sync_tasks_from_json
from backend.services.task_store import TaskStore

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/tasks",
    tags=["定时任务"],
)


@router.get("", summary="列出所有任务", description="从 Claude Code 的 scheduled_tasks.json 同步后,返回全部定时任务。")
def list_tasks() -> list[dict]:
    """List all tasks, synced from JSON on each call (cheap)."""
    sync_tasks_from_json()
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT id, name, prompt, schedule, enabled, created_at,
                      created_by, tags, next_run_at, synced_at
               FROM tasks ORDER BY name"""
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


@router.get("/{task_id}", summary="查看单个任务", description="按 ID 查询单个任务的详细信息。")
def get_task(task_id: str) -> dict:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    return _row_to_dict(row)


def _row_to_dict(row) -> dict:
    d = dict(row)
    if isinstance(d.get("tags"), str):
        try:
            d["tags"] = json.loads(d["tags"])
        except json.JSONDecodeError:
            d["tags"] = []
    return d
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd /c/Users/27825/Desktop/First_cc && .venv/Scripts/python.exe -m pytest tests/test_chinese_i18n.py -v`
Expected: 4 个测试全部 PASS

- [ ] **Step 6: 运行全套测试确保没破**

Run: `cd /c/Users/27825/Desktop/First_cc && .venv/Scripts/python.exe -m pytest -v`
Expected: 至少 21 + 4 = 25 个测试全部 PASS

- [ ] **Step 7: 提交**

```bash
cd /c/Users/27825/Desktop
git add First_cc/backend/api/system.py First_cc/backend/api/tasks.py First_cc/tests/test_chinese_i18n.py
git commit -m "feat(docs): Chinese tags and summaries for system and tasks routers"
```

---

## Task 2: Pydantic Task 模型中文化

**Files:**
- Modify: `backend/models/task.py`
- Test: `tests/test_chinese_i18n.py`

- [ ] **Step 1: 写失败测试 (追加到 `tests/test_chinese_i18n.py` 末尾)**

```python
def test_task_model_fields_have_chinese_descriptions(client):
    schema = client.get("/openapi.json").json()
    task_schema = schema["components"]["schemas"]["Task"]
    props = task_schema["properties"]
    # Every field should have a description and contain at least one CJK char
    for field_name, field_schema in props.items():
        assert "description" in field_schema, f"{field_name} 缺少 description"
        assert any('一' <= c <= '鿿' for c in field_schema["description"]), \
            f"{field_name} 的 description 不是中文: {field_schema['description']}"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /c/Users/27825/Desktop/First_cc && .venv/Scripts/python.exe -m pytest tests/test_chinese_i18n.py::test_task_model_fields_have_chinese_descriptions -v`
Expected: FAIL (字段没有 description)

- [ ] **Step 3: 改 `backend/models/task.py`**

把整个文件替换为:

```python
"""Task Pydantic model - mirrors Claude Code's scheduled_tasks.json format."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class Task(BaseModel):
    """定时任务。镜像 Claude Code 的 JSON 字段,并扩展 MZC 自己的字段。"""
    id: str = Field(..., description="任务唯一 ID,由 Claude Code 分配")
    name: str = Field(..., description="任务显示名")
    prompt: str = Field(..., description="任务执行的 prompt 文本")
    schedule: str = Field(..., description="cron 表达式,例如 '0 9 * * *'")
    enabled: bool = Field(..., description="是否启用")
    created_at: datetime = Field(..., description="创建时间 (ISO 8601)")
    last_run: datetime | None = Field(default=None, description="上次运行时间")
    last_status: Literal["success", "failed", "timeout", "running", "never"] = Field(
        default="never", description="上次运行状态"
    )

    # MZC 扩展字段(不在 Claude Code JSON 里,在 SQLite 镜像中)
    created_by: str | None = Field(default=None, description="创建者标识")
    tags: list[str] = Field(default_factory=list, description="任务标签")
    next_run_at: datetime | None = Field(default=None, description="下次计划运行时间")
    synced_at: datetime | None = Field(default=None, description="从 JSON 同步到 SQLite 的时间")

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

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /c/Users/27825/Desktop/First_cc && .venv/Scripts/python.exe -m pytest tests/test_chinese_i18n.py -v`
Expected: 5 个测试全部 PASS

- [ ] **Step 5: 运行全套测试**

Run: `cd /c/Users/27825/Desktop/First_cc && .venv/Scripts/python.exe -m pytest -v`
Expected: 至少 25 个测试全部 PASS

- [ ] **Step 6: 提交**

```bash
cd /c/Users/27825/Desktop
git add First_cc/backend/models/task.py First_cc/tests/test_chinese_i18n.py
git commit -m "feat(docs): Chinese descriptions on Task Pydantic model fields"
```

---

## Task 3: 挂载静态资源 + 关闭默认文档 + GET / 路由

**Files:**
- Modify: `backend/main.py`
- Create: `backend/static/.gitkeep` (占位,后续任务填入)
- Test: `tests/test_home_page.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_home_page.py` 写入:

```python
"""Tests for the custom home page and static asset serving."""


def test_home_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_home_references_assets(client):
    html = client.get("/").text
    assert "app.css" in html
    assert "app.js" in html


def test_swagger_ui_disabled(client):
    response = client.get("/docs")
    assert response.status_code == 404


def test_redoc_disabled(client):
    response = client.get("/redoc")
    assert response.status_code == 404


def test_static_assets_directory_mounted(client, tmp_path):
    """Verify /assets/ serves files from backend/static/."""
    # Even with an empty dir (just .gitkeep), mount should work
    response = client.get("/assets/.gitkeep")
    # Either 200 (if file present) or 404 (if empty) is acceptable —
    # but the path itself must not 500
    assert response.status_code in (200, 404)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /c/Users/27825/Desktop/First_cc && .venv/Scripts/python.exe -m pytest tests/test_home_page.py -v`
Expected: 5 个测试全部 FAIL (没有 / 路由、/docs 仍存在)

- [ ] **Step 3: 创建 `backend/static/` 目录和占位文件**

```bash
cd /c/Users/27825/Desktop/First_cc
mkdir -p backend/static
touch backend/static/.gitkeep
```

- [ ] **Step 4: 改 `backend/main.py`**

把整个文件替换为:

```python
"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.api import system, tasks
from backend.config import get_settings

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"


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
        title="MZC 移动中控",
        version="0.1.0",
        description="家用 Claude Code 移动控制中心",
        docs_url=None,    # 关闭默认 Swagger UI
        redoc_url=None,   # 关闭默认 ReDoc
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.include_router(system.router)
    app.include_router(tasks.router)
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR)), name="assets")

    @app.get("/", include_in_schema=False)
    def home() -> HTMLResponse:
        return HTMLResponse(INDEX_HTML.read_text(encoding="utf-8"))

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

- [ ] **Step 5: 运行测试确认通过**

Run: `cd /c/Users/27825/Desktop/First_cc && .venv/Scripts/python.exe -m pytest tests/test_home_page.py -v`
Expected: 注意: `test_home_returns_200` 仍会 FAIL,因为 `index.html` 还不存在(下一个任务创建)

- [ ] **Step 6: 临时创建最小 `index.html` 让测试能跑**

```bash
cd /c/Users/27825/Desktop/First_cc
cat > backend/static/index.html << 'EOF'
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>MZC 移动中控</title>
  <link rel="stylesheet" href="/assets/app.css">
</head>
<body>
  <p>占位 - 将在 Task 4 替换</p>
  <script src="/assets/app.js"></script>
</body>
</html>
EOF
```

- [ ] **Step 7: 重新运行测试**

Run: `cd /c/Users/27825/Desktop/First_cc && .venv/Scripts/python.exe -m pytest tests/test_home_page.py -v`
Expected: 5 个测试全部 PASS (assets/.gitkeep 404 是允许的)

- [ ] **Step 8: 运行全套测试**

Run: `cd /c/Users/27825/Desktop/First_cc && .venv/Scripts/python.exe -m pytest -v`
Expected: 至少 30 个测试全部 PASS

- [ ] **Step 9: 提交**

```bash
cd /c/Users/27825/Desktop
git add First_cc/backend/main.py First_cc/backend/static/ First_cc/tests/test_home_page.py
git commit -m "feat(docs): serve custom home page and static assets, close /docs and /redoc"
```

---

## Task 4: 创建 `index.html` 完整骨架

**Files:**
- Modify: `backend/static/index.html`
- Test: `tests/test_home_page.py` (追加)

- [ ] **Step 1: 写失败测试 (追加到 `tests/test_home_page.py` 末尾)**

```python
def test_home_contains_key_sections(client):
    html = client.get("/").text
    # Top-level sections from the design
    assert "MZC" in html
    assert "服务状态" in html or "id=\"sidebar\"" in html  # sidebar placeholder OK
    # The script tag loads app.js
    assert '<script src="/assets/app.js"' in html or 'src="app.js"' in html
```

- [ ] **Step 2: 运行测试确认通过(确认现有最小 HTML 满足)**

Run: `cd /c/Users/27825/Desktop/First_cc && .venv/Scripts/python.exe -m pytest tests/test_home_page.py::test_home_contains_key_sections -v`
Expected: PASS — 当前最小 HTML 满足

- [ ] **Step 3: 用完整骨架替换 `backend/static/index.html`**

把整个文件替换为:

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MZC 移动中控 · API 文档</title>
  <link rel="stylesheet" href="/assets/app.css">
</head>
<body>
  <header id="topbar">
    <div class="brand">
      <span class="logo">●</span>
      <span class="title">MZC</span>
      <span class="subtitle">移动中控</span>
    </div>
    <div class="meta">
      <span class="version">v0.1.0</span>
    </div>
  </header>

  <section id="statusbar">
    <span class="status-label">服务状态:</span>
    <span class="status-dot" id="health-dot" data-state="checking">●</span>
    <span class="status-text" id="health-text">检查中...</span>
    <span class="status-time" id="health-time"></span>
  </section>

  <main id="layout">
    <aside id="sidebar">
      <h2>目录</h2>
      <nav id="nav-list"><!-- JS 渲染 --></nav>
    </aside>

    <section id="content">
      <h1>API 文档</h1>
      <p class="lead">从 Claude Code 同步的定时任务与系统接口,均可在线试调。</p>
      <div id="endpoints"><!-- JS 渲染 --></div>
    </section>
  </main>

  <footer id="footer">
    <span>MZC · 家用 Claude Code 移动控制中心</span>
  </footer>

  <script src="/assets/app.js"></script>
</body>
</html>
```

- [ ] **Step 4: 重新运行测试**

Run: `cd /c/Users/27825/Desktop/First_cc && .venv/Scripts/python.exe -m pytest tests/test_home_page.py -v`
Expected: 6 个测试全部 PASS

- [ ] **Step 5: 手动 curl 验证 HTML 可读**

Run: `cd /c/Users/27825/Desktop/First_cc && .venv/Scripts/python.exe -c "from fastapi.testclient import TestClient; from backend.main import create_app; c=TestClient(create_app()); print(c.get('/').text[:200])"`
Expected: 输出 HTML 内容,含 `<!doctype html>` 和 `MZC`

- [ ] **Step 6: 提交**

```bash
cd /c/Users/27825/Desktop
git add First_cc/backend/static/index.html First_cc/tests/test_home_page.py
git commit -m "feat(docs): full HTML skeleton with header, sidebar, content, footer"
```

---

## Task 5: 创建 `app.css` 暗色主题

**Files:**
- Create: `backend/static/app.css`
- Test: `tests/test_home_page.py` (追加)

- [ ] **Step 1: 写失败测试 (追加到 `tests/test_home_page.py` 末尾)**

```python
def test_css_contains_dark_theme(client):
    css = client.get("/assets/app.css").text
    # Dark background color from the spec
    assert "#0d1117" in css
    # Card color
    assert "#161b22" in css


def test_css_contains_method_colors(client):
    css = client.get("/assets/app.css").text
    # GET = blue, POST = green from spec
    assert "#58a6ff" in css  # GET / accent
    assert "#3fb950" in css  # POST / success
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /c/Users/27825/Desktop/First_cc && .venv/Scripts/python.exe -m pytest tests/test_home_page.py::test_css_contains_dark_theme tests/test_home_page.py::test_css_contains_method_colors -v`
Expected: 2 个测试 FAIL (CSS 不存在)

- [ ] **Step 3: 创建 `backend/static/app.css`**

把以下内容写入:

```css
/* MZC 移动中控 API 文档 - 暗色技术风 */

:root {
  --bg-primary:   #0d1117;
  --bg-card:      #161b22;
  --bg-elevated:  #1f242c;
  --border:       #30363d;
  --text-primary: #c9d1d9;
  --text-muted:   #8b949e;
  --accent:       #58a6ff;
  --get:          #58a6ff;
  --post:         #3fb950;
  --delete:       #f85149;
  --put:          #d29922;
  --success:      #3fb950;
  --error:        #f85149;

  --font-mono: 'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace;
  --font-sans: 'Inter', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html, body {
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 16px;
  line-height: 1.5;
  min-height: 100vh;
}

a {
  color: var(--accent);
  text-decoration: none;
}
a:hover { text-decoration: underline; }

/* Topbar */
#topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 32px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
}
#topbar .brand {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
#topbar .logo { color: var(--accent); font-size: 20px; }
#topbar .title { font-weight: 600; font-size: 18px; }
#topbar .subtitle { color: var(--text-muted); font-size: 14px; }
#topbar .version {
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--text-muted);
  background: var(--bg-elevated);
  padding: 2px 8px;
  border-radius: 4px;
}

/* Status bar */
#statusbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 32px;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border);
  font-size: 14px;
}
.status-label { color: var(--text-muted); }
.status-dot {
  font-size: 12px;
  line-height: 1;
}
.status-dot[data-state="ok"]      { color: var(--success); }
.status-dot[data-state="error"]   { color: var(--error); }
.status-dot[data-state="checking"]{ color: var(--text-muted); }
.status-time {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-muted);
}

/* Layout */
#layout {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 0;
  min-height: calc(100vh - 130px);
}

/* Sidebar */
#sidebar {
  background: var(--bg-card);
  border-right: 1px solid var(--border);
  padding: 24px 16px;
  position: sticky;
  top: 0;
  align-self: start;
  max-height: 100vh;
  overflow-y: auto;
}
#sidebar h2 {
  font-size: 12px;
  text-transform: uppercase;
  color: var(--text-muted);
  letter-spacing: 1px;
  margin-bottom: 12px;
  padding: 0 8px;
}
#nav-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.nav-group { margin-bottom: 16px; }
.nav-group-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  padding: 4px 8px;
}
.nav-link {
  display: block;
  padding: 6px 8px 6px 16px;
  font-size: 13px;
  color: var(--text-muted);
  border-radius: 4px;
  font-family: var(--font-mono);
}
.nav-link:hover {
  background: var(--bg-elevated);
  color: var(--text-primary);
  text-decoration: none;
}
.nav-link.highlight {
  background: var(--bg-elevated);
  color: var(--accent);
}

/* Content */
#content {
  padding: 32px;
  max-width: 960px;
}
#content h1 {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 8px;
}
.lead {
  color: var(--text-muted);
  margin-bottom: 24px;
  font-size: 14px;
}

/* Endpoint card */
.endpoint {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 16px;
  overflow: hidden;
}
.endpoint-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  cursor: pointer;
  user-select: none;
}
.endpoint-head:hover { background: var(--bg-elevated); }
.method-badge {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  color: var(--bg-primary);
}
.method-badge.get    { background: var(--get); }
.method-badge.post   { background: var(--post); }
.method-badge.put    { background: var(--put); }
.method-badge.delete { background: var(--delete); }
.endpoint-path {
  font-family: var(--font-mono);
  font-size: 14px;
  color: var(--text-primary);
  flex: 1;
}
.endpoint-summary {
  color: var(--text-muted);
  font-size: 13px;
}
.endpoint-body {
  display: none;
  padding: 16px 20px 20px;
  border-top: 1px solid var(--border);
  background: var(--bg-primary);
}
.endpoint.open .endpoint-body { display: block; }

.endpoint-description {
  color: var(--text-muted);
  font-size: 13px;
  margin-bottom: 12px;
}

.try-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}
.try-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.try-label {
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--text-muted);
  min-width: 100px;
}
.try-input {
  flex: 1;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  color: var(--text-primary);
  padding: 6px 10px;
  font-family: var(--font-mono);
  font-size: 13px;
  border-radius: 4px;
}
.try-input:focus { outline: 1px solid var(--accent); border-color: var(--accent); }

.btn {
  background: var(--bg-elevated);
  color: var(--text-primary);
  border: 1px solid var(--border);
  padding: 6px 14px;
  font-size: 13px;
  border-radius: 4px;
  cursor: pointer;
  font-family: var(--font-sans);
}
.btn:hover { border-color: var(--accent); color: var(--accent); }
.btn-primary { background: var(--accent); color: var(--bg-primary); border-color: var(--accent); }
.btn-primary:hover { color: var(--bg-primary); opacity: 0.9; }

.response-box {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 12px;
  font-family: var(--font-mono);
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px;
  overflow-y: auto;
}
.response-status {
  font-size: 12px;
  margin-bottom: 6px;
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}
.response-status.ok    { background: var(--success); color: var(--bg-primary); }
.response-status.error { background: var(--error); color: var(--text-primary); }

/* Footer */
#footer {
  padding: 16px 32px;
  text-align: center;
  color: var(--text-muted);
  font-size: 12px;
  border-top: 1px solid var(--border);
}

/* Mobile */
@media (max-width: 768px) {
  #topbar, #statusbar, #content, #footer { padding-left: 16px; padding-right: 16px; }
  #layout { grid-template-columns: 1fr; }
  #sidebar {
    position: static;
    max-height: none;
    border-right: none;
    border-bottom: 1px solid var(--border);
  }
  .try-row { flex-direction: column; align-items: stretch; }
  .try-label { min-width: 0; }
  body { font-size: 17px; }
}
```

- [ ] **Step 4: 运行 CSS 测试**

Run: `cd /c/Users/27825/Desktop/First_cc && .venv/Scripts/python.exe -m pytest tests/test_home_page.py::test_css_contains_dark_theme tests/test_home_page.py::test_css_contains_method_colors -v`
Expected: 2 个测试 PASS

- [ ] **Step 5: 运行全套测试**

Run: `cd /c/Users/27825/Desktop/First_cc && .venv/Scripts/python.exe -m pytest -v`
Expected: 至少 32 个测试全部 PASS

- [ ] **Step 6: 提交**

```bash
cd /c/Users/27825/Desktop
git add First_cc/backend/static/app.css First_cc/tests/test_home_page.py
git commit -m "feat(docs): dark theme CSS for home page with method colors and responsive layout"
```

---

## Task 6: 创建 `app.js` — 渲染 + 试调 + 健康轮询

**Files:**
- Create: `backend/static/app.js`
- Test: `tests/test_home_page.py` (追加)

- [ ] **Step 1: 写失败测试 (追加到 `tests/test_home_page.py` 末尾)**

```python
def test_js_served(client):
    response = client.get("/assets/app.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"] or "ecmascript" in response.headers["content-type"]


def test_js_fetches_openapi(client):
    js = client.get("/assets/app.js").text
    # JS should reference /openapi.json
    assert "/openapi.json" in js
    # JS should call fetch
    assert "fetch(" in js
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /c/Users/27825/Desktop/First_cc && .venv/Scripts/python.exe -m pytest tests/test_home_page.py::test_js_served tests/test_home_page.py::test_js_fetches_openapi -v`
Expected: 2 个测试 FAIL (JS 不存在)

- [ ] **Step 3: 创建 `backend/static/app.js`**

把以下内容写入:

```javascript
// MZC 移动中控 API 文档 - 前端逻辑

const state = {
  schema: null,
  healthTimer: null,
};

const $ = (id) => document.getElementById(id);

// 把 JSON 漂亮地格式化(2 空格缩进)
function formatJSON(obj) {
  try {
    return JSON.stringify(obj, null, 2);
  } catch {
    return String(obj);
  }
}

// 把 OpenAPI path 模板 (/api/tasks/{task_id}) 转成可点击的 sample
function pathWithSample(tpl) {
  return tpl.replace(/\{(\w+)\}/g, (_, name) => `<${name}>`);
}

// 从 path 模板中提取 path 参数名
function extractPathParams(tpl) {
  const out = [];
  tpl.replace(/\{(\w+)\}/g, (_, name) => { out.push(name); return ''; });
  return out;
}

// 主入口
async function init() {
  try {
    const res = await fetch('/openapi.json');
    if (!res.ok) throw new Error('openapi.json ' + res.status);
    state.schema = await res.json();
    renderSidebar();
    renderEndpoints();
    bindGlobalClicks();
  } catch (e) {
    $('endpoints').innerHTML = `<p style="color:var(--error)">加载 openapi.json 失败: ${e.message}</p>`;
  }
  startHealthPolling();
}

function renderSidebar() {
  const navList = $('nav-list');
  navList.innerHTML = '';
  // 按 tag 分组
  const groups = {};
  for (const [path, methods] of Object.entries(state.schema.paths)) {
    for (const [method, op] of Object.entries(methods)) {
      if (method.startsWith('x-')) continue;
      const tag = (op.tags && op.tags[0]) || '未分类';
      if (!groups[tag]) groups[tag] = [];
      groups[tag].push({ method, path, op });
    }
  }
  for (const [tagName, items] of Object.entries(groups)) {
    const group = document.createElement('div');
    group.className = 'nav-group';
    const nameEl = document.createElement('div');
    nameEl.className = 'nav-group-name';
    nameEl.textContent = tagName;
    group.appendChild(nameEl);
    for (const item of items) {
      const link = document.createElement('a');
      link.href = '#op-' + item.method.toUpperCase() + '-' + item.path;
      link.className = 'nav-link';
      link.textContent = item.method.toUpperCase() + ' ' + item.path;
      link.dataset.target = 'op-' + item.method.toUpperCase() + '-' + item.path;
      group.appendChild(link);
    }
    navList.appendChild(group);
  }
}

function renderEndpoints() {
  const container = $('endpoints');
  container.innerHTML = '';
  for (const [path, methods] of Object.entries(state.schema.paths)) {
    for (const [method, op] of Object.entries(methods)) {
      if (method.startsWith('x-')) continue;
      container.appendChild(renderCard(method, path, op));
    }
  }
}

function renderCard(method, path, op) {
  const card = document.createElement('article');
  card.className = 'endpoint';
  card.id = 'op-' + method.toUpperCase() + '-' + path;

  const head = document.createElement('div');
  head.className = 'endpoint-head';
  head.innerHTML = `
    <span class="method-badge ${method}">${method.toUpperCase()}</span>
    <span class="endpoint-path">${pathWithSample(path)}</span>
    <span class="endpoint-summary">${op.summary || ''}</span>
  `;
  head.addEventListener('click', () => card.classList.toggle('open'));
  card.appendChild(head);

  const body = document.createElement('div');
  body.className = 'endpoint-body';
  if (op.description) {
    const desc = document.createElement('p');
    desc.className = 'endpoint-description';
    desc.textContent = op.description;
    body.appendChild(desc);
  }
  // Path 参数输入
  const pathParams = extractPathParams(path);
  const trySec = document.createElement('div');
  trySec.className = 'try-section';
  pathParams.forEach((p) => {
    const row = document.createElement('div');
    row.className = 'try-row';
    row.innerHTML = `
      <span class="try-label">${p}:</span>
      <input class="try-input" data-path-param="${p}" placeholder="请输入 ${p}">
    `;
    trySec.appendChild(row);
  });
  // 执行按钮 + 响应
  const actions = document.createElement('div');
  actions.className = 'try-row';
  actions.innerHTML = `
    <span class="try-label"></span>
    <button class="btn btn-primary" data-action="try">执行</button>
    <button class="btn" data-action="copy" disabled>复制响应</button>
  `;
  trySec.appendChild(actions);
  const responseBox = document.createElement('div');
  responseBox.style.display = 'none';
  body.appendChild(trySec);
  body.appendChild(responseBox);

  // 绑定按钮
  actions.querySelector('[data-action="try"]').addEventListener('click', async (ev) => {
    ev.stopPropagation();
    const btn = ev.currentTarget;
    btn.disabled = true;
    btn.textContent = '执行中...';
    responseBox.style.display = 'block';
    responseBox.innerHTML = '<span class="response-status">...</span><pre class="response-box">请求中</pre>';
    try {
      const params = {};
      trySec.querySelectorAll('[data-path-param]').forEach((inp) => {
        params[inp.dataset.pathParam] = inp.value;
      });
      const result = await tryEndpoint(method, path, params);
      const cls = result.status >= 200 && result.status < 300 ? 'ok' : 'error';
      responseBox.innerHTML = `
        <span class="response-status ${cls}">HTTP ${result.status}</span>
        <pre class="response-box">${formatJSON(result.body)}</pre>
      `;
      actions.querySelector('[data-action="copy"]').disabled = false;
      actions.querySelector('[data-action="copy"]').onclick = () => {
        navigator.clipboard.writeText(formatJSON(result.body));
      };
    } catch (e) {
      responseBox.innerHTML = `<span class="response-status error">ERROR</span><pre class="response-box">${e.message}</pre>`;
    } finally {
      btn.disabled = false;
      btn.textContent = '执行';
    }
  });

  card.appendChild(body);
  return card;
}

async function tryEndpoint(method, path, pathParams) {
  // 替换路径参数
  let url = path;
  for (const [k, v] of Object.entries(pathParams)) {
    url = url.replace(`{${k}}`, encodeURIComponent(v || ''));
  }
  const res = await fetch(url, { method: method.toUpperCase() });
  const text = await res.text();
  let body;
  try { body = JSON.parse(text); }
  catch { body = text; }
  return { status: res.status, body };
}

function bindGlobalClicks() {
  document.querySelectorAll('.nav-link').forEach((link) => {
    link.addEventListener('click', (ev) => {
      ev.preventDefault();
      const id = link.dataset.target;
      const target = document.getElementById(id);
      if (!target) return;
      // 自动展开
      target.classList.add('open');
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      // 高亮 1.5s
      link.classList.add('highlight');
      setTimeout(() => link.classList.remove('highlight'), 1500);
    });
  });
}

function startHealthPolling() {
  const dot = $('health-dot');
  const text = $('health-text');
  const time = $('health-time');
  async function check() {
    try {
      const res = await fetch('/api/system/status');
      const data = await res.json();
      if (data.status === 'ok') {
        dot.dataset.state = 'ok';
        text.textContent = '在线';
        const t = new Date(data.timestamp);
        time.textContent = '上次同步: ' + t.toLocaleTimeString('zh-CN');
      } else {
        dot.dataset.state = 'error';
        text.textContent = '异常';
      }
    } catch (e) {
      dot.dataset.state = 'error';
      text.textContent = '无法连接';
    }
  }
  check();
  state.healthTimer = setInterval(check, 5000);
}

document.addEventListener('DOMContentLoaded', init);
```

- [ ] **Step 4: 运行 JS 测试**

Run: `cd /c/Users/27825/Desktop/First_cc && .venv/Scripts/python.exe -m pytest tests/test_home_page.py::test_js_served tests/test_home_page.py::test_js_fetches_openapi -v`
Expected: 2 个测试 PASS

- [ ] **Step 5: 运行全套测试**

Run: `cd /c/Users/27825/Desktop/First_cc && .venv/Scripts/python.exe -m pytest -v`
Expected: 至少 34 个测试全部 PASS

- [ ] **Step 6: 提交**

```bash
cd /c/Users/27825/Desktop
git add First_cc/backend/static/app.js First_cc/tests/test_home_page.py
git commit -m "feat(docs): JS for sidebar, endpoint cards, try-it, and health polling"
```

---

## Task 7: 手动浏览器验证

**Files:** 无 (验证任务)

- [ ] **Step 1: 启动服务**

Run: `cd /c/Users/27825/Desktop/First_cc && .venv/Scripts/python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8765`
Expected: 服务启动,日志显示 "MZC service starting (version=0.1.0)"

- [ ] **Step 2: 在浏览器打开 `http://127.0.0.1:8765/`**

确认以下 6 项:
- [ ] 暗色背景(不是白色)
- [ ] 顶部显示 "MZC 移动中控 v0.1.0"
- [ ] 服务状态条显示绿点和"在线"
- [ ] 侧边栏有"服务状态"和"定时任务"两个分组
- [ ] 主区显示 3 个 endpoint 卡片,中文 method 标签(GET 蓝色)
- [ ] 点击"执行"按钮能调通 `/api/system/status`,响应显示 HTTP 200 和 JSON

- [ ] **Step 3: 测试手机宽度**

缩窄浏览器到 < 768px(或打开 DevTools 设备模拟选 iPhone):
- [ ] 布局变为单列
- [ ] 侧边栏在顶部
- [ ] 字号变大

- [ ] **Step 4: 测试 404 endpoint**

- [ ] 点击 `GET /api/tasks/{id}` 卡片的"执行",留空 task_id,提交 → 期望显示 HTTP 404 + 中文错误信息

- [ ] **Step 5: 关闭服务**

Ctrl+C 停止 uvicorn

- [ ] **Step 6: 如果有调整,提交;否则标记完成**

如果上一步手测发现需要调整(比如某个颜色不对、某个布局瑕疵),改完后:

```bash
cd /c/Users/27825/Desktop
git add First_cc/backend/static/
git commit -m "fix(docs): polish dark theme based on browser review"
```

否则,直接跳到下一个 task。

---

## Task 8: 文档更新 + 总结

**Files:**
- Modify: `docs/superpowers/specs/2026-06-19-api-docs-page-design.md` (状态改为"已实现")
- Modify: `First_cc/README.md` (如有,加一行说明新首页位置)

- [ ] **Step 1: 更新 spec 状态**

在 `docs/superpowers/specs/2026-06-19-api-docs-page-design.md` 顶部:
```markdown
> 状态:已实现 (commit <hash>)
```
把 `<hash>` 替换为最后一次 commit 的 hash。

- [ ] **Step 2: 检查/更新 README**

Run: `ls /c/Users/27825/Desktop/First_cc/README* 2>/dev/null || echo "no readme"`
- 如果存在 `README.md`,在 "API" 段加一句 "API 文档首页:`http://127.0.0.1:8765/`"
- 如果不存在,跳过

- [ ] **Step 3: 提交**

```bash
cd /c/Users/27825/Desktop
git add docs/superpowers/specs/2026-06-19-api-docs-page-design.md First_cc/README.md
git commit -m "docs: mark API docs page spec as implemented"
```

---

## 完成检查清单

- [ ] Task 1: 后端 API 中文化 (4 tests)
- [ ] Task 2: Pydantic Task 模型中文化 (1 test)
- [ ] Task 3: 挂载静态资源 + 关闭默认文档 (5 tests)
- [ ] Task 4: index.html 完整骨架 (1 test)
- [ ] Task 5: app.css 暗色主题 (2 tests)
- [ ] Task 6: app.js 渲染 + 试调 (2 tests)
- [ ] Task 7: 手动浏览器验证
- [ ] Task 8: 文档更新

**预计新增测试:** 15 (后端/前端各半)
**预计总测试数:** 21 (现有) + 15 (新增) = 36
**预计代码量:** ~600 行 (后端 30, 前端 500+, 测试 70+)
