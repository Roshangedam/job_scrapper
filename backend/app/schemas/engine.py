"""Pydantic schemas for Engine API requests/responses."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SearchPreferenceCreate(BaseModel):
    pref_type: str = Field(..., description="keyword, company, or location")
    pref_value: str


class EnginePlatformCreate(BaseModel):
    platform_id: str
    is_enabled: bool = True
    email_alerts_enabled: bool = True


class EngineCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: str = Field(..., max_length=255)
    refresh_interval_minutes: int = Field(60, ge=5, le=1440)
    platform_ids: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    companies: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    experience_min: Optional[float] = None
    experience_max: Optional[float] = None


class EngineUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    refresh_interval_minutes: Optional[int] = None
    is_active: Optional[bool] = None
    platform_ids: Optional[list[str]] = None
    keywords: Optional[list[str]] = None
    companies: Optional[list[str]] = None
    locations: Optional[list[str]] = None
    experience_min: Optional[float] = None
    experience_max: Optional[float] = None


class SearchPreferenceResponse(BaseModel):
    id: str
    pref_type: str
    pref_value: str

    model_config = {"from_attributes": True}


class EnginePlatformResponse(BaseModel):
    id: str
    platform_id: str
    platform_name: Optional[str] = None
    platform_display_name: Optional[str] = None
    platform_logo: Optional[str] = None
    is_enabled: bool
    email_alerts_enabled: bool

    model_config = {"from_attributes": True}


class EngineResponse(BaseModel):
    id: str
    name: str
    email: str
    status: str
    refresh_interval_minutes: int
    is_active: bool
    last_run_at: Optional[datetime] = None
    total_jobs_found: int
    resume_path: Optional[str] = None
    has_resume: bool = False
    has_profile: bool = False
    created_at: datetime
    updated_at: datetime
    platforms: list[EnginePlatformResponse] = []
    search_preferences: list[SearchPreferenceResponse] = []

    model_config = {"from_attributes": True}


class EngineListResponse(BaseModel):
    engines: list[EngineResponse]
    total: int
