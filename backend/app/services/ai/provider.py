"""Abstract AI provider interface — model-agnostic."""

from abc import ABC, abstractmethod
from typing import Any


class AIProvider(ABC):
    """Interface for AI model providers. Gemini implements this; others can follow."""

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema_description: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Send a prompt expecting JSON-structured output. Returns parsed dict."""
        ...

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        """Send a prompt and return plain text."""
        ...
