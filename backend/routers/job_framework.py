from fastapi import APIRouter, HTTPException

from backend.db.models import (
    EnqueueJobRequest,
    JobFailureRequest,
    JobSuccessRequest,
    RetryBudgetUpdateRequest,
)
from backend.services import job_framework as jobs

router = APIRouter(prefix="/api/job-framework", tags=["job-framework"])


@router.post("/retry-budgets")
async def upsert_retry_budget(request: RetryBudgetUpdateRequest):
    return await jobs.set_retry_budget(
        job_class=request.job_class,
        max_retries=request.max_retries,
        base_delay_seconds=request.base_delay_seconds,
        max_delay_seconds=request.max_delay_seconds,
        backoff_multiplier=request.backoff_multiplier,
    )


@router.get("/retry-budgets/{job_class}")
async def get_retry_budget(job_class: str):
    return await jobs.get_retry_budget(job_class)


@router.post("/jobs")
async def enqueue_job(request: EnqueueJobRequest):
    job, created = await jobs.enqueue_job(
        job_class=request.job_class,
        payload=request.payload,
        idempotency_key=request.idempotency_key,
    )
    return {"created": created, "job": job}


@router.get("/jobs")
async def list_jobs(status: str | None = None, job_class: str | None = None, limit: int = 50):
    return await jobs.list_jobs(status=status, job_class=job_class, limit=limit)


@router.post("/jobs/claim")
async def claim_job(job_class: str | None = None):
    job = await jobs.claim_due_job(job_class=job_class)
    if not job:
        return {"job": None}
    return {"job": job}


@router.get("/jobs/{job_id}")
async def get_job(job_id: int):
    job = await jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.post("/jobs/{job_id}/success")
async def mark_job_success(job_id: int, request: JobSuccessRequest):
    job = await jobs.mark_job_success(job_id=job_id, result=request.result)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.post("/jobs/{job_id}/failure")
async def mark_job_failure(job_id: int, request: JobFailureRequest):
    job = await jobs.mark_job_failure(job_id=job_id, error_message=request.error_message)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.get("/jobs/{job_id}/failures")
async def list_failure_events(job_id: int, limit: int = 50):
    return await jobs.get_failure_events(job_id=job_id, limit=limit)


@router.get("/quarantine")
async def list_quarantined_jobs(limit: int = 50):
    return await jobs.list_quarantine(limit=limit)
