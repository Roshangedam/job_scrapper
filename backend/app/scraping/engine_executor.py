"""Engine Executor — orchestrates a single scrape cycle for an engine.

Responsibilities:
1. Load engine config and search preferences
2. For each enabled platform → run adapter → get raw jobs
3. Deduplicate jobs
4. AI-normalize each job
5. AI-score each job against candidate profile
6. Save to database
7. Send email alerts for high-match jobs
8. Record scrape run health data
"""

import json
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.engine_model import Engine, EnginePlatform, SearchPreference
from app.models.job import Job, JobMatchReport
from app.models.candidate import CandidateProfile
from app.models.scrape_run import ScrapeRun
from app.scraping.adapter_registry import adapter_registry
from app.scraping.base_adapter import RawJobListing
from app.services.ai_service import ai_service
from app.services.dedup_service import DedupService

logger = logging.getLogger(__name__)


class EngineExecutor:
    """Executes a full scrape cycle for a given engine."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.dedup = DedupService()

    async def run_engine(self, engine_id: str) -> dict:
        """Execute a full scrape cycle for the given engine."""
        # Load engine
        engine = await self.db.get(Engine, engine_id)
        if not engine:
            raise ValueError(f"Engine {engine_id} not found")

        if not engine.is_active:
            logger.info(f"⏸️ Engine '{engine.name}' is not active, skipping")
            return {"status": "skipped", "reason": "engine not active"}

        # Update engine status
        engine.status = "running"
        engine.last_run_at = datetime.utcnow()
        await self.db.commit()

        total_new = 0
        total_dupes = 0
        errors = []

        # Get enabled platforms
        result = await self.db.execute(
            select(EnginePlatform)
            .where(EnginePlatform.engine_id == engine_id, EnginePlatform.is_enabled == True)
        )
        engine_platforms = result.scalars().all()

        # Get search preferences
        result = await self.db.execute(
            select(SearchPreference).where(SearchPreference.engine_id == engine_id)
        )
        preferences = result.scalars().all()

        search_params = self._build_search_params(preferences)

        # Get candidate profile for matching
        result = await self.db.execute(
            select(CandidateProfile).where(CandidateProfile.engine_id == engine_id)
        )
        candidate = result.scalar_one_or_none()

        # Run each platform adapter
        for ep in engine_platforms:
            platform_name = ep.platform_id  # We store platform name as ID in seeding
            adapter = adapter_registry.get_adapter(platform_name)

            if not adapter:
                logger.warning(f"⚠️ No adapter found for platform: {platform_name}")
                continue

            # Create scrape run record
            scrape_run = ScrapeRun(
                engine_id=engine_id,
                platform_name=adapter.platform_name,
                status="running",
                started_at=datetime.utcnow(),
            )
            self.db.add(scrape_run)
            await self.db.commit()

            try:
                # Initialize adapter
                await adapter.initialize()

                # Scrape
                raw_jobs = await adapter.scrape_jobs(search_params)

                # Process jobs
                new_count, dupe_count = await self._process_jobs(
                    raw_jobs=raw_jobs,
                    engine=engine,
                    scrape_run=scrape_run,
                    candidate=candidate,
                    platform_name=adapter.platform_name,
                )

                total_new += new_count
                total_dupes += dupe_count

                # Update scrape run
                scrape_run.status = "success"
                scrape_run.jobs_found = len(raw_jobs)
                scrape_run.jobs_new = new_count
                scrape_run.jobs_duplicate = dupe_count
                scrape_run.completed_at = datetime.utcnow()
                scrape_run.duration_seconds = (
                    scrape_run.completed_at - scrape_run.started_at
                ).total_seconds()

            except Exception as e:
                logger.error(f"❌ Scrape failed for {adapter.platform_name}: {e}")
                scrape_run.status = "failed"
                scrape_run.error_message = str(e)
                scrape_run.error_count = 1
                scrape_run.completed_at = datetime.utcnow()
                errors.append(str(e))

            finally:
                await adapter.cleanup()
                await self.db.commit()

        # Update engine status
        engine.status = "idle" if not errors else "error"
        engine.total_jobs_found += total_new
        await self.db.commit()

        result = {
            "status": "success" if not errors else "partial",
            "new_jobs": total_new,
            "duplicates": total_dupes,
            "errors": errors,
        }

        logger.info(f"✅ Engine '{engine.name}' completed: {result}")
        return result

    async def _process_jobs(
        self,
        raw_jobs: List[RawJobListing],
        engine: Engine,
        scrape_run: ScrapeRun,
        candidate: Optional[CandidateProfile],
        platform_name: str,
    ) -> tuple[int, int]:
        """Process raw jobs: dedup, normalize, match, and save."""
        new_count = 0
        dupe_count = 0

        for raw_job in raw_jobs:
            try:
                # Check for duplicates
                dedup_hash = self.dedup.compute_hash(raw_job)
                is_dupe = await self.dedup.is_duplicate(self.db, dedup_hash)

                if is_dupe:
                    dupe_count += 1
                    continue

                # AI normalize the job
                normalized = None
                try:
                    normalized = await ai_service.normalize_job(
                        raw_job.to_raw_text(), platform_name
                    )
                except Exception as e:
                    logger.warning(f"AI normalization failed, saving raw data: {e}")

                # Create Job record
                job = self._create_job_record(
                    raw_job=raw_job,
                    normalized=normalized,
                    engine=engine,
                    scrape_run=scrape_run,
                    dedup_hash=dedup_hash,
                )
                self.db.add(job)
                await self.db.flush()  # Get job.id

                # AI match scoring (if candidate profile exists)
                if candidate and candidate.profile_json:
                    try:
                        job_json = job.job_json or raw_job.to_raw_text()
                        match_result = await ai_service.compute_match(
                            candidate.profile_json, job_json
                        )
                        match_data = match_result.get("match_report", match_result)

                        match_report = JobMatchReport(
                            job_id=job.id,
                            candidate_id=candidate.id,
                            overall_match_pct=match_data.get("overall_match_percentage", 0),
                            skill_match_pct=match_data.get("skill_match", {}).get("percentage", 0),
                            experience_match_pct=match_data.get("experience_match", {}).get("percentage", 0),
                            education_match_pct=match_data.get("education_match", {}).get("percentage", 0),
                            location_match_pct=match_data.get("location_match", {}).get("percentage", 0),
                            selection_probability=match_data.get("selection_probability", 0),
                            recommendation=match_data.get("recommendation", ""),
                            ai_summary=match_data.get("ai_summary", ""),
                            report_json=json.dumps(match_data),
                        )
                        self.db.add(match_report)
                    except Exception as e:
                        logger.warning(f"Match scoring failed for job {job.title}: {e}")

                new_count += 1

            except Exception as e:
                logger.error(f"Failed to process job: {e}")
                continue

        await self.db.commit()
        return new_count, dupe_count

    def _create_job_record(
        self,
        raw_job: RawJobListing,
        normalized: Optional[dict],
        engine: Engine,
        scrape_run: ScrapeRun,
        dedup_hash: str,
    ) -> Job:
        """Create a Job DB record from raw + normalized data."""
        # Extract from normalized AI data if available
        n_job = {}
        if normalized:
            n_job = normalized.get("job", normalized)

        n_req = n_job.get("requirements", {})
        n_comp = n_job.get("compensation", {})
        n_loc = n_job.get("location", {})
        n_meta = n_job.get("metadata", {})
        n_contact = n_job.get("contact", {})
        n_salary = n_comp.get("salary_range", {})
        n_exp = n_req.get("experience_range", {})

        # Build skills fallbacks from raw data when AI normalization unavailable
        raw_required_skills = n_req.get("required_skills", [])
        if not raw_required_skills and raw_job.skills_list:
            raw_required_skills = raw_job.skills_list

        raw_preferred_skills = n_req.get("preferred_skills", [])
        if not raw_preferred_skills and raw_job.skills_preferred:
            raw_preferred_skills = raw_job.skills_preferred

        # Build education fallback
        raw_education = n_req.get("education", "")
        if not raw_education:
            edu_parts = []
            if raw_job.education_ug:
                edu_parts.append(f"UG: {raw_job.education_ug}")
            if raw_job.education_pg:
                edu_parts.append(f"PG: {raw_job.education_pg}")
            raw_education = "; ".join(edu_parts)

        # Build posted_date fallback (prefer ISO date if available)
        raw_posted = n_meta.get("posted_date", "")
        if not raw_posted:
            raw_posted = raw_job.date_posted_iso or raw_job.posted_date

        # Build extra metadata for job_json
        extra = {}
        if raw_job.role:
            extra["role"] = raw_job.role
        if raw_job.industry_type:
            extra["industry_type"] = raw_job.industry_type
        if raw_job.department:
            extra["department"] = raw_job.department
        if raw_job.role_category:
            extra["role_category"] = raw_job.role_category
        if raw_job.apply_url:
            extra["apply_url"] = raw_job.apply_url
        if raw_job.valid_through:
            extra["valid_through"] = raw_job.valid_through
        if raw_job.description_html:
            extra["description_html"] = raw_job.description_html
        if raw_job.extra_data:
            extra["extra"] = raw_job.extra_data

        # Merge extra into the normalized json
        final_job_json = n_job.copy() if n_job else {}
        final_job_json.update(extra)

        return Job(
            engine_id=engine.id,
            scrape_run_id=scrape_run.id,
            source_platform=raw_job.source_platform,
            source_url=raw_job.source_url,
            source_job_id=raw_job.source_job_id,
            title=n_job.get("title", raw_job.title),
            company_name=n_job.get("company", {}).get("name", raw_job.company_name) if isinstance(n_job.get("company"), dict) else raw_job.company_name,
            company_logo_url=raw_job.company_logo_url,
            company_rating=raw_job.company_rating,
            location_city=n_loc.get("city", raw_job.location),
            location_state=n_loc.get("state", ""),
            location_country=n_loc.get("country", "India"),
            remote_type=n_loc.get("remote_type", ""),
            description_raw=raw_job.description_raw,
            description_clean=n_job.get("description_clean", raw_job.description_raw),
            required_skills=json.dumps(raw_required_skills),
            preferred_skills=json.dumps(raw_preferred_skills),
            experience_min_years=n_exp.get("min_years"),
            experience_max_years=n_exp.get("max_years"),
            education=raw_education,
            salary_min=n_salary.get("min"),
            salary_max=n_salary.get("max"),
            salary_currency=n_salary.get("currency", "INR"),
            posted_date=raw_posted,
            applicants_count=n_meta.get("applicants_count", raw_job.applicants_count),
            employment_type=n_meta.get("employment_type", raw_job.employment_type),
            seniority_level=n_meta.get("seniority_level", ""),
            hr_name=n_contact.get("hr_name", raw_job.hr_name),
            hr_email=n_contact.get("hr_email", raw_job.hr_email),
            job_json=json.dumps(final_job_json) if final_job_json else None,
            dedup_hash=dedup_hash,
            is_duplicate=False,
        )

    def _build_search_params(self, preferences: list) -> dict:
        """Convert SearchPreference records to scraper params dict."""
        params = {
            "keywords": [],
            "companies": [],
            "locations": [],
        }
        for pref in preferences:
            if pref.pref_type == "keyword":
                params["keywords"].append(pref.pref_value)
            elif pref.pref_type == "company":
                params["companies"].append(pref.pref_value)
            elif pref.pref_type == "location":
                params["locations"].append(pref.pref_value)
            elif pref.pref_type == "experience_min":
                try:
                    params["experience_min"] = float(pref.pref_value)
                except ValueError:
                    pass
            elif pref.pref_type == "experience_max":
                try:
                    params["experience_max"] = float(pref.pref_value)
                except ValueError:
                    pass

        return params
