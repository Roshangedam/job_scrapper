"""Engine API routes — CRUD, resume upload, and engine control."""

import json
import os
import uuid
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.engine_model import Engine, EnginePlatform, SearchPreference
from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.schemas.engine import EngineCreate, EngineUpdate, EngineResponse, EngineListResponse
from app.services.ai_service import ai_service
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/engines", tags=["engines"])


@router.get("", response_model=EngineListResponse)
async def list_engines(db: AsyncSession = Depends(get_db)):
    """Get all engines with their platforms and preferences."""
    result = await db.execute(
        select(Engine)
        .options(
            selectinload(Engine.platforms).selectinload(EnginePlatform.platform),
            selectinload(Engine.search_preferences),
            selectinload(Engine.candidate_profile),
        )
        .order_by(Engine.created_at.desc())
    )
    engines = result.scalars().all()

    responses = []
    for eng in engines:
        resp = _engine_to_response(eng)
        responses.append(resp)

    return EngineListResponse(engines=responses, total=len(responses))


@router.get("/{engine_id}", response_model=EngineResponse)
async def get_engine(engine_id: str, db: AsyncSession = Depends(get_db)):
    """Get engine by ID."""
    result = await db.execute(
        select(Engine)
        .where(Engine.id == engine_id)
        .options(
            selectinload(Engine.platforms).selectinload(EnginePlatform.platform),
            selectinload(Engine.search_preferences),
            selectinload(Engine.candidate_profile),
        )
    )
    engine = result.scalar_one_or_none()
    if not engine:
        raise HTTPException(status_code=404, detail="Engine not found")

    return _engine_to_response(engine)


