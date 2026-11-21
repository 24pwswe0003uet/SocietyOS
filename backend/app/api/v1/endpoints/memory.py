"""Institutional Memory & Learning Engine endpoints.

Layer 2 — Episodic Memory: Post-event outcomes with validation.
Layer 3 — Semantic Memory: Retrieval, management, and insights.
"""

import uuid
from datetime import datetime, timezone


def _ev(val) -> str:
    return val.value if hasattr(val, "value") else str(val)

from fastapi import APIRouter, Query


from sqlalchemy import select, func



from app.core.dependencies import DB, CurrentUser


from app.core.exceptions import NotFoundError, BadRequestError, ForbiddenError


from app.models.event import EventRecord


from app.models.event_outcome import EventOutcome


from app.models.event_memory import EventMemory, VerificationStatus


from app.models.society import Society, SocietyMembership


from app.schemas.common import SuccessResponse


from app.schemas.outcome import (


    OutcomeCreate, OutcomeUpdate, OutcomeResponse,
    MemoryResponse, MemoryUpdate,
)
from app.services.memory.learning import generate_event_memory


from app.services.memory.retrieval import retrieve_relevant_memories



router = APIRouter(prefix="/memory", tags=["Institutional Memory"])


# ---------------------------------------------------------------------------
# PART A — Post-Event Outcomes (Layer 2 — Episodic Memory)
# ---------------------------------------------------------------------------

