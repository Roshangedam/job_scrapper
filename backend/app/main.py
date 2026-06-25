"""Job Scrapper — FastAPI Application Entry Point.

Initializes the database, discovers adapters, seeds platforms, and registers all API routes.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db, AsyncSessionLocal
from app.scraping.adapter_registry import adapter_registry
from app.scheduler.scheduler import start_scheduler, stop_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("🚀 Starting Job Scrapper Backend...")

    # Initialize database
    await init_db()
    logger.info("✅ Database initialized")

    # Discover platform adapters
    adapter_registry.discover_adapters()
    logger.info(f"✅ Adapters discovered: {adapter_registry.available_platforms}")

    # Seed platforms in DB
    await seed_platforms()

    # Start scheduler
    start_scheduler()
    logger.info("✅ Scheduler started")

    yield

    # Shutdown
    stop_scheduler()
    logger.info("👋 Job Scrapper Backend shut down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
from app.api import engines, jobs, dashboard, platforms, settings as settings_api  # noqa

app.include_router(engines.router)
app.include_router(jobs.router)
app.include_router(dashboard.router)
app.include_router(platforms.router)
app.include_router(settings_api.router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "adapters": adapter_registry.available_platforms,
    }


async def seed_platforms():
    """Seed platform records from discovered adapters."""
    from app.models.platform import Platform
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        for info in adapter_registry.get_platform_info():
            result = await db.execute(
                select(Platform).where(Platform.name == info["name"])
            )
            existing = result.scalar_one_or_none()

            if not existing:
                platform = Platform(
                    id=info["name"],  # Use name as ID for simplicity
                    name=info["name"],
                    display_name=info["display_name"],
                    logo_path=info["logo"],
                    adapter_class=info["name"],
                    is_available=True,
                )
                db.add(platform)
                logger.info(f"🌱 Seeded platform: {info['display_name']}")

        await db.commit()
