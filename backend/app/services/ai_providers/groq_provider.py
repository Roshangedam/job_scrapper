"""Groq AI provider — free tier, fast Llama 3.3 inference. Fallback for Gemini."""

import logging
from groq import Groq
from app.config import settings
from app.services.ai_providers.base_provider import BaseAIProvider, RateLimitError

logger = logging.getLogger(__name__)


class GroqProvider(BaseAIProvider):
    """Groq API — free tier: 30 RPM, 1000 RPD, Llama 3.3 70B."""

    @property
    def name(self) -> str:
        return "Groq"

    def is_configured(self) -> bool:
        return bool(settings.GROQ_API_KEY)

    async def generate_json(self, prompt: str, system_prompt: str = "") -> dict:
        if not self.is_configured():
            raise RateLimitError("Groq API key not configured")

        try:
            client = Groq(api_key=settings.GROQ_API_KEY)

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            return self._extract_json(response.choices[0].message.content)

        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate" in error_str or "quota" in error_str:
                logger.warning(f"[Groq] Rate limited: {e}")
                raise RateLimitError(f"Groq rate limited: {e}")
            logger.error(f"[Groq] Error: {e}")
            raise
