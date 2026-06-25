"""ScrapeRun model — execution history per engine run."""

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ScrapeRun(Base):
    """Records each scrape execution for health monitoring."""
    __tablename__ = "scrape_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    engine_id: Mapped[str] = mapped_column(ForeignKey("engines.id"), nullable=False)
    platform_name: Mapped[str] = mapped_column(String(50), nullable=False)

    # Execution info
    status: Mapped[str] = mapped_column(String(20), default="running")  # running, success, failed, partial
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=True)

    # Results
    jobs_found: Mapped[int] = mapped_column(Integer, default=0)
    jobs_new: Mapped[int] = mapped_column(Integer, default=0)
    jobs_duplicate: Mapped[int] = mapped_column(Integer, default=0)

    # Error tracking
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, default=0)

    # Logs
    log: Mapped[str] = mapped_column(Text, nullable=True)

    # Relationships
    engine: Mapped["Engine"] = relationship(back_populates="scrape_runs")
    jobs: Mapped[list["Job"]] = relationship(back_populates="scrape_run")

    def __repr__(self):
        return f"<ScrapeRun {self.engine_id} [{self.status}]>"


from app.models.engine_model import Engine  # noqa: E402, F401
from app.models.job import Job  # noqa: E402, F401
