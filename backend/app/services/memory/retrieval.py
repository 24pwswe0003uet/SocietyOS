"""Semantic memory retrieval with tenant isolation.

CRITICAL: All queries are filtered by university_id to enforce
tenant isolation. A society cannot access another society's private
event information. University-wide knowledge requires verified status.
"""

import logging
import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.event_memory import EventMemory, VerificationStatus
from app.services.memory.embedding import generate_embedding

logger = logging.getLogger("societyos.memory.retrieval")


async def retrieve_relevant_memories(
    db: AsyncSession,
    university_id: uuid.UUID,
    event_type: str,
    exclude_event_id: uuid.UUID | None = None,
    society_id: uuid.UUID | None = None,
    query_text: str | None = None,
    limit: int | None = None,
) -> list[EventMemory]:
    """Retrieve the most relevant historical event memories.

    Tenant isolation rules:
    - Always filters by university_id (hard requirement)
    - If society_id is provided, returns: own society's memories + verified university-wide memories
    - Without society_id, returns only verified memories for the university
    - Excluded/inactive memories are never returned
    - Current event is excluded from results

    Retrieval strategy:
    1. If query_text is provided, use vector similarity search
    2. Otherwise, filter by event_type match + recency
    """
    max_results = limit or settings.MEMORY_RETRIEVAL_LIMIT

    if query_text:
        return await _vector_search(
            db, university_id, query_text, exclude_event_id,
            society_id, max_results,
        )
    else:
        return await _metadata_search(
            db, university_id, event_type, exclude_event_id,
            society_id, max_results,
        )


async def _vector_search(
    db: AsyncSession,
    university_id: uuid.UUID,
    query_text: str,
    exclude_event_id: uuid.UUID | None,
    society_id: uuid.UUID | None,
    limit: int,
) -> list[EventMemory]:
    """Search using cosine similarity on embeddings.

    Uses ORM-level filtering + Python-side similarity scoring
    to avoid raw SQL compatibility issues with asyncpg parameter binding.
    """
    query_embedding = await generate_embedding(query_text)

    # Build ORM query with tenant isolation
    query = (
        select(EventMemory)
        .where(
            EventMemory.university_id == university_id,
            EventMemory.is_active == True,
            EventMemory.verification_status != "excluded",
        )
    )

    if exclude_event_id:
        query = query.where(EventMemory.event_id != exclude_event_id)

    # Tenant isolation
    if society_id:
        query = query.where(
            (EventMemory.society_id == society_id)
            | (EventMemory.verification_status == "verified")
        )
    else:
        query = query.where(EventMemory.verification_status == "verified")

    # Try pgvector ordering, fall back to fetch-all + Python sort
    try:
        from app.models.event_memory import HAS_PGVECTOR
        if HAS_PGVECTOR:
            query = query.order_by(
                EventMemory.embedding.cosine_distance(query_embedding)
            ).limit(limit * 2)
        else:
            query = query.limit(limit * 5)  # Fetch more, sort in Python
    except Exception:
        query = query.limit(limit * 5)

    result = await db.execute(query)
    memories = list(result.scalars().all())

    # Filter by similarity threshold (cosine similarity = 1 - distance)
    # We can't easily do this in SQL with asyncpg params, so filter in Python
    filtered = []
    for m in memories:
        if len(filtered) >= limit:
            break
        # Compute cosine similarity
        import numpy as np
        mem_vec = np.array(m.embedding)
        q_vec = np.array(query_embedding)
        dot = np.dot(mem_vec, q_vec)
        norm_product = np.linalg.norm(mem_vec) * np.linalg.norm(q_vec)
        similarity = dot / norm_product if norm_product > 0 else 0
        if similarity >= settings.MEMORY_SIMILARITY_THRESHOLD:
            filtered.append(m)

    return filtered


async def _metadata_search(
    db: AsyncSession,
    university_id: uuid.UUID,
    event_type: str,
    exclude_event_id: uuid.UUID | None,
    society_id: uuid.UUID | None,
    limit: int,
) -> list[EventMemory]:
    """Fallback search using metadata filters (event type + recency)."""
    query = (
        select(EventMemory)
        .where(
            EventMemory.university_id == university_id,
            EventMemory.is_active == True,
            EventMemory.verification_status != "excluded",
        )
    )

    if exclude_event_id:
        query = query.where(EventMemory.event_id != exclude_event_id)

    # Tenant isolation
    if society_id:
        query = query.where(
            (EventMemory.society_id == society_id)
            | (EventMemory.verification_status == "verified")
        )
    else:
        query = query.where(EventMemory.verification_status == "verified")

    # Prioritize same event type, then recency
    query = query.order_by(
        (EventMemory.event_type == event_type).desc(),
        EventMemory.created_at.desc(),
    ).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


async def retrieve_memories_for_event(
    db: AsyncSession,
    university_id: uuid.UUID,
    society_id: uuid.UUID,
    event_type: str,
    event_description: str,
    exclude_event_id: uuid.UUID | None = None,
) -> list[EventMemory]:
    """High-level retrieval for event generation context.

    Combines vector search (if description available) with metadata fallback.
    """
    if event_description and len(event_description) > 20:
        query_text = f"{event_type}: {event_description}"
        memories = await retrieve_relevant_memories(
            db=db,
            university_id=university_id,
            event_type=event_type,
            exclude_event_id=exclude_event_id,
            society_id=society_id,
            query_text=query_text,
        )
        if memories:
            return memories

    # Fallback to metadata search
    return await retrieve_relevant_memories(
        db=db,
        university_id=university_id,
        event_type=event_type,
        exclude_event_id=exclude_event_id,
        society_id=society_id,
    )
