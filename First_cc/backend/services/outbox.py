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
        now = datetime.now().isoformat()
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
        now = datetime.now().isoformat()
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
        now = datetime.now().isoformat()
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
                datetime.now() + timedelta(seconds=backoff)
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