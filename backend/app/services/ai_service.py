"""AI Service — orchestrates AI providers with fallback chain.

This is the single entry point for all AI operations:
1. Resume parsing → structured candidate JSON
2. Job description normalization → standardized job JSON
3. Candidate-job match scoring → match report JSON
"""

import json
import logging
from typing import Optional
from app.services.ai_providers.base_provider import BaseAIProvider, RateLimitError
from app.services.ai_providers.gemini_provider import GeminiProvider
from app.services.ai_providers.groq_provider import GroqProvider

logger = logging.getLogger(__name__)

# ── AI Prompt Templates ──

RESUME_PARSE_PROMPT = """Analyze the following resume text and extract structured information.
Return a JSON object with this exact structure:

{
  "candidate": {
    "name": "full name",
    "email": "email address",
    "phone": "phone number",
    "location": "city, country",
    "summary": "2-3 sentence professional summary",
    "total_experience_years": 0.0,
    "skills": {
      "primary": ["top technical skills"],
      "secondary": ["supporting technical skills"],
      "soft": ["soft skills"]
    },
    "experience": [
      {
        "title": "job title",
        "company": "company name",
        "location": "location",
        "start_date": "YYYY-MM",
        "end_date": "YYYY-MM or present",
        "duration_months": 0,
        "description": "brief description",
        "technologies": ["tech used"]
      }
    ],
    "education": [
      {
        "degree": "degree name",
        "institution": "school name",
        "year": 2024,
        "cgpa": null
      }
    ],
    "certifications": ["cert names"],
    "projects": [
      {
        "name": "project name",
        "description": "brief description",
        "technologies": ["tech used"]
      }
    ],
    "preferred_roles": ["role titles candidate is suited for"],
    "preferred_locations": ["locations mentioned or inferred"],
    "expected_salary_range": null
  }
}

Be thorough. Extract ALL skills, experiences, and projects. If a field is not found, use null.

Resume text:
---
{resume_text}
---"""

JOB_NORMALIZE_PROMPT = """Analyze the following raw job listing data and normalize it into a standardized JSON format.
Extract and clean all relevant information. Return this exact structure:

{
  "job": {
    "title": "cleaned job title",
    "company": {
      "name": "company name",
      "industry": "industry if available",
      "size": "company size if available",
      "rating": null
    },
    "location": {
      "city": "city",
      "state": "state",
      "country": "country",
      "remote_type": "remote/hybrid/onsite"
    },
    "description_clean": "cleaned description without HTML, formatted nicely",
    "requirements": {
      "experience_range": {"min_years": 0, "max_years": 0},
      "required_skills": ["explicitly required skills"],
      "preferred_skills": ["nice-to-have skills"],
      "education": "education requirement",
      "certifications": []
    },
    "compensation": {
      "salary_range": {"min": null, "max": null, "currency": "INR"},
      "benefits": []
    },
    "metadata": {
      "posted_date": "date if available",
      "applicants_count": null,
      "employment_type": "full-time/part-time/contract",
      "seniority_level": "entry/mid/senior/lead"
    },
    "contact": {
      "hr_name": null,
      "hr_email": null
    }
  }
}

Raw job data (platform: {platform}):
---
{job_data}
---"""

MATCH_SCORE_PROMPT = """Compare this candidate profile with this job listing and provide a detailed match analysis.
Be honest and thorough. Return this exact JSON structure:

{
  "match_report": {
    "overall_match_percentage": 0,
    "skill_match": {
      "percentage": 0,
      "matched_skills": ["skills that match"],
      "missing_skills": ["required skills candidate lacks"],
      "bonus_skills": ["candidate skills beyond requirements"]
    },
    "experience_match": {
      "percentage": 0,
      "required_years": "X-Y",
      "candidate_years": 0,
      "assessment": "brief assessment"
    },
    "education_match": {
      "percentage": 0,
      "assessment": "brief assessment"
    },
    "location_match": {
      "percentage": 0,
      "assessment": "brief assessment"
    },
    "selection_probability": 0,
    "strengths": ["top 3-5 strengths for this role"],
    "gaps": ["top 3-5 gaps or weaknesses"],
    "recommendation": "STRONG_APPLY or APPLY or CONSIDER or SKIP",
    "ai_summary": "2-3 sentence overall assessment and advice"
  }
}

Score Guidelines:
- overall_match: weighted average (skills 40%, experience 25%, education 15%, location 20%)
- selection_probability: realistic chance of getting selected (0-100)
- recommendation: STRONG_APPLY (>75%), APPLY (50-75%), CONSIDER (30-50%), SKIP (<30%)

Candidate Profile:
---
{candidate_json}
---

Job Listing:
---
{job_json}
---"""


class AIService:
    """Orchestrates AI providers with automatic fallback."""

    def __init__(self):
        self._providers: list[BaseAIProvider] = []
        self._init_providers()

    def _init_providers(self):
        """Initialize providers in priority order."""
        gemini = GeminiProvider()
        groq = GroqProvider()

        if gemini.is_configured():
            self._providers.append(gemini)
            logger.info("✅ Gemini AI provider configured (primary)")

        if groq.is_configured():
            self._providers.append(groq)
            logger.info("✅ Groq AI provider configured (fallback)")

        if not self._providers:
            logger.warning("⚠️ No AI providers configured! Set GEMINI_API_KEY or GROQ_API_KEY in .env")

    def refresh_providers(self):
        """Re-initialize providers (after settings change)."""
        self._providers.clear()
        self._init_providers()

    async def _call_with_fallback(self, prompt: str, system_prompt: str = "") -> dict:
        """Try each provider in order, falling back on rate limits."""
        last_error = None

        for provider in self._providers:
            try:
                logger.info(f"🤖 Using {provider.name} provider...")
                result = await provider.generate_json(prompt, system_prompt)
                logger.info(f"✅ {provider.name} responded successfully")
                return result
            except RateLimitError as e:
                logger.warning(f"⚠️ {provider.name} rate limited, trying next provider...")
                last_error = e
                continue
            except Exception as e:
                logger.error(f"❌ {provider.name} error: {e}")
                last_error = e
                continue

        raise Exception(f"All AI providers failed. Last error: {last_error}")

    async def parse_resume(self, resume_text: str) -> dict:
        """Parse resume text into structured candidate JSON."""
        prompt = RESUME_PARSE_PROMPT.replace("{resume_text}", resume_text)
        system_prompt = "You are an expert resume parser. Extract structured data precisely."
        return await self._call_with_fallback(prompt, system_prompt)

    async def normalize_job(self, raw_job_data: str, platform: str) -> dict:
        """Normalize raw job listing into standardized JSON."""
        prompt = JOB_NORMALIZE_PROMPT.replace("{job_data}", raw_job_data).replace("{platform}", platform)
        system_prompt = "You are a job data normalizer. Clean and structure job data precisely."
        return await self._call_with_fallback(prompt, system_prompt)

    async def compute_match(self, candidate_json: str, job_json: str) -> dict:
        """Compute match score between candidate and job."""
        prompt = MATCH_SCORE_PROMPT.replace("{candidate_json}", candidate_json).replace("{job_json}", job_json)
        system_prompt = "You are a recruitment AI. Analyze candidate-job fit objectively and thoroughly."
        return await self._call_with_fallback(prompt, system_prompt)


# Singleton instance
ai_service = AIService()