@router.post("", response_model=EngineResponse)
async def create_engine(
    name: str = Form(...),
    email: str = Form(...),
    refresh_interval_minutes: int = Form(60),
    platform_ids: str = Form("[]"),  # JSON array string
    keywords: str = Form("[]"),
    companies: str = Form("[]"),
    locations: str = Form("[]"),
    experience_min: Optional[float] = Form(None),
    experience_max: Optional[float] = Form(None),
    resume: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    """Create a new scraping engine with optional resume upload."""
    # Create engine
    engine = Engine(
        name=name,
        email=email,
        refresh_interval_minutes=refresh_interval_minutes,
    )
    db.add(engine)
    await db.flush()

    # Add platforms
    try:
        platform_list = json.loads(platform_ids)
    except json.JSONDecodeError:
        platform_list = []

    for pid in platform_list:
        ep = EnginePlatform(engine_id=engine.id, platform_id=pid)
        db.add(ep)

    # Add search preferences
    for kw in json.loads(keywords):
        if kw.strip():
            db.add(SearchPreference(engine_id=engine.id, pref_type="keyword", pref_value=kw.strip()))

    for comp in json.loads(companies):
        if comp.strip():
            db.add(SearchPreference(engine_id=engine.id, pref_type="company", pref_value=comp.strip()))

    for loc in json.loads(locations):
        if loc.strip():
            db.add(SearchPreference(engine_id=engine.id, pref_type="location", pref_value=loc.strip()))

    if experience_min is not None:
        db.add(SearchPreference(engine_id=engine.id, pref_type="experience_min", pref_value=str(experience_min)))
    if experience_max is not None:
        db.add(SearchPreference(engine_id=engine.id, pref_type="experience_max", pref_value=str(experience_max)))

    # Handle resume upload
    if resume:
        resume_path = await _save_resume(resume, engine.id)
        engine.resume_path = resume_path

        # Parse resume with AI
        resume_text = await _extract_resume_text(resume_path)
        if resume_text:
            try:
                parsed = await ai_service.parse_resume(resume_text)
                candidate_data = parsed.get("candidate", parsed)

                profile = CandidateProfile(
                    engine_id=engine.id,
                    name=candidate_data.get("name"),
                    email=candidate_data.get("email"),
                    phone=candidate_data.get("phone"),
                    location=candidate_data.get("location"),
                    summary=candidate_data.get("summary"),
                    total_experience_years=candidate_data.get("total_experience_years"),
                    profile_json=json.dumps(candidate_data),
                    resume_text=resume_text,
                )
                db.add(profile)
            except Exception as e:
                logger.error(f"Failed to parse resume with AI: {e}")

    await db.commit()

    # Reload with relationships
    return await get_engine(engine.id, db)


@router.put("/{engine_id}", response_model=EngineResponse)
async def update_engine(
    engine_id: str,
    data: EngineUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing engine."""
    engine = await db.get(Engine, engine_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Engine not found")

    if data.name is not None:
        engine.name = data.name
    if data.email is not None:
        engine.email = data.email
    if data.refresh_interval_minutes is not None:
        engine.refresh_interval_minutes = data.refresh_interval_minutes
    if data.is_active is not None:
        engine.is_active = data.is_active

    # Update platforms
    if data.platform_ids is not None:
        # Delete existing
        result = await db.execute(
            select(EnginePlatform).where(EnginePlatform.engine_id == engine_id)
        )
        for ep in result.scalars().all():
            await db.delete(ep)

        for pid in data.platform_ids:
            db.add(EnginePlatform(engine_id=engine_id, platform_id=pid))

    # Update search preferences
    if any(x is not None for x in [data.keywords, data.companies, data.locations]):
        result = await db.execute(
            select(SearchPreference).where(SearchPreference.engine_id == engine_id)
        )
        for sp in result.scalars().all():
            await db.delete(sp)

        if data.keywords:
            for kw in data.keywords:
                if kw.strip():
                    db.add(SearchPreference(engine_id=engine_id, pref_type="keyword", pref_value=kw.strip()))
        if data.companies:
            for c in data.companies:
                if c.strip():
                    db.add(SearchPreference(engine_id=engine_id, pref_type="company", pref_value=c.strip()))
        if data.locations:
            for l in data.locations:
                if l.strip():
                    db.add(SearchPreference(engine_id=engine_id, pref_type="location", pref_value=l.strip()))

    if data.experience_min is not None:
        db.add(SearchPreference(engine_id=engine_id, pref_type="experience_min", pref_value=str(data.experience_min)))
    if data.experience_max is not None:
        db.add(SearchPreference(engine_id=engine_id, pref_type="experience_max", pref_value=str(data.experience_max)))

    engine.updated_at = datetime.utcnow()
    await db.commit()

    return await get_engine(engine_id, db)


@router.delete("/{engine_id}")
async def delete_engine(engine_id: str, db: AsyncSession = Depends(get_db)):
    """Delete an engine and all associated data."""
    engine = await db.get(Engine, engine_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Engine not found")

    await db.delete(engine)
    await db.commit()

    return {"message": "Engine deleted successfully"}


@router.post("/{engine_id}/run")
async def run_engine(engine_id: str, db: AsyncSession = Depends(get_db)):
    """Manually trigger a scrape run for an engine."""
    from app.scraping.engine_executor import EngineExecutor

    engine = await db.get(Engine, engine_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Engine not found")

    executor = EngineExecutor(db)
    result = await executor.run_engine(engine_id)

    return result


@router.post("/{engine_id}/resume")
async def upload_resume(
    engine_id: str,
    resume: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload/replace resume for an engine and re-parse with AI."""
    engine = await db.get(Engine, engine_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Engine not found")

    resume_path = await _save_resume(resume, engine_id)
    engine.resume_path = resume_path

    resume_text = await _extract_resume_text(resume_path)
    if resume_text:
        try:
            parsed = await ai_service.parse_resume(resume_text)
            candidate_data = parsed.get("candidate", parsed)

            # Update or create profile
            result = await db.execute(
                select(CandidateProfile).where(CandidateProfile.engine_id == engine_id)
            )
            profile = result.scalar_one_or_none()

            if profile:
                profile.name = candidate_data.get("name")
                profile.email = candidate_data.get("email")
                profile.phone = candidate_data.get("phone")
                profile.location = candidate_data.get("location")
                profile.summary = candidate_data.get("summary")
                profile.total_experience_years = candidate_data.get("total_experience_years")
                profile.profile_json = json.dumps(candidate_data)
                profile.resume_text = resume_text
                profile.updated_at = datetime.utcnow()
            else:
                profile = CandidateProfile(
                    engine_id=engine_id,
                    name=candidate_data.get("name"),
                    email=candidate_data.get("email"),
                    phone=candidate_data.get("phone"),
                    location=candidate_data.get("location"),
                    summary=candidate_data.get("summary"),
                    total_experience_years=candidate_data.get("total_experience_years"),
                    profile_json=json.dumps(candidate_data),
                    resume_text=resume_text,
                )
                db.add(profile)

            await db.commit()
            return {"message": "Resume parsed successfully", "candidate": candidate_data}

        except Exception as e:
            logger.error(f"Resume AI parsing failed: {e}")
            await db.commit()
            return {"message": "Resume uploaded but AI parsing failed", "error": str(e)}

    await db.commit()
    return {"message": "Resume uploaded but text extraction failed"}


# ── Helpers ──

async def _save_resume(file: UploadFile, engine_id: str) -> str:
    """Save uploaded resume file to disk."""
    ext = os.path.splitext(file.filename)[1] if file.filename else ".pdf"
    filename = f"resume_{engine_id}{ext}"
    filepath = os.path.join(settings.UPLOADS_DIR, filename)

    os.makedirs(settings.UPLOADS_DIR, exist_ok=True)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    return filepath


async def _extract_resume_text(filepath: str) -> Optional[str]:
    """Extract text from PDF or DOCX resume files."""
    ext = os.path.splitext(filepath)[1].lower()

    try:
        if ext == ".pdf":
            import fitz  # PyMuPDF
            doc = fitz.open(filepath)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text.strip() if text.strip() else None

        elif ext in (".docx", ".doc"):
            from docx import Document
            doc = Document(filepath)
            text = "\n".join(para.text for para in doc.paragraphs)
            return text.strip() if text.strip() else None

        elif ext == ".txt":
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read().strip()

    except Exception as e:
        logger.error(f"Failed to extract text from {filepath}: {e}")

    return None


def _engine_to_response(engine: Engine) -> EngineResponse:
    """Convert Engine ORM object to response schema."""
    platforms = []
    for ep in engine.platforms:
        platforms.append({
            "id": ep.id,
            "platform_id": ep.platform_id,
            "platform_name": ep.platform.name if ep.platform else ep.platform_id,
            "platform_display_name": ep.platform.display_name if ep.platform else ep.platform_id,
            "platform_logo": ep.platform.logo_path if ep.platform else None,
            "is_enabled": ep.is_enabled,
            "email_alerts_enabled": ep.email_alerts_enabled,
        })

    prefs = []
    for sp in engine.search_preferences:
        prefs.append({
            "id": sp.id,
            "pref_type": sp.pref_type,
            "pref_value": sp.pref_value,
        })

    return EngineResponse(
        id=engine.id,
        name=engine.name,
        email=engine.email,
        status=engine.status,
        refresh_interval_minutes=engine.refresh_interval_minutes,
        is_active=engine.is_active,
        last_run_at=engine.last_run_at,
        total_jobs_found=engine.total_jobs_found,
        resume_path=engine.resume_path,
        has_resume=bool(engine.resume_path),
        has_profile=bool(engine.candidate_profile),
        created_at=engine.created_at,
        updated_at=engine.updated_at,
        platforms=platforms,
        search_preferences=prefs,
    )
