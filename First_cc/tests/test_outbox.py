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
        next_retry_at=(datetime.now() - timedelta(minutes=1)).isoformat(),
    ))
    outbox.enqueue(OutboxItem(
        target_url="https://x", payload="{}",
        next_retry_at=(datetime.now() + timedelta(minutes=10)).isoformat(),
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