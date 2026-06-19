"""定时任务相关接口。"""
import json
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException

from backend.db.connection import get_connection
from backend.models.task import Task
from backend.services.claude_runner import ClaudeRunner
from backend.services.history_store import HistoryStore, RunRecord
from backend.services.sync import sync_tasks_from_json
from backend.services.task_store import TaskStore

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/tasks",
    tags=["定时任务"],
)


@router.get("", summary="列出所有任务", response_model=list[Task], description="从 Claude Code 的 scheduled_tasks.json 同步后,返回全部定时任务。")
def list_tasks() -> list[Task]:
    """List all tasks, synced from JSON on each call (cheap)."""
    sync_tasks_from_json()
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT id, name, prompt, schedule, enabled, created_at,
                      created_by, tags, next_run_at, synced_at
               FROM tasks ORDER BY name"""
        ).fetchall()
    return [Task(**_row_to_dict(r)) for r in rows]


@router.get("/{task_id}", summary="查看单个任务", response_model=Task, description="按 ID 查询单个任务的详细信息。")
def get_task(task_id: str) -> Task:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    return Task(**_row_to_dict(row))


def _row_to_dict(row) -> dict:
    d = dict(row)
    if isinstance(d.get("tags"), str):
        try:
            d["tags"] = json.loads(d["tags"])
        except json.JSONDecodeError:
            d["tags"] = []
    return d


@router.post("/{task_id}/run", summary="手动触发任务", description="立即执行指定任务,记录运行历史。")
def run_task(task_id: str) -> dict:
    """Manually trigger a task and record the run."""
    sync_tasks_from_json()

    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, prompt, name FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    # Record as running
    record = RunRecord(
        task_id=task_id,
        started_at=datetime.now(),
        status="running",
        trigger_source="manual_web",
    )
    run_id = HistoryStore().insert(record)
    record.id = run_id

    # Execute
    runner = ClaudeRunner()
    try:
        result = runner.run(prompt=row["prompt"])
    except TimeoutError as e:
        # Timeout: record the failure with status='timeout'
        record.finished_at = datetime.now()
        record.status = "timeout"
        record.error = str(e)
        record.duration_sec = int((record.finished_at - record.started_at).total_seconds())
        HistoryStore().update(record)
        # Update last_run in JSON
        TaskStore().update_last_run(task_id, record.finished_at, record.status)
        return {
            "id": run_id,
            "task_id": task_id,
            "status": record.status,
            "exit_code": None,
            "duration_sec": record.duration_sec,
            "trigger_source": "manual_web",
            "started_at": record.started_at.isoformat(),
            "finished_at": record.finished_at.isoformat(),
        }

    # Success or non-timeout failure
    record.finished_at = result.finished_at
    record.status = "success" if result.exit_code == 0 else "failed"
    record.exit_code = result.exit_code
    record.output = _truncate_output(result.output, max_bytes=1_000_000)
    record.output_summary = result.output[:500] if result.output else None
    record.duration_sec = result.duration_sec
    HistoryStore().update(record)

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
