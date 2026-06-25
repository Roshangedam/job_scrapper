"""Dashboard API — stats overview and scrape health monitoring."""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case

from app.database import get_db
from app.models.engine_model import Engine
from app.models.job import Job, JobMatchReport
from app.models.scrape_run import ScrapeRun

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get overview stats for the dashboard home."""
    # Total engines
    result = await db.execute(select(func.count(Engine.id)))
    total_engines = result.scalar() or 0

    # Active engines
    result = await db.execute(
        select(func.count(Engine.id)).where(Engine.is_active == True)
    )
    active_engines = result.scalar() or 0

    # Total jobs (non-duplicate)
    result = await db.execute(
        select(func.count(Job.id)).where(Job.is_duplicate == False)
    )
    total_jobs = result.scalar() or 0

    # Jobs today
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(Job.id)).where(
            Job.scraped_at >= today,
            Job.is_duplicate == False,
        )
    )
    jobs_today = result.scalar() or 0

    # Average match %
    result = await db.execute(
        select(func.avg(JobMatchReport.overall_match_pct))
    )
    avg_match = result.scalar() or 0

    # High match jobs (>= 75%)
    result = await db.execute(
        select(func.count(JobMatchReport.id))
        .where(JobMatchReport.overall_match_pct >= 75)
    )
    high_match_count = result.scalar() or 0

    return {
        "total_engines": total_engines,
        "active_engines": active_engines,
        "total_jobs": total_jobs,
        "jobs_today": jobs_today,
        "average_match_pct": round(avg_match, 1),
        "high_match_count": high_match_count,
    }


@router.get("/scrape-health")
async def get_scrape_health(db: AsyncSession = Depends(get_db)):
    """Get scrape health monitoring data — recent runs and platform stats."""
    # Recent scrape runs (last 20)
    result = await db.execute(
        select(ScrapeRun)
        .order_by(ScrapeRun.started_at.desc())
        .limit(20)
    )
    runs = result.scalars().all()

    recent_runs = []
    for run in runs:
        recent_runs.append({
            "id": run.id,
            "engine_id": run.engine_id,
            "platform_name": run.platform_name,
            "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "duration_seconds": run.duration_seconds,
            "jobs_found": run.jobs_found,
            "jobs_new": run.jobs_new,
            "jobs_duplicate": run.jobs_duplicate,
            "error_message": run.error_message,
        })

    # Platform-level health stats
    result = await db.execute(
        select(
            ScrapeRun.platform_name,
            func.count(ScrapeRun.id).label("total_runs"),
            func.sum(case((ScrapeRun.status == "success", 1), else_=0)).label("success_count"),
            func.sum(case((ScrapeRun.status == "failed", 1), else_=0)).label("failure_count"),
            func.avg(ScrapeRun.duration_seconds).label("avg_duration"),
            func.sum(ScrapeRun.jobs_new).label("total_new_jobs"),
        )
        .group_by(ScrapeRun.platform_name)
    )
    platform_stats = []
    for row in result.all():
        total = row.total_runs or 0
        success = row.success_count or 0
        platform_stats.append({
            "platform": row.platform_name,
            "total_runs": total,
            "success_rate": round((success / total) * 100, 1) if total > 0 else 0,
            "failure_count": row.failure_count or 0,
            "avg_duration_seconds": round(row.avg_duration or 0, 1),
            "total_new_jobs": row.total_new_jobs or 0,
        })

    return {
        "recent_runs": recent_runs,
        "platform_stats": platform_stats,
    }
