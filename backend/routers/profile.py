from pathlib import Path
from fastapi import APIRouter, HTTPException
from backend.db.models import ProfileCreate, ProfileUpdate
from backend.services import profile as profile_service
from backend.config import BASE_DIR

router = APIRouter(prefix="/api/profile", tags=["profile"])

SAMPLE_RESUME_PATH = BASE_DIR / "data" / "sample_resume.md"


async def _seed_from_sample() -> dict | None:
    """Auto-create a profile from sample_resume.md on first run."""
    if not SAMPLE_RESUME_PATH.exists():
        return None
    md = SAMPLE_RESUME_PATH.read_text(encoding="utf-8")
    # Extract name from frontmatter
    name = "New User"
    for line in md.split("\n"):
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip()
            break
    return await profile_service.create_profile(
        name=name,
        master_resume=md,
        gemini_api_key="",
        page_mode="single",
    )


@router.get("")
async def get_profile():
    p = await profile_service.get_profile()
    if not p:
        p = await _seed_from_sample()
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
