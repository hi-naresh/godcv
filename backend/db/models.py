from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class ProfileCreate(BaseModel):
    name: str
    master_resume: str
    gemini_api_key: str = ""
    page_mode: str = "single"
    stealth_mode: bool = False
    max_projects: int = 4
    max_bullets_per_entry: int = 3
    require_quantified_bullets: bool = True


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    master_resume: str | None = None
    gemini_api_key: str | None = None
    page_mode: str | None = None
    stealth_mode: bool | None = None
    max_projects: int | None = None
    max_bullets_per_entry: int | None = None
    require_quantified_bullets: bool | None = None


class ProfileResponse(BaseModel):
    id: int
    name: str
    master_resume: str
    gemini_api_key: str
    page_mode: str
    stealth_mode: bool
    max_projects: int
    max_bullets_per_entry: int
    require_quantified_bullets: bool
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
    model_config = ConfigDict(extra="forbid")

    job_description: str
    resume_override: str | None = None
    gemini_api_key: str | None = None
    role_level: str | None = None
    page_mode: str = "single"
    analyze_only: bool = False
    stealth_mode: bool | None = None
    max_projects: int | None = None
    max_bullets_per_entry: int | None = None
    require_quantified_bullets: bool | None = None


class ExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_description: str
    resume_override: str | None = None
    gemini_api_key: str | None = None
    role_level: str | None = None
    plan: dict
    stealth_mode: bool | None = None
    max_projects: int | None = None
    max_bullets_per_entry: int | None = None
    require_quantified_bullets: bool | None = None


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
    html: str
    font_size: float = 11.0
    line_spacing: float = 1.4
    page_mode: str = "single"
    filename: str = "resume.pdf"
    document_title: str | None = None
    document_lang: str = "en"


class RetryBudgetUpdateRequest(BaseModel):
    job_class: str
    max_retries: int = 5
    base_delay_seconds: int = 30
    max_delay_seconds: int = 1800
    backoff_multiplier: float = 2.0


class EnqueueJobRequest(BaseModel):
    job_class: str
    idempotency_key: str
    payload: dict = Field(default_factory=dict)


class JobSuccessRequest(BaseModel):
    result: dict | None = None


class JobFailureRequest(BaseModel):
    error_message: str
