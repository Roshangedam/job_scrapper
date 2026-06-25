"""Pydantic schemas for candidate profile and match report."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CandidateProfileResponse(BaseModel):
    id: str
    engine_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    total_experience_years: Optional[float] = None
    profile_json: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MatchReportResponse(BaseModel):
    id: str
    job_id: str
    candidate_id: str
    overall_match_pct: float
    skill_match_pct: float
    experience_match_pct: float
    education_match_pct: float
    location_match_pct: float
    selection_probability: float
    recommendation: Optional[str] = None
    ai_summary: Optional[str] = None
    report_json: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
