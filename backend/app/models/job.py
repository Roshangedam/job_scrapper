"""Job and JobMatchReport models — scraped job listings and AI match scores."""

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, Float, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Job(Base):
    """Standardized scraped job listing."""
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    engine_id: Mapped[str] = mapped_column(ForeignKey("engines.id"), nullable=False)
    scrape_run_id: Mapped[str] = mapped_column(ForeignKey("scrape_runs.id"), nullable=True)

    # Source
    source_platform: Mapped[str] = mapped_column(String(50), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=True)
    source_job_id: Mapped[str] = mapped_column(String(200), nullable=True)

    # Core info
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    company_name: Mapped[str] = mapped_column(String(300), nullable=True)
    company_logo_url: Mapped[str] = mapped_column(String(1000), nullable=True)
    company_rating: Mapped[float] = mapped_column(Float, nullable=True)

    # Location
    location_city: Mapped[str] = mapped_column(String(200), nullable=True)
    location_state: Mapped[str] = mapped_column(String(200), nullable=True)
    location_country: Mapped[str] = mapped_column(String(100), default="India")
    remote_type: Mapped[str] = mapped_column(String(50), nullable=True)  # remote, hybrid, onsite

    # Description
    description_raw: Mapped[str] = mapped_column(Text, nullable=True)
    description_clean: Mapped[str] = mapped_column(Text, nullable=True)

    # Requirements (JSON string)
    required_skills: Mapped[str] = mapped_column(Text, nullable=True)  # JSON array
    preferred_skills: Mapped[str] = mapped_column(Text, nullable=True)  # JSON array
    experience_min_years: Mapped[float] = mapped_column(Float, nullable=True)
    experience_max_years: Mapped[float] = mapped_column(Float, nullable=True)
    education: Mapped[str] = mapped_column(String(500), nullable=True)

    # Compensation
    salary_min: Mapped[float] = mapped_column(Float, nullable=True)
    salary_max: Mapped[float] = mapped_column(Float, nullable=True)
    salary_currency: Mapped[str] = mapped_column(String(10), default="INR")

    # Metadata
    posted_date: Mapped[str] = mapped_column(String(50), nullable=True)
    applicants_count: Mapped[int] = mapped_column(Integer, nullable=True)
    employment_type: Mapped[str] = mapped_column(String(50), nullable=True)
    seniority_level: Mapped[str] = mapped_column(String(50), nullable=True)

    # Contact
    hr_name: Mapped[str] = mapped_column(String(200), nullable=True)
    hr_email: Mapped[str] = mapped_column(String(255), nullable=True)

    # Full standardized JSON
    job_json: Mapped[str] = mapped_column(Text, nullable=True)

    # Deduplication hash
    dedup_hash: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    engine: Mapped["Engine"] = relationship(back_populates="jobs")
    scrape_run: Mapped["ScrapeRun"] = relationship(back_populates="jobs")
    match_report: Mapped["JobMatchReport"] = relationship(
        back_populates="job", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Job {self.title} @ {self.company_name}>"


class JobMatchReport(Base):
    """AI-generated match score between a job and candidate profile."""
    __tablename__ = "job_match_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), unique=True, nullable=False)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidate_profiles.id"), nullable=False)

    # Scores
    overall_match_pct: Mapped[float] = mapped_column(Float, default=0)
    skill_match_pct: Mapped[float] = mapped_column(Float, default=0)
    experience_match_pct: Mapped[float] = mapped_column(Float, default=0)
    education_match_pct: Mapped[float] = mapped_column(Float, default=0)
    location_match_pct: Mapped[float] = mapped_column(Float, default=0)
    selection_probability: Mapped[float] = mapped_column(Float, default=0)

    # Detailed JSON report
    report_json: Mapped[str] = mapped_column(Text, nullable=True)

    # AI summary
    recommendation: Mapped[str] = mapped_column(String(50), nullable=True)  # STRONG_APPLY, APPLY, CONSIDER, SKIP
    ai_summary: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    job: Mapped["Job"] = relationship(back_populates="match_report")
    candidate: Mapped["CandidateProfile"] = relationship()

    def __repr__(self):
        return f"<JobMatchReport job={self.job_id} match={self.overall_match_pct}%>"


from app.models.engine_model import Engine  # noqa: E402, F401
from app.models.scrape_run import ScrapeRun  # noqa: E402, F401
from app.models.candidate import CandidateProfile  # noqa: E402, F401
