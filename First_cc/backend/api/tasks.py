"""定时任务相关接口。"""
import json
import logging
from fastapi import APIRouter, HTTPException

from backend.db.connection import get_connection
from backend.models.task import Task
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
