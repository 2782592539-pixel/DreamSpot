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
