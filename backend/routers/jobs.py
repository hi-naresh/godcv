from fastapi import APIRouter, HTTPException
from backend.services import profile as profile_service

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("")
async def list_jobs(limit: int = 20):
    profile = await profile_service.get_profile()
    if not profile:
        return []
    return await profile_service.get_tailoring_history(profile["id"], limit)


@router.get("/{job_id}")
async def get_job(job_id: int):
    job = await profile_service.get_tailoring_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Tailoring not found.")
    return job


@router.delete("/{job_id}")
async def delete_job(job_id: int):
    await profile_service.delete_tailoring(job_id)
    return {"ok": True}
