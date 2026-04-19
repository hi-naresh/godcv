from fastapi import APIRouter, HTTPException
from backend.db.models import SavedCVCreate
from backend.services import profile as profile_service
from backend.services import saved_cvs as cv_service

router = APIRouter(prefix="/api/saved-cvs", tags=["saved-cvs"])


@router.get("")
async def list_cvs(limit: int = 50):
    p = await profile_service.get_profile()
    if not p:
        return []
    return await cv_service.list_saved_cvs(p["id"], limit)


@router.get("/{cv_id}")
async def get_cv(cv_id: int):
    cv = await cv_service.get_saved_cv(cv_id)
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found.")
    return cv


@router.post("")
async def save_cv(data: SavedCVCreate):
    p = await profile_service.get_profile()
    if not p:
        raise HTTPException(status_code=400, detail="No profile found. Create one first.")
    return await cv_service.save_cv(p["id"], data.name, data.markdown, data.job_title, data.company)


@router.delete("/{cv_id}")
async def delete_cv(cv_id: int):
    await cv_service.delete_saved_cv(cv_id)
    return {"ok": True}
