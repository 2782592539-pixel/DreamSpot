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
    now = datetime.now().isoformat()

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

        for existing_id in existing_map:
            if existing_id not in json_ids:
                conn.execute("DELETE FROM tasks WHERE id = ?", (existing_id,))
                logger.info(f"Removed task {existing_id} (no longer in JSON)")

    logger.info(f"Synced {len(tasks)} tasks from JSON to SQLite")
    return len(tasks)
