"""Gemini AI provider implementation using httpx (REST API)."""

import json
import logging
import re
from typing import Any

import httpx

from app.config import settings
from app.services.ai.provider import AIProvider

logger = logging.getLogger("societyos.ai.gemini")

GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={key}"
)


class GeminiProvider(AIProvider):
    """Calls Gemini REST API. No SDK dependency — just httpx."""

    def __init__(self):
        self.model = settings.GEMINI_MODEL
        self.api_key = settings.GEMINI_API_KEY
        self.default_temp = settings.GEMINI_TEMPERATURE
        self.default_max_tokens = settings.GEMINI_MAX_TOKENS

    def _url(self) -> str:
        return GEMINI_API_URL.format(model=self.model, key=self.api_key)

    async def _call(
        self, prompt: str, temperature: float, max_tokens: int
    ) -> str:
        """Make a single Gemini API call and return the text response."""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(self._url(), json=payload)
            resp.raise_for_status()
            data = resp.json()

        # Extract text from Gemini response
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            logger.error("Unexpected Gemini response structure: %s", data)
            raise ValueError("Failed to parse Gemini response") from e

    def _extract_json(self, text: str) -> dict[str, Any]:
        """Extract JSON from Gemini's text response (handles markdown fences)."""
        # Try to find JSON block in markdown code fences
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        json_str = match.group(1) if match else text.strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from Gemini: %s", text[:500])
            raise ValueError("Gemini did not return valid JSON")

    async def generate_structured(
        self,
        prompt: str,
        schema_description: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Send a prompt expecting JSON output. Parses and returns dict."""
        full_prompt = (
            f"{prompt}\n\n"
            f"Respond ONLY with valid JSON matching this schema:\n{schema_description}\n"
            f"Do not include any text outside the JSON object."
        )
        raw = await self._call(
            full_prompt,
            temperature or self.default_temp,
            max_tokens or self.default_max_tokens,
        )
        return self._extract_json(raw)

    async def generate_text(
        self,
        prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Send a prompt and return plain text."""
        return await self._call(
            prompt,
            temperature or self.default_temp,
            max_tokens or self.default_max_tokens,
        )


# Singleton instance
gemini_provider = GeminiProvider()
