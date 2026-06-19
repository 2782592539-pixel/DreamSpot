"""Tick handler: executes a task via ClaudeRunner, records the run, updates last_run.

Strategy P1 (anti-dual-trigger): if a task was last_run within ~80% of the
cron interval, assume Claude Code already triggered it and skip.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

import httpx
from croniter import croniter

from backend.services.claude_runner import ClaudeRunner
from backend.services.feishu_client import FeishuClient
from backend.services.history_store import HistoryStore, RunRecord
from backend.services.outbox import Outbox, OutboxItem
from backend.services.task_store import TaskStore

logger = logging.getLogger(__name__)

ANTI_DUAL_THRESHOLD = 0.8


class TaskExecutor:
    """Called by the scheduler when a task fires."""

    def tick(self, task_id: str, prompt: str) -> None:
        if not self._should_fire(task_id):
            logger.info(f"Skipping {task_id} (strategy P1: too soon after last_run)")
            return

        # Ensure task exists in DB (for FK constraint on runs.task_id)
        from backend.services.sync import sync_tasks_from_json
        from backend.db.connection import get_connection
        sync_tasks_from_json()
        with get_connection() as conn:
            exists = conn.execute(
                "SELECT 1 FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
        if not exists:
            logger.warning(f"Task {task_id} not found in DB; skipping tick")
            return

        record = RunRecord(
            task_id=task_id,
            started_at=datetime.now(),
            status="running",
            trigger_source="cron",
        )
        run_id = HistoryStore().insert(record)
        record.id = run_id

        runner = ClaudeRunner()
        try:
            result = runner.run(prompt=prompt)
        except TimeoutError as e:
            record.finished_at = datetime.now()
            record.status = "timeout"
            record.output_summary = f"Timeout: {e}"
            record.duration_sec = int((record.finished_at - record.started_at).total_seconds())
            HistoryStore().update(record)
            TaskStore().update_last_run(task_id, record.finished_at, record.status)
            logger.info(f"Task {task_id} timed out after {record.duration_sec}s")
            return

        record.finished_at = result.finished_at
        record.status = "success" if result.exit_code == 0 else "failed"
        record.exit_code = result.exit_code
        record.output = self._truncate(result.output, 1_000_000)
        record.output_summary = result.output[:500] if result.output else None
        record.duration_sec = result.duration_sec
        HistoryStore().update(record)

        TaskStore().update_last_run(task_id, result.finished_at, record.status)

        logger.info(
            f"Task {task_id} finished: {record.status} "
            f"(exit={result.exit_code}, dur={result.duration_sec}s)"
        )

        # Push Feishu notification
        self._push_feishu(task_id, record)

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
            # task.last_run is a datetime (Pydantic v2 parses ISO 8601)
            last_run_naive = task.last_run.replace(tzinfo=None) if task.last_run.tzinfo else task.last_run
            elapsed = datetime.now() - last_run_naive
            threshold = interval * ANTI_DUAL_THRESHOLD
            return elapsed > threshold
        except Exception:
            logger.exception(f"_should_fire error for {task_id}; defaulting to fire")
            return True

    @staticmethod
    def _estimate_interval(schedule: str) -> Optional[timedelta]:
        try:
            iter_obj = croniter(schedule, datetime.now())
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

    def _push_feishu(self, task_id: str, record: RunRecord) -> None:
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
                run_id=record.id or 0,
            )
            payload_dict = card.to_dict()
            webhook = client.webhook_url
            try:
                resp = httpx.post(webhook, json=payload_dict, timeout=10)
                if resp.status_code == 200 and resp.json().get("code") == 0:
                    HistoryStore().set_feishu_msg_id(record.id, str(record.id))
                    return
            except Exception as e:
                logger.warning(f"Feishu send failed; enqueueing: {e}")

            # Fallback: enqueue for retry
            Outbox().enqueue(OutboxItem(
                target_url=webhook,
                payload=json.dumps(payload_dict, ensure_ascii=False),
            ))
        except Exception:
            logger.exception("Feishu push failed entirely")
