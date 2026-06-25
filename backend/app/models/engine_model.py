"""Engine model — scraping engine configuration."""

import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Engine(Base):
    __tablename__ = "engines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="idle")  # idle, running, paused, error
    refresh_interval_minutes: Mapped[int] = mapped_column(Integer, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    total_jobs_found: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Resume filepath
    resume_path: Mapped[str] = mapped_column(String(500), nullable=True)

    # Relationships
    platforms: Mapped[list["EnginePlatform"]] = relationship(
        back_populates="engine", cascade="all, delete-orphan"
    )
    candidate_profile: Mapped["CandidateProfile"] = relationship(
        back_populates="engine", uselist=False, cascade="all, delete-orphan"
    )
    search_preferences: Mapped[list["SearchPreference"]] = relationship(
        back_populates="engine", cascade="all, delete-orphan"
    )
    scrape_runs: Mapped[list["ScrapeRun"]] = relationship(
        back_populates="engine", cascade="all, delete-orphan"
    )
    jobs: Mapped[list["Job"]] = relationship(
        back_populates="engine", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Engine {self.name} [{self.status}]>"


class EnginePlatform(Base):
    """M2M: which platforms are enabled per engine."""
    __tablename__ = "engine_platforms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    engine_id: Mapped[str] = mapped_column(ForeignKey("engines.id"), nullable=False)
    platform_id: Mapped[str] = mapped_column(ForeignKey("platforms.id"), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    email_alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    engine: Mapped["Engine"] = relationship(back_populates="platforms")
    platform: Mapped["Platform"] = relationship()

    def __repr__(self):
        return f"<EnginePlatform engine={self.engine_id} platform={self.platform_id}>"


class SearchPreference(Base):
    """Scraping search criteria per engine."""
    __tablename__ = "search_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    engine_id: Mapped[str] = mapped_column(ForeignKey("engines.id"), nullable=False)
    pref_type: Mapped[str] = mapped_column(String(50), nullable=False)  # keyword, company, location
    pref_value: Mapped[str] = mapped_column(String(500), nullable=False)

    # Relationships
    engine: Mapped["Engine"] = relationship(back_populates="search_preferences")

    def __repr__(self):
        return f"<SearchPreference {self.pref_type}={self.pref_value}>"


# Avoid circular import — these are string references resolved by SQLAlchemy
from app.models.candidate import CandidateProfile  # noqa: E402, F401
from app.models.scrape_run import ScrapeRun  # noqa: E402, F401
from app.models.job import Job  # noqa: E402, F401
from app.models.platform import Platform  # noqa: E402, F401
