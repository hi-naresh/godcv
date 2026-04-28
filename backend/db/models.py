from pydantic import BaseModel
from datetime import datetime


class ProfileCreate(BaseModel):
    name: str
    master_resume: str
    gemini_api_key: str = ""
    page_mode: str = "single"
    fabrication_mode: bool = False


class ProfileUpdate(BaseModel):
    name: str | None = None
    master_resume: str | None = None
    gemini_api_key: str | None = None
    page_mode: str | None = None
    fabrication_mode: bool | None = None


class ProfileResponse(BaseModel):
    id: int
    name: str
    master_resume: str
    gemini_api_key: str
    page_mode: str
    fabrication_mode: bool
    created_at: str
    updated_at: str


class RoleInsightResponse(BaseModel):
    id: int
    profile_id: int
    role_type: str
    strongest_points: list[str]
    preferred_skill_order: list[str]
    frequently_modified_sections: list[str]
    tailoring_count: int


class TailorRequest(BaseModel):
    job_description: str
    resume_override: str | None = None
    gemini_api_key: str | None = None
    seniority_level: str | None = None
    page_mode: str = "single"
    analyze_only: bool = False


class ExecuteRequest(BaseModel):
    job_description: str
    resume_override: str | None = None
    gemini_api_key: str | None = None
    seniority_level: str | None = None
    plan: dict


class TailoringHistoryResponse(BaseModel):
    id: int
    profile_id: int
    job_title: str | None
    company: str | None
    job_description: str
    original_resume: str
    tailored_resume: str
    orchestrator_plan: str | None
    role_type: str | None
    sections_modified: list[str]
    created_at: str


class SavedCVCreate(BaseModel):
    name: str
    markdown: str
    job_title: str | None = None
    company: str | None = None


class SavedCVResponse(BaseModel):
    id: int
    profile_id: int
    name: str
    markdown: str
    job_title: str | None
    company: str | None
    created_at: str


class ExportRequest(BaseModel):
    markdown: str
