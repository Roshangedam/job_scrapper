"""Pydantic schemas for Job API requests/responses."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class JobResponse(BaseModel):
    id: str
    engine_id: str
    source_platform: str
    source_url: Optional[str] = None
    title: str
    company_name: Optional[str] = None
    company_logo_url: Optional[str] = None
    company_rating: Optional[float] = None
    location_city: Optional[str] = None
    location_state: Optional[str] = None
    remote_type: Optional[str] = None
    description_clean: Optional[str] = None
    required_skills: Optional[str] = None  # JSON string
    preferred_skills: Optional[str] = None
    experience_min_years: Optional[float] = None
    experience_max_years: Optional[float] = None
    education: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: str = "INR"
    posted_date: Optional[str] = None
    applicants_count: Optional[int] = None
    employment_type: Optional[str] = None
    seniority_level: Optional[str] = None
    hr_name: Optional[str] = None
    hr_email: Optional[str] = None
    is_duplicate: bool = False
    scraped_at: datetime

    # Match data (joined)
    match_pct: Optional[float] = None
    skill_match_pct: Optional[float] = None
    experience_match_pct: Optional[float] = None
    recommendation: Optional[str] = None
    ai_summary: Optional[str] = None

    model_config = {"from_attributes": True}


class JobDetailResponse(JobResponse):
    """Extended response with full details."""
    description_raw: Optional[str] = None
    job_json: Optional[str] = None
    match_report_json: Optional[str] = None


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int
    page: int
    page_size: int


class JobFilterParams(BaseModel):
    engine_id: Optional[str] = None
    platform: Optional[str] = None
    search: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    min_match_pct: Optional[float] = None
    max_match_pct: Optional[float] = None
    min_experience: Optional[float] = None
    max_experience: Optional[float] = None
    employment_type: Optional[str] = None
    hide_duplicates: bool = True
    sort_by: str = "scraped_at"
    sort_order: str = "desc"
    page: int = 1
    page_size: int = 20
