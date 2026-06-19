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
