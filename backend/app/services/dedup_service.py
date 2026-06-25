"""Duplicate detection service — prevents storing the same job twice."""

import hashlib
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.scraping.base_adapter import RawJobListing
from app.models.job import Job

logger = logging.getLogger(__name__)


class DedupService:
    """Detects duplicate jobs using content hashing."""

    def compute_hash(self, job: RawJobListing) -> str:
        """Compute a dedup hash from job title + company + platform."""
        content = (
            f"{job.title.lower().strip()}"
            f"|{job.company_name.lower().strip()}"
            f"|{job.source_platform}"
            f"|{job.source_job_id or job.source_url}"
        )
        return hashlib.sha256(content.encode()).hexdigest()

    async def is_duplicate(self, db: AsyncSession, dedup_hash: str) -> bool:
        """Check if a job with this hash already exists in the database."""
        result = await db.execute(
            select(Job.id).where(Job.dedup_hash == dedup_hash).limit(1)
        )
        return result.scalar_one_or_none() is not None
