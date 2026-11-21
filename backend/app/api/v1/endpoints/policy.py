"""University Policy Intelligence endpoints — FR-002.

Three input modes:
  POST /policy/upload           — Mode 1 (direct) & Mode 2 (prospectus)
  POST /policy/url              — Mode 1 (URL variant)
  POST /policy/questionnaire    — Mode 3
  GET  /policy/{id}             — Get single policy
  GET  /policy/university/{id}  — List policies for a university
  PUT  /policy/{id}/verify      — Human verification
  PUT  /policy/{id}/edit        — Edit individual fields
  POST /policy/{id}/rerun       — Re-run extraction
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Form, Body, Query
from sqlalchemy import select

logger = logging.getLogger(__name__)

from app.core.dependencies import DB, CurrentUser
from app.core.exceptions import NotFoundError, BadRequestError
from app.models.policy import PolicyData
from app.models.university import University
from app.schemas.policy import (
    PolicyDataResponse,
    PolicyListItem,
    QuestionnaireRequest,
    VerifyPolicyRequest,
)
from app.schemas.common import SuccessResponse
from app.services.policy.policy_service import (
    process_document_upload,
    process_url,
    process_questionnaire,
)

router = APIRouter(prefix="/policy", tags=["Policy Intelligence"])


# ---------------------------------------------------------------------------
# Mode 1 & 2: Document Upload
# ---------------------------------------------------------------------------
@router.post("/upload", status_code=201)
async def upload_policy_document(
    user: CurrentUser,
    db: DB,
    file: UploadFile = File(...),
    university_id: str = Form(...),
    event_id: str = Form(None),
    mode: str = Form("direct"),  # "direct" or "prospectus"
) -> SuccessResponse[PolicyDataResponse]:
    """Upload a policy document (PDF/DOCX/TXT) or university prospectus.

    Mode 'direct': assumes the entire document is policy-related.
    Mode 'prospectus': filters to relevant sections before extraction.
    """
    if mode not in ("direct", "prospectus"):
        raise BadRequestError("Mode must be 'direct' or 'prospectus'")

    # Validate university exists
    uni_uuid = uuid.UUID(university_id)
    result = await db.execute(select(University).where(University.id == uni_uuid))
    if not result.scalar_one_or_none():
        raise NotFoundError("University not found")

    evt_uuid = uuid.UUID(event_id) if event_id else None

    content = await file.read()

    policy = await process_document_upload(
        content=content,
        filename=file.filename,
        content_type=file.content_type,
        university_id=uni_uuid,
        user_id=user.id,
        db=db,
        mode=mode,
        event_id=evt_uuid,
    )

    return SuccessResponse(
        data=PolicyDataResponse.model_validate(policy),
        message=f"Policy extracted from {'prospectus' if mode == 'prospectus' else 'document'} successfully",
    )


# ---------------------------------------------------------------------------
# Mode 1: URL variant
# ---------------------------------------------------------------------------
@router.post("/url", status_code=201)
async def extract_from_policy_url(
    user: CurrentUser,
    db: DB,
    url: str = Body(..., embed=True),
    university_id: uuid.UUID = Body(..., embed=True),
    event_id: uuid.UUID | None = Body(None, embed=True),
) -> SuccessResponse[PolicyDataResponse]:
    """Fetch a URL and extract policy data from its content."""
    result = await db.execute(select(University).where(University.id == university_id))
    if not result.scalar_one_or_none():
        raise NotFoundError("University not found")

    policy = await process_url(
        url=url,
        university_id=university_id,
        user_id=user.id,
        db=db,
        event_id=event_id,
    )

    return SuccessResponse(
        data=PolicyDataResponse.model_validate(policy),
        message="Policy extracted from URL successfully",
    )


# ---------------------------------------------------------------------------
# Mode 3: Questionnaire
# ---------------------------------------------------------------------------
@router.post("/questionnaire", status_code=201)
async def submit_questionnaire(
    body: QuestionnaireRequest,
    user: CurrentUser,
    db: DB,
    university_id: uuid.UUID | None = Query(None),
    event_id: uuid.UUID | None = Query(None),
) -> SuccessResponse[PolicyDataResponse]:
    """Answer 5 questions to generate inferred policy data.

    Results are clearly labeled as questionnaire-derived and unverified.
    Accepts university_id/event_id in the JSON body or as query params.
    """
    # Allow query params to fill in missing body fields
    uni_id = body.university_id or university_id
    evt_id = body.event_id or event_id

    if not uni_id:
        raise BadRequestError("university_id is required (in body or query params)")

    logger.info("Questionnaire submission: university_id=%s, event_id=%s", uni_id, evt_id)
    result = await db.execute(select(University).where(University.id == uni_id))
    if not result.scalar_one_or_none():
        raise NotFoundError("University not found")

    policy = await process_questionnaire(
        university_id=uni_id,
        user_id=user.id,
        db=db,
        faculty_advisor=body.faculty_advisor,
        department=body.department,
        reports_to=body.reports_to,
        previous_events=body.previous_events,
        past_rejections=body.past_rejections,
        event_id=evt_id,
    )

    return SuccessResponse(
        data=PolicyDataResponse.model_validate(policy),
        message="Policy inferred from questionnaire responses",
    )


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
@router.get("/{policy_id}")
async def get_policy(
    policy_id: uuid.UUID, user: CurrentUser, db: DB
) -> SuccessResponse[PolicyDataResponse]:
    """Get a specific policy data record with all extracted fields."""
    result = await db.execute(select(PolicyData).where(PolicyData.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise NotFoundError("Policy data not found")

    return SuccessResponse(
        data=PolicyDataResponse.model_validate(policy),
        message="Policy data retrieved",
    )


@router.get("/university/{university_id}")
async def list_policies_for_university(
    university_id: uuid.UUID, user: CurrentUser, db: DB
) -> SuccessResponse[list[PolicyListItem]]:
    """List all policy extraction records for a university."""
    result = await db.execute(
        select(PolicyData)
        .where(PolicyData.university_id == university_id)
        .order_by(PolicyData.created_at.desc())
    )
    policies = result.scalars().all()

    return SuccessResponse(
        data=[PolicyListItem.model_validate(p) for p in policies],
        message=f"{len(policies)} policy record(s) found",
    )


# ---------------------------------------------------------------------------
# Human Review & Verification
# ---------------------------------------------------------------------------
@router.put("/{policy_id}/verify")
async def verify_policy(
    policy_id: uuid.UUID,
    body: VerifyPolicyRequest,
    user: CurrentUser,
    db: DB,
) -> SuccessResponse[PolicyDataResponse]:
    """Mark a policy as human-verified, optionally correcting extracted fields.

    Only non-null fields in the request body are applied as corrections.
    """
    result = await db.execute(select(PolicyData).where(PolicyData.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise NotFoundError("Policy data not found")

    # Apply corrections (only non-None fields)
    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if hasattr(policy, field):
            setattr(policy, field, value)

    # Mark as verified
    policy.is_verified = True
    policy.verified_by = user.id
    policy.verified_at = datetime.now(timezone.utc)

    # Boost confidence if human-verified
    if policy.confidence_score is not None and policy.confidence_score < 0.9:
        policy.confidence_score = 0.95  # Human verification = high confidence

    await db.flush()
    await db.refresh(policy)

    return SuccessResponse(
        data=PolicyDataResponse.model_validate(policy),
        message="Policy verified and confirmed",
    )


@router.put("/{policy_id}/edit")
async def edit_policy_field(
    policy_id: uuid.UUID,
    field: str = Body(..., embed=True),
    value: str | int | float | list | dict | None = Body(..., embed=True),
    user: CurrentUser = ...,
    db: DB = ...,
) -> SuccessResponse[PolicyDataResponse]:
    """Edit a single field on a policy record without full verification."""
    result = await db.execute(select(PolicyData).where(PolicyData.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise NotFoundError("Policy data not found")

    allowed_fields = {
        "approval_chain", "lead_time_days", "required_documents",
        "sponsorship_rules", "prohibitions", "additional_rules",
    }
    if field not in allowed_fields:
        raise BadRequestError(f"Cannot edit field '{field}'. Allowed: {', '.join(sorted(allowed_fields))}")

    setattr(policy, field, value)
    await db.flush()
    await db.refresh(policy)

    return SuccessResponse(
        data=PolicyDataResponse.model_validate(policy),
        message=f"Field '{field}' updated",
    )


# ---------------------------------------------------------------------------
# Re-run analysis
# ---------------------------------------------------------------------------
@router.post("/{policy_id}/rerun")
async def rerun_analysis(
    policy_id: uuid.UUID,
    user: CurrentUser,
    db: DB,
) -> SuccessResponse[PolicyDataResponse]:
    """Re-run policy extraction on the same source.

    For questionnaire-based policies, returns a message to re-submit.
    For document-based, we'd need the original file — this creates a placeholder.
    """
    result = await db.execute(select(PolicyData).where(PolicyData.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise NotFoundError("Policy data not found")

    if policy.source_format.value == "questionnaire":
        raise BadRequestError(
            "Questionnaire-based policies cannot be re-run automatically. "
            "Please submit a new questionnaire."
        )

    raise BadRequestError(
        "To re-run document analysis, please upload the document again. "
        "Original files are not stored for privacy."
    )
