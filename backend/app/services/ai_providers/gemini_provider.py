"""Google Gemini AI provider — free tier, primary provider."""

import logging
from google import genai
from google.genai import types
from app.config import settings
from app.services.ai_providers.base_provider import BaseAIProvider, RateLimitError

logger = logging.getLogger(__name__)


class GeminiProvider(BaseAIProvider):
    """Google Gemini API — free tier: 15 RPM, 1500 RPD."""

    @property
    def name(self) -> str:
        return "Gemini"

    def is_configured(self) -> bool:
        return bool(settings.GEMINI_API_KEY)

    async def generate_json(self, prompt: str, system_prompt: str = "") -> dict:
        if not self.is_configured():
            raise RateLimitError("Gemini API key not configured")

        try:
            client = genai.Client(api_key=settings.GEMINI_API_KEY)

            contents = prompt
            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
                response_mime_type="application/json",
                temperature=0.1,
            )

            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=contents,
                config=config,
            )

            return self._extract_json(response.text)

        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate" in error_str or "quota" in error_str:
                logger.warning(f"[Gemini] Rate limited: {e}")
                raise RateLimitError(f"Gemini rate limited: {e}")
            logger.error(f"[Gemini] Error: {e}")
            raise
