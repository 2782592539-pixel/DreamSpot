"""Tests for history_store - SQLite runs CRUD."""
import pytest
from datetime import datetime
from backend.db.init_db import init_db
from backend.services.history_store import HistoryStore, RunRecord


@pytest.fixture
def store(temp_data_dir):
    init_db()
    return HistoryStore()


def test_insert_and_get_run(store):
    record = RunRecord(
        task_id="t_1",
        started_at=datetime(2026, 6, 19, 9, 0),
        finished_at=datetime(2026, 6, 19, 9, 5),
        status="success",
        exit_code=0,
        output="all good",
        output_summary="all good",
        duration_sec=300,
        trigger_source="cron",
    )
    run_id = store.insert(record)
    assert run_id > 0

    fetched = store.get(run_id)
    assert fetched is not None
    assert fetched.task_id == "t_1"
    assert fetched.status == "success"
    assert fetched.duration_sec == 300


def test_list_runs_by_task(store):
    for i in range(3):
        store.insert(RunRecord(
            task_id="t_a",
            started_at=datetime(2026, 6, 19, 9, i),
            status="success",
            trigger_source="cron",
        ))
    store.insert(RunRecord(
        task_id="t_b",
        started_at=datetime(2026, 6, 19, 10, 0),
        status="failed",
        trigger_source="manual_web",
    ))

    runs_a = store.list_by_task("t_a")
    assert len(runs_a) == 3

    runs_b = store.list_by_task("t_b")
    assert len(runs_b) == 1
    assert runs_b[0].status == "failed"


def test_set_feishu_msg_id(store):
    rec = RunRecord(
        task_id="t_1",
        started_at=datetime.now(),
        status="success",
        trigger_source="cron",
    )
    run_id = store.insert(rec)
    store.set_feishu_msg_id(run_id, "om_xyz123")

    fetched = store.get(run_id)
    assert fetched.feishu_msg_id == "om_xyz123"
