"""Candidate profile model — AI-parsed resume data."""

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class CandidateProfile(Base):
    """Stores AI-parsed candidate data as JSON from uploaded resume."""
    __tablename__ = "candidate_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    engine_id: Mapped[str] = mapped_column(ForeignKey("engines.id"), unique=True, nullable=False)

    # Core info extracted by AI
    name: Mapped[str] = mapped_column(String(200), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    location: Mapped[str] = mapped_column(String(200), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    total_experience_years: Mapped[float] = mapped_column(Float, nullable=True)

    # Full parsed JSON (complete candidate schema)
    profile_json: Mapped[str] = mapped_column(Text, nullable=True)

    # Raw resume text
    resume_text: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    engine: Mapped["Engine"] = relationship(back_populates="candidate_profile")

    def __repr__(self):
        return f"<CandidateProfile {self.name}>"


from app.models.engine_model import Engine  # noqa: E402, F401
