import json
from datetime import datetime, timedelta, timezone

import aiosqlite

from backend.db.database import get_db

DEFAULT_RETRY_BUDGET = {
    "max_retries": 5,
    "base_delay_seconds": 30,
    "max_delay_seconds": 1800,
    "backoff_multiplier": 2.0,
}


def _coerce_job(row) -> dict:
    data = dict(row)
    data["payload"] = json.loads(data["payload"]) if data.get("payload") else {}
    data["result"] = json.loads(data["result"]) if data.get("result") else None
    return data


async def set_retry_budget(
    job_class: str,
    max_retries: int,
    base_delay_seconds: int,
    max_delay_seconds: int,
    backoff_multiplier: float = 2.0,
) -> dict:
    db = await get_db()
    await db.execute(
        """
        INSERT INTO job_retry_budgets
            (job_class, max_retries, base_delay_seconds, max_delay_seconds, backoff_multiplier, updated_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(job_class) DO UPDATE SET
            max_retries = excluded.max_retries,
            base_delay_seconds = excluded.base_delay_seconds,
            max_delay_seconds = excluded.max_delay_seconds,
            backoff_multiplier = excluded.backoff_multiplier,
            updated_at = CURRENT_TIMESTAMP
        """,
        (job_class, max_retries, base_delay_seconds, max_delay_seconds, backoff_multiplier),
    )
    await db.commit()
    return await get_retry_budget(job_class)


async def get_retry_budget(job_class: str) -> dict:
    db = await get_db()
    cursor = await db.execute(
        """
        SELECT job_class, max_retries, base_delay_seconds, max_delay_seconds, backoff_multiplier
        FROM job_retry_budgets
        WHERE job_class = ?
        """,
        (job_class,),
    )
    row = await cursor.fetchone()
    if row:
        return dict(row)
    return {"job_class": job_class, **DEFAULT_RETRY_BUDGET}


async def enqueue_job(job_class: str, payload: dict, idempotency_key: str) -> tuple[dict, bool]:
    db = await get_db()
    payload_json = json.dumps(payload or {})
    try:
        cursor = await db.execute(
            """
            INSERT INTO job_queue (job_class, payload, idempotency_key)
            VALUES (?, ?, ?)
            """,
            (job_class, payload_json, idempotency_key),
        )
        await db.commit()
        created = await get_job(cursor.lastrowid)
        return created, True
    except aiosqlite.IntegrityError:
        cursor = await db.execute(
            "SELECT * FROM job_queue WHERE idempotency_key = ?",
            (idempotency_key,),
        )
        row = await cursor.fetchone()
        if not row:
            raise
        return _coerce_job(row), False


async def get_job(job_id: int) -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM job_queue WHERE id = ?", (job_id,))
    row = await cursor.fetchone()
    if not row:
        return None
    return _coerce_job(row)


async def list_jobs(status: str | None = None, job_class: str | None = None, limit: int = 50) -> list[dict]:
    db = await get_db()
    clauses = []
    values = []
    if status:
        clauses.append("status = ?")
        values.append(status)
    if job_class:
        clauses.append("job_class = ?")
        values.append(job_class)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    cursor = await db.execute(
        f"""
        SELECT * FROM job_queue
        {where}
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (*values, limit),
    )
    rows = await cursor.fetchall()
    return [_coerce_job(row) for row in rows]


async def list_quarantine(limit: int = 50) -> list[dict]:
    return await list_jobs(status="quarantined", limit=limit)


async def claim_due_job(job_class: str | None = None) -> dict | None:
    db = await get_db()
    await db.execute("BEGIN IMMEDIATE")
    try:
        clause = ""
        values: list[str] = []
        if job_class:
            clause = "AND job_class = ?"
            values.append(job_class)
        cursor = await db.execute(
            f"""
            SELECT id FROM job_queue
            WHERE status = 'queued'
              AND run_at <= CURRENT_TIMESTAMP
              {clause}
            ORDER BY run_at ASC, id ASC
            LIMIT 1
            """,
            values,
        )
        row = await cursor.fetchone()
        if not row:
            await db.commit()
            return None

        job_id = row["id"]
        await db.execute(
            """
            UPDATE job_queue
            SET status = 'running', started_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status = 'queued'
            """,
            (job_id,),
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return await get_job(job_id)


async def mark_job_success(job_id: int, result: dict | None = None) -> dict | None:
    db = await get_db()
    await db.execute(
        """
        UPDATE job_queue
        SET status = 'succeeded',
            result = ?,
            updated_at = CURRENT_TIMESTAMP,
            finished_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (json.dumps(result) if result is not None else None, job_id),
    )
    await db.commit()
    return await get_job(job_id)


async def mark_job_failure(job_id: int, error_message: str) -> dict | None:
    db = await get_db()
    existing = await get_job(job_id)
    if not existing:
        return None

    attempt_number = int(existing.get("attempt_count", 0)) + 1
    await db.execute(
        """
        INSERT INTO job_failure_events (job_id, attempt_number, error_message)
        VALUES (?, ?, ?)
        """,
        (job_id, attempt_number, error_message),
    )

    budget = await get_retry_budget(existing["job_class"])
    max_retries = int(budget["max_retries"])
    if attempt_number > max_retries:
        await db.execute(
            """
            UPDATE job_queue
            SET status = 'quarantined',
                attempt_count = ?,
                last_error = ?,
                quarantine_reason = ?,
                updated_at = CURRENT_TIMESTAMP,
                finished_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                attempt_number,
                error_message,
                f"Retry budget exhausted for {existing['job_class']} after {max_retries} retries.",
                job_id,
            ),
        )
        await db.commit()
        return await get_job(job_id)

    multiplier = float(budget["backoff_multiplier"])
    base_delay = int(budget["base_delay_seconds"])
    max_delay = int(budget["max_delay_seconds"])
    delay_seconds = min(int(base_delay * (multiplier ** (attempt_number - 1))), max_delay)
    next_run_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
    next_run_at_sql = next_run_at.strftime("%Y-%m-%d %H:%M:%S")

    await db.execute(
        """
        UPDATE job_queue
        SET status = 'queued',
            attempt_count = ?,
            run_at = ?,
            last_error = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (attempt_number, next_run_at_sql, error_message, job_id),
    )
    await db.commit()
    return await get_job(job_id)


async def get_failure_events(job_id: int, limit: int = 50) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        """
        SELECT id, job_id, attempt_number, error_message, created_at
        FROM job_failure_events
        WHERE job_id = ?
        ORDER BY attempt_number DESC
        LIMIT ?
        """,
        (job_id, limit),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]
