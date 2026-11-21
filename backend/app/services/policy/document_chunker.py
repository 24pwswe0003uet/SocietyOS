"""Document chunking service — splits large documents for Gemini processing.

Gemini 2.0 Flash has ~1M token context, but we still need to:
1. Identify relevant sections (not every page is about event policy).
2. Keep chunks within reasonable token limits for reliable extraction.
3. Preserve page/section references for source attribution.
"""

import logging
import re
from dataclasses import dataclass

from app.services.policy.text_extractor import ExtractedDocument

logger = logging.getLogger("societyos.policy.chunker")

# Approximate: 1 token ≈ 4 chars. We target 100K tokens per chunk to stay safe.
MAX_CHUNK_CHARS = 400_000  # ~100K tokens

# Keywords that indicate policy-relevant content
RELEVANCE_KEYWORDS = [
    "event", "society", "societies", "club", "student organization",
    "approval", "approve", "permission", "consent",
    "budget", "fund", "funding", "sponsor", "sponsorship",
    "venue", "booking", "reservation",
    "policy", "regulation", "rule", "guideline",
    "prohibited", "prohibition", "not allowed", "restricted",
    "deadline", "lead time", "submit", "submission",
    "advisor", "adviser", "faculty", "dean", "head of department",
    "proposal", "application", "registration",
    "student affairs", "extracurricular", "co-curricular",
]


@dataclass
class DocumentChunk:
    """A chunk of document text with metadata."""

    text: str
    char_count: int
    page_range: str | None  # e.g., "Pages 1-15" or None for non-paged docs
    relevance_score: float  # 0.0 to 1.0 based on keyword density
    chunk_index: int


def chunk_document(doc: ExtractedDocument, mode: str = "direct") -> list[DocumentChunk]:
    """Split a document into processable chunks.

    For Mode 1 (direct policy upload): The whole document is likely relevant.
    For Mode 2 (prospectus): Filter to relevant sections first, then chunk.
    """
    if doc.char_count <= MAX_CHUNK_CHARS:
        # Small enough to process in one chunk
        relevance = _score_relevance(doc.text)
        return [DocumentChunk(
            text=doc.text,
            char_count=doc.char_count,
            page_range=f"Pages 1-{doc.page_count}" if doc.page_count else None,
            relevance_score=relevance,
            chunk_index=0,
        )]

    if mode == "prospectus" and doc.pages:
        return _chunk_prospectus_by_relevance(doc)

    return _chunk_by_size(doc)


def _chunk_prospectus_by_relevance(doc: ExtractedDocument) -> list[DocumentChunk]:
    """For prospectus mode: score each page, group high-relevance pages into chunks.

    This avoids sending 300 pages of irrelevant content to Gemini.
    """
    if not doc.pages:
        return _chunk_by_size(doc)

    # Score each page
    scored_pages = []
    for page in doc.pages:
        score = _score_relevance(page["text"])
        scored_pages.append({**page, "relevance": score})

    # Sort by relevance and take top pages (up to MAX_CHUNK_CHARS total)
    scored_pages.sort(key=lambda p: p["relevance"], reverse=True)

    chunks = []
    current_text = ""
    current_pages = []

    for page in scored_pages:
        if page["relevance"] < 0.05:
            continue  # Skip completely irrelevant pages

        if len(current_text) + page["char_count"] > MAX_CHUNK_CHARS:
            if current_text:
                chunks.append(DocumentChunk(
                    text=current_text,
                    char_count=len(current_text),
                    page_range=_format_page_range(current_pages),
                    relevance_score=max(p["relevance"] for p in current_pages) if current_pages else 0,
                    chunk_index=len(chunks),
                ))
            current_text = page["text"]
            current_pages = [page]
        else:
            current_text += f"\n\n--- Page {page['page']} ---\n\n" + page["text"]
            current_pages.append(page)

    # Final chunk
    if current_text:
        chunks.append(DocumentChunk(
            text=current_text,
            char_count=len(current_text),
            page_range=_format_page_range(current_pages),
            relevance_score=max(p["relevance"] for p in current_pages) if current_pages else 0,
            chunk_index=len(chunks),
        ))

    if not chunks:
        # No relevant pages found — send first chunk of full text
        logger.warning("No relevant pages found in prospectus; using first %d chars", MAX_CHUNK_CHARS)
        return _chunk_by_size(doc)

    logger.info(
        "Prospectus chunked: %d relevant chunks from %d pages (skipped %d pages)",
        len(chunks),
        len([p for p in scored_pages if p["relevance"] >= 0.05]),
        len([p for p in scored_pages if p["relevance"] < 0.05]),
    )

    return chunks


def _chunk_by_size(doc: ExtractedDocument) -> list[DocumentChunk]:
    """Simple size-based chunking for direct uploads or fallback."""
    text = doc.text
    chunks = []

    for i in range(0, len(text), MAX_CHUNK_CHARS):
        chunk_text = text[i:i + MAX_CHUNK_CHARS]

        # Try to break at a paragraph boundary
        if i + MAX_CHUNK_CHARS < len(text):
            last_para = chunk_text.rfind("\n\n")
            if last_para > MAX_CHUNK_CHARS * 0.8:
                chunk_text = chunk_text[:last_para]

        chunks.append(DocumentChunk(
            text=chunk_text,
            char_count=len(chunk_text),
            page_range=None,
            relevance_score=_score_relevance(chunk_text),
            chunk_index=len(chunks),
        ))

    return chunks


def _score_relevance(text: str) -> float:
    """Score how relevant a text block is to university event policy (0.0 - 1.0)."""
    if not text:
        return 0.0

    text_lower = text.lower()
    word_count = len(text_lower.split())
    if word_count == 0:
        return 0.0

    hit_count = sum(1 for kw in RELEVANCE_KEYWORDS if kw in text_lower)
    # Normalize: 5+ keyword hits in a page is very relevant
    score = min(1.0, hit_count / 5.0)
    return round(score, 2)


def _format_page_range(pages: list[dict]) -> str:
    """Format a list of page dicts into a readable range string."""
    if not pages:
        return "Unknown"
    page_nums = sorted(p["page"] for p in pages)
    if len(page_nums) == 1:
        return f"Page {page_nums[0]}"
    return f"Pages {page_nums[0]}-{page_nums[-1]}"
