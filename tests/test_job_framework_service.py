from datetime import datetime, timezone

import pytest
import pytest_asyncio

from backend.db import database
from backend.services import job_framework


@pytest_asyncio.fixture(autouse=True)
async def isolated_db(tmp_path, monkeypatch):
    db_file = tmp_path / "jobs.db"
    monkeypatch.setattr(database, "DB_PATH", str(db_file))
    monkeypatch.setattr(database, "_db", None)
    yield
    if database._db is not None:
        await database._db.close()
        database._db = None


def _parse_sql_ts(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_enqueue_is_idempotent_for_same_key():
    first, created_first = await job_framework.enqueue_job(
        job_class="TailorResumeJob",
        payload={"profile_id": 1},
        idempotency_key="resume-1-jd-1",
    )
    second, created_second = await job_framework.enqueue_job(
        job_class="TailorResumeJob",
        payload={"profile_id": 1},
        idempotency_key="resume-1-jd-1",
    )

    assert created_first is True
    assert created_second is False
    assert first["id"] == second["id"]


@pytest.mark.asyncio
async def test_exponential_backoff_and_quarantine_after_budget_exhausted():
    await job_framework.set_retry_budget(
        job_class="TailorResumeJob",
        max_retries=2,
        base_delay_seconds=10,
        max_delay_seconds=60,
        backoff_multiplier=2.0,
    )
    job, _ = await job_framework.enqueue_job(
        job_class="TailorResumeJob",
        payload={"profile_id": 1},
        idempotency_key="resume-2-jd-2",
    )
    claimed = await job_framework.claim_due_job("TailorResumeJob")
    assert claimed is not None
    assert claimed["id"] == job["id"]
    assert claimed["status"] == "running"

    failed_once = await job_framework.mark_job_failure(job["id"], "timeout")
    assert failed_once["status"] == "queued"
    assert failed_once["attempt_count"] == 1
    first_delay = (_parse_sql_ts(failed_once["run_at"]) - datetime.now(timezone.utc)).total_seconds()
    assert 0 < first_delay <= 12

    db = await database.get_db()
    await db.execute("UPDATE job_queue SET run_at = CURRENT_TIMESTAMP WHERE id = ?", (job["id"],))
    await db.commit()
    await job_framework.claim_due_job("TailorResumeJob")
    failed_twice = await job_framework.mark_job_failure(job["id"], "timeout again")
    assert failed_twice["status"] == "queued"
    assert failed_twice["attempt_count"] == 2
    second_delay = (_parse_sql_ts(failed_twice["run_at"]) - datetime.now(timezone.utc)).total_seconds()
    assert 8 <= second_delay <= 22

    await db.execute("UPDATE job_queue SET run_at = CURRENT_TIMESTAMP WHERE id = ?", (job["id"],))
    await db.commit()
    await job_framework.claim_due_job("TailorResumeJob")
    quarantined = await job_framework.mark_job_failure(job["id"], "still failing")
    assert quarantined["status"] == "quarantined"
    assert quarantined["attempt_count"] == 3
    assert "Retry budget exhausted" in quarantined["quarantine_reason"]

    failures = await job_framework.get_failure_events(job["id"])
    assert len(failures) == 3
