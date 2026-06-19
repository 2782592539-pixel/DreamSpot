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
                      created_by, tags, next_run_at, synced_at
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
    if isinstance(d.get("tags"), str):
        try:
            d["tags"] = json.loads(d["tags"])
        except json.JSONDecodeError:
            d["tags"] = []
    return d
