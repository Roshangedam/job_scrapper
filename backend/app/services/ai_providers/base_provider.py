"""Base AI provider interface — all providers must implement this."""

from abc import ABC, abstractmethod
from typing import Optional
import json
import logging

logger = logging.getLogger(__name__)


class BaseAIProvider(ABC):
    """Abstract base class for AI providers (Gemini, Groq, OpenAI, etc.)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging."""
        pass

    @abstractmethod
    async def generate_json(self, prompt: str, system_prompt: str = "") -> dict:
        """Send prompt and return parsed JSON response."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if API key is set."""
        pass

    def _extract_json(self, text: str) -> dict:
        """Extract JSON from response text, handling markdown code blocks."""
        text = text.strip()

        # Remove markdown code block wrappers
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"[{self.name}] Failed to parse JSON: {e}")
            logger.debug(f"[{self.name}] Raw text: {text[:500]}")
            raise ValueError(f"AI response was not valid JSON: {e}")


class RateLimitError(Exception):
    """Raised when an AI provider rate limits the request."""
    pass