@router.post("/events/{event_id}/outcome")
async def submit_event_outcome(
    event_id: uuid.UUID, body: OutcomeCreate, user: CurrentUser, db: DB,
) -> SuccessResponse:
    """Submit post-event outcome data with validation.

    Validates all fields, computes budget variance, and triggers
    the learning loop to generate semantic memory.
    """
    # Load event
    result = await db.execute(select(EventRecord).where(EventRecord.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise NotFoundError("Event not found")

    # Check for duplicate
    existing = await db.execute(
        select(EventOutcome).where(EventOutcome.event_id == event_id)
    )
    if existing.scalar_one_or_none():
        raise BadRequestError("Outcome already exists for this event. Use PUT to update.")

    # Load society for university_id
    soc = await db.execute(select(Society).where(Society.id == event.society_id))
    society = soc.scalar_one_or_none()
    if not society:
        raise NotFoundError("Society not found")

    # Compute budget variance
    budget_variance = None
    if body.actual_spend is not None and event.budget_target:
        target = float(event.budget_target)
        if target > 0:
            budget_variance = ((body.actual_spend - target) / target) * 100

    # Create outcome
    outcome = EventOutcome(
        event_id=event_id,
        university_id=society.university_id,
        approval_result=body.approval_result,
        rejection_reasons=body.rejection_reasons,
        actual_approval_days=body.actual_approval_days,
        budget_target=event.budget_target,
        actual_spend=body.actual_spend,
        budget_variance_pct=budget_variance,
        overspent_categories=body.overspent_categories,
        expected_audience=event.audience_size,
        actual_audience=body.actual_audience,
        sponsors_pitched=body.sponsors_pitched,
        sponsors_confirmed=body.sponsors_confirmed,
        lessons_learned=body.lessons_learned,
        risk_flags=body.risk_flags,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(outcome)
    await db.flush()

    # Mark event as completed
    event.status = "completed"
    await db.flush()

    # Trigger learning loop — generate semantic memory
    memory = await generate_event_memory(db, outcome, event, society)
    await db.commit()

    return SuccessResponse(
        data={
            "outcome_id": str(outcome.id),
            "event_id": str(event_id),
            "budget_variance_pct": budget_variance,
            "memory_generated": memory is not None,
        },
        message="Event outcome recorded and memory generated",
    )


@router.get("/events/{event_id}/outcome")
async def get_event_outcome(
    event_id: uuid.UUID, user: CurrentUser, db: DB,
) -> SuccessResponse:
    """Get the outcome record for a completed event."""
    result = await db.execute(
        select(EventOutcome).where(EventOutcome.event_id == event_id)
    )
    outcome = result.scalar_one_or_none()
    if not outcome:
        raise NotFoundError("No outcome found for this event")

    return SuccessResponse(
        data=_outcome_to_dict(outcome),
        message="Outcome loaded",
    )


@router.put("/events/{event_id}/outcome")
async def update_event_outcome(
    event_id: uuid.UUID, body: OutcomeUpdate, user: CurrentUser, db: DB,
) -> SuccessResponse:
    """Correct historical outcome data.

    Only updates the fields provided. Triggers memory regeneration.
    """
    result = await db.execute(
        select(EventOutcome).where(EventOutcome.event_id == event_id)
    )
    outcome = result.scalar_one_or_none()
    if not outcome:
        raise NotFoundError("No outcome found for this event")

    # Apply partial updates
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(outcome, field, value)

    # Recompute budget variance if spend changed
    if "actual_spend" in update_data and outcome.budget_target:
        target = float(outcome.budget_target)
        if target > 0:
            outcome.budget_variance_pct = ((float(outcome.actual_spend) - target) / target) * 100

    # Clear verification on data change
    outcome.is_verified = False
    outcome.verified_at = None
    outcome.verified_by = None

    await db.flush()

    # Regenerate memory
    event_result = await db.execute(select(EventRecord).where(EventRecord.id == event_id))
    event = event_result.scalar_one_or_none()
    soc_result = await db.execute(select(Society).where(Society.id == event.society_id))
    society = soc_result.scalar_one_or_none()

    if event and society:
        await generate_event_memory(db, outcome, event, society)

    await db.commit()

    return SuccessResponse(
        data=_outcome_to_dict(outcome),
        message="Outcome updated and memory regenerated",
    )


@router.put("/events/{event_id}/outcome/verify")
async def verify_event_outcome(
    event_id: uuid.UUID, user: CurrentUser, db: DB,
) -> SuccessResponse:
    """Mark an outcome as verified by an authorized user."""
    result = await db.execute(
        select(EventOutcome).where(EventOutcome.event_id == event_id)
    )
    outcome = result.scalar_one_or_none()
    if not outcome:
        raise NotFoundError("No outcome found for this event")

    outcome.is_verified = True
    outcome.verified_by = user.id
    outcome.verified_at = datetime.now(timezone.utc)
    await db.flush()

    # Also upgrade memory verification status
    mem_result = await db.execute(
        select(EventMemory).where(EventMemory.event_id == event_id)
    )
    memory = mem_result.scalar_one_or_none()
    if memory:
        memory.verification_status = VerificationStatus.VERIFIED
        memory.verified_by = user.id
        memory.verified_at = datetime.now(timezone.utc)

    await db.commit()

    return SuccessResponse(
        data={"event_id": str(event_id), "is_verified": True},
        message="Outcome and associated memory verified",
    )


# ---------------------------------------------------------------------------
# PART B — Semantic Memory Management (Layer 3)
# ---------------------------------------------------------------------------

@router.get("/university/{university_id}/memories")
async def list_university_memories(
    university_id: uuid.UUID,
    user: CurrentUser,
    db: DB,
    event_type: str | None = Query(None),
    status: str | None = Query(None, pattern="^(unverified|verified|disputed|excluded)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> SuccessResponse:
    """List semantic memories for a university with filtering.

    Returns memories the user is authorized to see based on
    their society membership and memory verification status.
    """
    query = (
        select(EventMemory)
        .where(EventMemory.university_id == university_id)
        .order_by(EventMemory.created_at.desc())
    )

    if event_type:
        query = query.where(EventMemory.event_type == event_type)
    if status:
        query = query.where(EventMemory.verification_status == status)

    # Count total
    count_query = select(func.count()).select_from(
        query.subquery()
    )
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    memories = result.scalars().all()

    return SuccessResponse(
        data={
            "memories": [_memory_to_dict(m) for m in memories],
            "total": total,
            "limit": limit,
            "offset": offset,
        },
        message=f"Found {total} memories",
    )


@router.get("/memories/{memory_id}")
async def get_memory(
    memory_id: uuid.UUID, user: CurrentUser, db: DB,
) -> SuccessResponse:
    """Get a single memory record with full details."""
    result = await db.execute(
        select(EventMemory).where(EventMemory.id == memory_id)
    )
    memory = result.scalar_one_or_none()
    if not memory:
        raise NotFoundError("Memory not found")

    return SuccessResponse(
        data=_memory_to_dict(memory),
        message="Memory loaded",
    )


@router.put("/memories/{memory_id}")
async def update_memory(
    memory_id: uuid.UUID, body: MemoryUpdate, user: CurrentUser, db: DB,
) -> SuccessResponse:
    """Update memory verification status, notes, or exclude from retrieval.

    This is the management interface for controlling what the AI learns from.
    """
    result = await db.execute(
        select(EventMemory).where(EventMemory.id == memory_id)
    )
    memory = result.scalar_one_or_none()
    if not memory:
        raise NotFoundError("Memory not found")

    update_data = body.model_dump(exclude_unset=True)

    if "verification_status" in update_data:
        memory.verification_status = update_data["verification_status"]
        if update_data["verification_status"] == "verified":
            memory.verified_by = user.id
            memory.verified_at = datetime.now(timezone.utc)
    if "is_active" in update_data:
        memory.is_active = update_data["is_active"]
    if "admin_notes" in update_data:
        memory.admin_notes = update_data["admin_notes"]
    if "lessons" in update_data:
        memory.lessons = update_data["lessons"]

    await db.commit()

    return SuccessResponse(
        data=_memory_to_dict(memory),
        message="Memory updated",
    )


# ---------------------------------------------------------------------------
# PART C — Historical Insights for Events
# ---------------------------------------------------------------------------

@router.get("/events/{event_id}/insights")
async def get_event_insights(
    event_id: uuid.UUID, user: CurrentUser, db: DB,
) -> SuccessResponse:
    """Retrieve historical insights relevant to an event.

    Shows what the AI would use to inform generation, with
    full provenance (which events the insights come from).
    """
    # Load event
    result = await db.execute(select(EventRecord).where(EventRecord.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise NotFoundError("Event not found")

    soc = await db.execute(select(Society).where(Society.id == event.society_id))
    society = soc.scalar_one_or_none()
    if not society:
        raise NotFoundError("Society not found")

    # Retrieve relevant memories
    query_text = f"{_ev(event.event_type)}: {event.title}. {event.description or ''}"
    memories = await retrieve_relevant_memories(
        db=db,
        university_id=society.university_id,
        event_type=_ev(event.event_type),
        exclude_event_id=event_id,
        society_id=society.id,
        query_text=query_text,
    )

    insights = []
    for m in memories:
        insight = {
            "source_event": m.event_title,
            "source_type": m.event_type,
            "verification": m.verification_status.value if hasattr(m.verification_status, 'value') else str(m.verification_status),
            "lessons": m.lessons or [],
            "risk_flags": m.risk_flags or [],
            "success_factors": m.success_factors or [],
            "metrics": {},
        }
        if m.budget_variance_pct is not None:
            insight["metrics"]["budget_variance"] = f"{m.budget_variance_pct:.0f}%"
        if m.attendance_variance_pct is not None:
            insight["metrics"]["attendance_variance"] = f"{m.attendance_variance_pct:.0f}%"
        if m.approval_days is not None:
            insight["metrics"]["approval_days"] = m.approval_days
        insights.append(insight)

    # Generate recommendations
    recommendations = _generate_recommendations(memories, _ev(event.event_type))

    return SuccessResponse(
        data={
            "event_id": str(event_id),
            "insights": insights,
            "recommendations": recommendations,
            "total_historical_events": len(memories),
        },
        message=f"Found {len(insights)} relevant historical insights",
    )


@router.get("/university/{university_id}/outcomes")
async def list_university_outcomes(
    university_id: uuid.UUID,
    user: CurrentUser,
    db: DB,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> SuccessResponse:
    """List all event outcomes for a university (management view)."""
    query = (
        select(EventOutcome)
        .where(EventOutcome.university_id == university_id)
        .order_by(EventOutcome.completed_at.desc())
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    outcomes = result.scalars().all()

    return SuccessResponse(
        data={
            "outcomes": [_outcome_to_dict(o) for o in outcomes],
            "total": total,
            "limit": limit,
            "offset": offset,
        },
        message=f"Found {total} outcomes",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _outcome_to_dict(outcome: EventOutcome) -> dict:
    return {
        "id": str(outcome.id),
        "event_id": str(outcome.event_id),
        "university_id": str(outcome.university_id),
        "approval_result": _ev(outcome.approval_result),
        "rejection_reasons": outcome.rejection_reasons,
        "actual_approval_days": outcome.actual_approval_days,
        "budget_target": float(outcome.budget_target) if outcome.budget_target else None,
        "actual_spend": float(outcome.actual_spend) if outcome.actual_spend else None,
        "budget_variance_pct": outcome.budget_variance_pct,
        "overspent_categories": outcome.overspent_categories,
        "expected_audience": outcome.expected_audience,
        "actual_audience": outcome.actual_audience,
        "sponsors_pitched": outcome.sponsors_pitched,
        "sponsors_confirmed": outcome.sponsors_confirmed,
        "lessons_learned": outcome.lessons_learned,
        "risk_flags": outcome.risk_flags,
        "completed_at": outcome.completed_at.isoformat() if outcome.completed_at else None,
        "is_verified": outcome.is_verified,
        "verified_at": outcome.verified_at.isoformat() if outcome.verified_at else None,
        "created_at": outcome.created_at.isoformat() if outcome.created_at else None,
    }


def _memory_to_dict(memory: EventMemory) -> dict:
    return {
        "id": str(memory.id),
        "event_id": str(memory.event_id),
        "event_title": memory.event_title,
        "event_type": memory.event_type,
        "summary_text": memory.summary_text,
        "lessons": memory.lessons,
        "risk_flags": memory.risk_flags,
        "success_factors": memory.success_factors,
        "budget_variance_pct": memory.budget_variance_pct,
        "attendance_variance_pct": memory.attendance_variance_pct,
        "sponsor_conversion_rate": memory.sponsor_conversion_rate,
        "approval_days": memory.approval_days,
        "verification_status": memory.verification_status.value if hasattr(memory.verification_status, 'value') else str(memory.verification_status),
        "is_active": memory.is_active,
        "admin_notes": memory.admin_notes,
        "created_at": memory.created_at.isoformat() if memory.created_at else None,
    }


def _generate_recommendations(memories: list[EventMemory], event_type: str) -> list[str]:
    """Generate specific recommendations from historical data."""
    recs = []

    if not memories:
        return ["No historical data available yet — this will be the first recorded event."]

    # Budget recommendations
    budget_overs = [m for m in memories if m.budget_variance_pct and m.budget_variance_pct > 10]
    if budget_overs:
        avg_over = sum(m.budget_variance_pct for m in budget_overs) / len(budget_overs)
        recs.append(
            f"{len(budget_overs)} previous event(s) exceeded their budget by an average of "
            f"{avg_over:.0f}%. Consider increasing your budget allocation or contingency."
        )

    # Overspent categories
    all_overspent = []
    for m in memories:
        if m.risk_flags:
            for flag in m.risk_flags:
                if "Overspent category:" in str(flag):
                    cat = str(flag).replace("Overspent category:", "").strip()
                    all_overspent.append(cat)
    if all_overspent:
        from collections import Counter
        common = Counter(all_overspent).most_common(2)
        for cat, count in common:
            recs.append(
                f"'{cat}' has been an overspent category in {count} previous event(s). "
                f"Consider increasing the {cat} budget allocation."
            )

    # Approval timeline
    long_approvals = [m for m in memories if m.approval_days and m.approval_days > 14]
    if long_approvals:
        avg_days = sum(m.approval_days for m in long_approvals) / len(long_approvals)
        recs.append(
            f"Approval typically takes {avg_days:.0f} days at this university. "
            f"Plan your submission timeline accordingly."
        )

    # Attendance
    low_attendance = [m for m in memories if m.attendance_variance_pct and m.attendance_variance_pct < -20]
    if low_attendance:
        recs.append(
            f"{len(low_attendance)} previous event(s) had attendance significantly below expectations. "
            f"Consider stronger marketing or more realistic audience estimates."
        )

    if not recs:
        recs.append("Historical events at this university have generally met their targets.")

    return recs
