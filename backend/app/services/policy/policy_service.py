"""Policy orchestration service — ties together validation, extraction, AI, and persistence.

This is the main entry point called by the API endpoints.
"""

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy import PolicyData, PolicySourceFormat
from app.models.university import University
from app.services.policy.file_validator import validate_upload, ValidatedFile
from app.services.policy.text_extractor import extract_text, extract_from_url, ExtractedDocument
from app.services.policy.document_chunker import chunk_document
from app.services.policy.gemini_extractor import extract_policy_from_chunk, merge_chunk_extractions
from app.services.policy.questionnaire import build_policy_from_questionnaire

logger = logging.getLogger("societyos.policy.service")


async def process_document_upload(
    content: bytes,
    filename: str | None,
    content_type: str | None,
    university_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
    mode: str = "direct",
    event_id: uuid.UUID | None = None,
) -> PolicyData:
    """Mode 1 & 2: Process an uploaded document end-to-end.

    Pipeline: validate → extract text → chunk → Gemini extract → merge → persist.
    """
    # 1. Validate
    validated = validate_upload(content, filename, content_type)

    # 2. Extract text
    extracted = extract_text(validated)

    if extracted.char_count < 50:
        logger.warning("Document yielded too little text (%d chars)", extracted.char_count)
        # Still create a record with low confidence
        return await _persist_policy(
            db=db,
            university_id=university_id,
            user_id=user_id,
            event_id=event_id,
            source_format=_detect_source_format(validated, mode),
            source_filename=filename,
            page_count=extracted.page_count,
            text_length=extracted.char_count,
            extraction={
                "confidence_score": 0.05,
                "extraction_warnings": ["Document yielded insufficient text for analysis."],
            },
        )

    # 3. Chunk for processing
    is_prospectus = mode == "prospectus"
    chunks = chunk_document(extracted, mode="prospectus" if is_prospectus else "direct")
    logger.info("Document split into %d chunk(s)", len(chunks))

    # 4. Get university name for context
    uni_name = await _get_university_name(db, university_id)

    # 5. Extract from each chunk
    extractions = []
    for chunk in chunks:
        result = await extract_policy_from_chunk(
            chunk=chunk,
            university_name=uni_name,
            source_type="university prospectus" if is_prospectus else "event policy document",
            is_prospectus=is_prospectus,
        )
        extractions.append(result)

    # 6. Merge results
    merged = await merge_chunk_extractions(extractions) if len(extractions) > 1 else extractions[0]

    # 7. Persist
    return await _persist_policy(
        db=db,
        university_id=university_id,
        user_id=user_id,
        event_id=event_id,
        source_format=_detect_source_format(validated, mode),
        source_filename=filename,
        page_count=extracted.page_count,
        text_length=extracted.char_count,
        extraction=merged,
    )


async def process_url(
    url: str,
    university_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
    event_id: uuid.UUID | None = None,
) -> PolicyData:
    """Mode 1 (URL variant): Fetch a URL and extract policy data."""
    extracted = await extract_from_url(url)

    chunks = chunk_document(extracted, mode="direct")
    uni_name = await _get_university_name(db, university_id)

    extractions = []
    for chunk in chunks:
        result = await extract_policy_from_chunk(
            chunk=chunk, university_name=uni_name, source_type="policy web page",
        )
        extractions.append(result)

    merged = await merge_chunk_extractions(extractions) if len(extractions) > 1 else extractions[0]

    return await _persist_policy(
        db=db,
        university_id=university_id,
        user_id=user_id,
        event_id=event_id,
        source_format=PolicySourceFormat.URL,
        source_filename=None,
        source_url=url,
        page_count=None,
        text_length=extracted.char_count,
        extraction=merged,
    )


async def process_questionnaire(
    university_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
    faculty_advisor: str,
    department: str,
    reports_to: str,
    previous_events: str,
    past_rejections: str,
    event_id: uuid.UUID | None = None,
) -> PolicyData:
    """Mode 3: Build policy data from questionnaire answers."""
    result = await build_policy_from_questionnaire(
        faculty_advisor=faculty_advisor,
        department=department,
        reports_to=reports_to,
        previous_events=previous_events,
        past_rejections=past_rejections,
    )

    return await _persist_policy(
        db=db,
        university_id=university_id,
        user_id=user_id,
        event_id=event_id,
        source_format=PolicySourceFormat.QUESTIONNAIRE,
        source_filename=None,
        page_count=None,
        text_length=None,
        extraction=result,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _get_university_name(db: AsyncSession, university_id: uuid.UUID) -> str:
    result = await db.execute(select(University).where(University.id == university_id))
    uni = result.scalar_one_or_none()
    return uni.name if uni else "this university"


def _detect_source_format(validated: ValidatedFile, mode: str) -> PolicySourceFormat:
    if mode == "prospectus":
        return PolicySourceFormat.PROSPECTUS
    type_map = {"pdf": PolicySourceFormat.PDF, "docx": PolicySourceFormat.DOCX}
    return type_map.get(validated.detected_type, PolicySourceFormat.PDF)


async def _persist_policy(
    db: AsyncSession,
    university_id: uuid.UUID,
    user_id: uuid.UUID,
    event_id: uuid.UUID | None,
    source_format: PolicySourceFormat,
    source_filename: str | None = None,
    source_url: str | None = None,
    page_count: int | None = None,
    text_length: int | None = None,
    extraction: dict[str, Any] | None = None,
) -> PolicyData:
    """Create and persist a PolicyData record from extraction results."""
    ext = extraction or {}

    policy = PolicyData(
        university_id=university_id,
        event_id=event_id,
        created_by=user_id,
        source_format=source_format,
        source_filename=source_filename,
        source_url=source_url,
        source_page_count=page_count,
        source_text_length=text_length,
        approval_chain=ext.get("approval_chain"),
        lead_time_days=ext.get("lead_time_days"),
        required_documents=ext.get("required_documents"),
        sponsorship_rules=ext.get("sponsorship_rules"),
        prohibitions=ext.get("prohibitions"),
        additional_rules=ext.get("additional_rules"),
        confidence_score=ext.get("confidence_score", 0.0),
        extraction_warnings=ext.get("extraction_warnings"),
        source_references=ext.get("source_references"),
    )
    db.add(policy)
    await db.flush()
    await db.refresh(policy)

    logger.info(
        "Policy saved: id=%s, university=%s, format=%s, confidence=%.2f",
        policy.id, university_id, source_format.value,
        policy.confidence_score or 0,
    )
    return policy
