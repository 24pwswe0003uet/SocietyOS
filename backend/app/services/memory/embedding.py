"""Embedding generation using Gemini's text-embedding API.

Supports configurable model and dimensions via app settings.
Falls back to random embeddings when API is unavailable (dev mode).
"""

import logging
import numpy as np
import httpx

from app.config import settings

logger = logging.getLogger("societyos.memory.embedding")

EMBEDDING_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:embedContent?key={key}"
)


async def generate_embedding(text: str) -> list[float]:
    """Generate an embedding vector for the given text.

    Uses Gemini's text-embedding API. Falls back to a deterministic
    pseudo-random vector when the API key is not configured (dev mode).
    """
    if not settings.GEMINI_API_KEY:
        logger.warning("No GEMINI_API_KEY — generating deterministic fallback embedding")
        return _fallback_embedding(text)

    try:
        url = EMBEDDING_API_URL.format(
            model=settings.EMBEDDING_MODEL,
            key=settings.GEMINI_API_KEY,
        )
        payload = {
            "model": f"models/{settings.EMBEDDING_MODEL}",
            "content": {"parts": [{"text": text}]},
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        values = data["embedding"]["values"]
        # Ensure correct dimensions
        if len(values) != settings.EMBEDDING_DIMENSIONS:
            logger.warning(
                "Embedding dimensions mismatch: got %d, expected %d. Truncating/padding.",
                len(values), settings.EMBEDDING_DIMENSIONS,
            )
            values = _resize_embedding(values, settings.EMBEDDING_DIMENSIONS)
        return values

    except Exception as e:
        logger.error("Embedding API failed: %s — using fallback", e)
        return _fallback_embedding(text)


def _fallback_embedding(text: str) -> list[float]:
    """Generate a deterministic pseudo-random embedding from text hash.

    This allows the system to function without API access,
    though similarity search quality will be degraded.
    """
    seed = hash(text) % (2**32)
    rng = np.random.RandomState(seed)
    vec = rng.randn(settings.EMBEDDING_DIMENSIONS).astype(float)
    # Normalize to unit vector
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


def _resize_embedding(values: list[float], target_dim: int) -> list[float]:
    """Truncate or pad an embedding to match target dimensions."""
    if len(values) >= target_dim:
        return values[:target_dim]
    # Pad with zeros
    return values + [0.0] * (target_dim - len(values))
