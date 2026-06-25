"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    # ── App ──
    APP_NAME: str = "Job Scrapper"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Database ──
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/job_scrapper.db"

    # ── AI Providers (Free Tiers) ──
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.0-flash"

    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # ── Email ──
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_EMAIL: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True

    # ── Scraping ──
    DEFAULT_SCRAPE_INTERVAL_MINUTES: int = 60
    MAX_JOBS_PER_SCRAPE: int = 50
    PLAYWRIGHT_HEADLESS: bool = True

    # ── Paths ──
    DATA_DIR: str = "./data"
    UPLOADS_DIR: str = "./data/uploads"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


settings = Settings()

# Ensure directories exist
Path(settings.DATA_DIR).mkdir(parents=True, exist_ok=True)
Path(settings.UPLOADS_DIR).mkdir(parents=True, exist_ok=True)
