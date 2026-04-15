from fastapi import APIRouter, HTTPException
from backend.db.models import ProfileCreate, ProfileUpdate
from backend.services import profile as profile_service

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("")
async def get_profile():
    p = await profile_service.get_profile()
    if not p:
        raise HTTPException(status_code=404, detail="No profile found. Create one first.")
    return p


@router.post("")
async def create_profile(data: ProfileCreate):
    p = await profile_service.create_profile(
        name=data.name,
        master_resume=data.master_resume,
        gemini_api_key=data.gemini_api_key,
        page_mode=data.page_mode,
    )
    return p


@router.put("")
async def update_profile(data: ProfileUpdate):
    p = await profile_service.get_profile()
    if not p:
        raise HTTPException(status_code=404, detail="No profile found.")
    updated = await profile_service.update_profile(p["id"], **data.model_dump(exclude_none=True))
    return updated


@router.get("/insights")
async def get_insights():
    p = await profile_service.get_profile()
    if not p:
        return []
    return await profile_service.get_role_insights(p["id"])


@router.delete("/insights/{insight_id}")
async def delete_insight(insight_id: int):
    await profile_service.delete_role_insight(insight_id)
    return {"ok": True}
