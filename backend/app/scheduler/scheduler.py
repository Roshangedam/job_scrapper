"""APScheduler integration — schedules engine scrape runs at configured intervals."""

import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.engine_model import Engine

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def run_scheduled_engine(engine_id: str):
    """Background task: execute a scrape cycle for an engine."""
    from app.scraping.engine_executor import EngineExecutor

    logger.info(f"⏰ Scheduled run for engine: {engine_id}")

    async with AsyncSessionLocal() as db:
        try:
            executor = EngineExecutor(db)
            result = await executor.run_engine(engine_id)
            logger.info(f"✅ Scheduled run completed: {result}")
        except Exception as e:
            logger.error(f"❌ Scheduled run failed for {engine_id}: {e}")


async def sync_engine_schedules():
    """Sync scheduler jobs with active engines from the database."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Engine).where(Engine.is_active == True)
        )
        engines = result.scalars().all()

        # Get current job IDs
        current_jobs = {job.id for job in scheduler.get_jobs()}

        for engine in engines:
            job_id = f"engine_{engine.id}"

            if job_id not in current_jobs:
                scheduler.add_job(
                    run_scheduled_engine,
                    trigger=IntervalTrigger(minutes=engine.refresh_interval_minutes),
                    args=[engine.id],
                    id=job_id,
                    name=f"Scrape: {engine.name}",
                    replace_existing=True,
                )
                logger.info(
                    f"📅 Scheduled engine '{engine.name}' every "
                    f"{engine.refresh_interval_minutes} minutes"
                )


def start_scheduler():
    """Start the APScheduler."""
    if not scheduler.running:
        scheduler.start()

        # Schedule the sync task to run once after startup
        scheduler.add_job(
            sync_engine_schedules,
            trigger="interval",
            minutes=5,  # Re-sync every 5 minutes
            id="sync_schedules",
            name="Sync Engine Schedules",
            replace_existing=True,
        )

        # Run initial sync
        asyncio.get_event_loop().create_task(sync_engine_schedules())

        logger.info("⏰ APScheduler started")


def stop_scheduler():
    """Stop the APScheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("⏰ APScheduler stopped")


def add_engine_schedule(engine_id: str, interval_minutes: int, engine_name: str = ""):
    """Add or update a schedule for a specific engine."""
    job_id = f"engine_{engine_id}"

    scheduler.add_job(
        run_scheduled_engine,
        trigger=IntervalTrigger(minutes=interval_minutes),
        args=[engine_id],
        id=job_id,
        name=f"Scrape: {engine_name}",
        replace_existing=True,
    )
    logger.info(f"📅 Engine '{engine_name}' scheduled every {interval_minutes} min")


def remove_engine_schedule(engine_id: str):
    """Remove schedule for an engine."""
    job_id = f"engine_{engine_id}"
    try:
        scheduler.remove_job(job_id)
        logger.info(f"🗑️ Removed schedule for engine {engine_id}")
    except Exception:
        pass
