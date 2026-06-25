"""Jobs API routes — list, filter, search scraped jobs."""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, desc, asc
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.job import Job, JobMatchReport
from app.schemas.job import JobResponse, JobDetailResponse, JobListResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=JobListResponse)
async def list_jobs(
    engine_id: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    min_match_pct: Optional[float] = Query(None, ge=0, le=100),
    max_match_pct: Optional[float] = Query(None, ge=0, le=100),
    min_experience: Optional[float] = Query(None),
    max_experience: Optional[float] = Query(None),
    employment_type: Optional[str] = Query(None),
    hide_duplicates: bool = Query(True),
    sort_by: str = Query("scraped_at"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List jobs with filtering, sorting, and pagination."""
    query = select(Job).options(selectinload(Job.match_report))

    # Filters
    conditions = []
    if engine_id:
        conditions.append(Job.engine_id == engine_id)
    if platform:
        conditions.append(Job.source_platform == platform)
    if company:
        conditions.append(Job.company_name.ilike(f"%{company}%"))
    if location:
        conditions.append(
            or_(
                Job.location_city.ilike(f"%{location}%"),
                Job.location_state.ilike(f"%{location}%"),
            )
        )
    if search:
        conditions.append(
            or_(
                Job.title.ilike(f"%{search}%"),
                Job.company_name.ilike(f"%{search}%"),
                Job.description_clean.ilike(f"%{search}%"),
            )
        )
    if employment_type:
        conditions.append(Job.employment_type == employment_type)
    if min_experience is not None:
        conditions.append(Job.experience_min_years >= min_experience)
    if max_experience is not None:
        conditions.append(Job.experience_max_years <= max_experience)
    if hide_duplicates:
        conditions.append(Job.is_duplicate == False)

    if conditions:
        query = query.where(and_(*conditions))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Sorting
    sort_col = getattr(Job, sort_by, Job.scraped_at)
    if sort_order == "desc":
        query = query.order_by(desc(sort_col))
    else:
        query = query.order_by(asc(sort_col))

    # Pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    jobs = result.scalars().all()

    # Build response with match data
    job_responses = []
    for job in jobs:
        resp = _job_to_response(job)
        job_responses.append(resp)

    # Filter by match_pct (done after loading since it's in a related table)
    if min_match_pct is not None:
        job_responses = [j for j in job_responses if j.match_pct and j.match_pct >= min_match_pct]
    if max_match_pct is not None:
        job_responses = [j for j in job_responses if j.match_pct and j.match_pct <= max_match_pct]

    return JobListResponse(
        jobs=job_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job_detail(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get detailed job information with full description and match report."""
    result = await db.execute(
        select(Job)
        .where(Job.id == job_id)
        .options(selectinload(Job.match_report))
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    resp = JobDetailResponse(
        **_job_to_response(job).model_dump(),
        description_raw=job.description_raw,
        job_json=job.job_json,
        match_report_json=job.match_report.report_json if job.match_report else None,
    )
    return resp


@router.delete("/{job_id}")
async def delete_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a specific job."""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    await db.delete(job)
    await db.commit()
    return {"message": "Job deleted"}


def _job_to_response(job: Job) -> JobResponse:
    """Convert Job ORM to response with match data."""
    match = job.match_report

    return JobResponse(
        id=job.id,
        engine_id=job.engine_id,
        source_platform=job.source_platform,
        source_url=job.source_url,
        title=job.title,
        company_name=job.company_name,
        company_logo_url=job.company_logo_url,
        company_rating=job.company_rating,
        location_city=job.location_city,
        location_state=job.location_state,
        remote_type=job.remote_type,
        description_clean=job.description_clean,
        required_skills=job.required_skills,
        preferred_skills=job.preferred_skills,
        experience_min_years=job.experience_min_years,
        experience_max_years=job.experience_max_years,
        education=job.education,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        salary_currency=job.salary_currency,
        posted_date=job.posted_date,
        applicants_count=job.applicants_count,
        employment_type=job.employment_type,
        seniority_level=job.seniority_level,
        hr_name=job.hr_name,
        hr_email=job.hr_email,
        is_duplicate=job.is_duplicate,
        scraped_at=job.scraped_at,
        match_pct=match.overall_match_pct if match else None,
        skill_match_pct=match.skill_match_pct if match else None,
        experience_match_pct=match.experience_match_pct if match else None,
        recommendation=match.recommendation if match else None,
        ai_summary=match.ai_summary if match else None,
    )
