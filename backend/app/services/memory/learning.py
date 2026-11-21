"""Learning loop — post-event analysis, summary generation, and memory storage.

When an event is completed:
1. Collect actual event results (from EventOutcome)
2. Compare planned vs actual outcomes
3. Generate structured post-event summary (AI or fallback)
4. Identify successful decisions and mistakes
5. Save EventOutcome (already done by endpoint)
6. Generate and store semantic memory embedding
7. Make verified lessons available to future generation
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import EventRecord
from app.models.event_outcome import EventOutcome
from app.models.event_memory import EventMemory, VerificationStatus
from app.models.society import Society
from app.services.memory.embedding import generate_embedding
from app.services.ai.gemini import gemini_provider

logger = logging.getLogger("societyos.memory.learning")


def _ev(val) -> str:
    """Safely extract enum value or return string as-is."""
    return val.value if hasattr(val, 'value') else str(val)


async def generate_event_memory(
    db: AsyncSession,
    outcome: EventOutcome,
    event: EventRecord,
    society: Society,
) -> EventMemory | None:
    """Generate a semantic memory record from a completed event outcome.

    This is the core of the learning loop — it creates a structured summary
    of what happened, generates an embedding, and stores it for future retrieval.
    """
    try:
        # Helper to safely extract enum value
        def _enum_val(v):
            return v.value if hasattr(v, 'value') else str(v)

        # 1. Build structured analysis
        analysis = _analyze_outcome(outcome, event)

        # 2. Generate AI summary or fallback
        summary_text = await _generate_summary(event, outcome, analysis)

        # 3. Extract lessons
        lessons = await _extract_lessons(event, outcome, analysis)

        # 4. Generate embedding from summary
        event_type_str = _enum_val(event.event_type)
        embedding_text = (
            f"{event_type_str} event: {event.title}. "
            f"{summary_text} "
            f"Lessons: {'; '.join(lessons[:5])}"
        )
        embedding = await generate_embedding(embedding_text)

        # 5. Check for existing memory (idempotent)
        existing = await db.execute(
            select(EventMemory).where(EventMemory.event_id == event.id)
        )
        old = existing.scalar_one_or_none()
        if old:
            # Update existing
            old.summary_text = summary_text
            old.lessons = lessons
            old.risk_flags = analysis.get("risk_flags", [])
            old.success_factors = analysis.get("success_factors", [])
            old.budget_variance_pct = outcome.budget_variance_pct
            old.attendance_variance_pct = analysis.get("attendance_variance_pct")
            old.sponsor_conversion_rate = analysis.get("sponsor_conversion_rate")
            old.approval_days = outcome.actual_approval_days
            old.embedding = embedding
            logger.info("Updated existing memory for event %s", event.id)
            return old

        # 6. Create new memory
        memory = EventMemory(
            event_id=event.id,
            outcome_id=outcome.id,
            university_id=outcome.university_id,
            society_id=event.society_id,
            event_type=event_type_str,
            event_title=event.title,
            summary_text=summary_text,
            lessons=lessons,
            risk_flags=analysis.get("risk_flags", []),
            success_factors=analysis.get("success_factors", []),
            budget_variance_pct=outcome.budget_variance_pct,
            attendance_variance_pct=analysis.get("attendance_variance_pct"),
            sponsor_conversion_rate=analysis.get("sponsor_conversion_rate"),
            approval_days=outcome.actual_approval_days,
            embedding=embedding,
            verification_status="unverified",
            is_active=True,
        )
        db.add(memory)
        logger.info("Created memory for event %s", event.id)
        return memory

    except Exception as e:
        logger.error("Failed to generate event memory: %s", e)
        return None


def _analyze_outcome(outcome: EventOutcome, event: EventRecord) -> dict:
    """Compare planned vs actual outcomes and identify patterns."""
    analysis = {
        "risk_flags": list(outcome.risk_flags or []),
        "success_factors": [],
    }

    # Budget analysis
    if outcome.budget_variance_pct is not None:
        if outcome.budget_variance_pct > 20:
            analysis["risk_flags"].append(
                f"Budget exceeded by {outcome.budget_variance_pct:.0f}%"
            )
            if outcome.overspent_categories:
                for cat in outcome.overspent_categories:
                    analysis["risk_flags"].append(f"Overspent category: {cat}")
        elif outcome.budget_variance_pct < -10:
            analysis["success_factors"].append(
                f"Came in {abs(outcome.budget_variance_pct):.0f}% under budget"
            )
        else:
            analysis["success_factors"].append("Budget was well-managed")

    # Attendance analysis
    if outcome.expected_audience and outcome.actual_audience:
        att_var = ((outcome.actual_audience - outcome.expected_audience) / outcome.expected_audience) * 100
        analysis["attendance_variance_pct"] = att_var
        if att_var > 20:
            analysis["success_factors"].append(
                f"Attendance exceeded expectations by {att_var:.0f}%"
            )
        elif att_var < -30:
            analysis["risk_flags"].append(
                f"Attendance was {abs(att_var):.0f}% below expected"
            )

    # Sponsorship analysis
    if outcome.sponsors_pitched and outcome.sponsors_pitched > 0:
        confirmed = outcome.sponsors_confirmed or 0
        rate = (confirmed / outcome.sponsors_pitched) * 100
        analysis["sponsor_conversion_rate"] = rate
        if rate >= 50:
            analysis["success_factors"].append(
                f"Strong sponsor conversion rate: {rate:.0f}%"
            )
        elif rate < 20:
            analysis["risk_flags"].append(
                f"Low sponsor conversion: {rate:.0f}%"
            )

    # Approval analysis
    if outcome.actual_approval_days is not None:
        if outcome.actual_approval_days > 30:
            analysis["risk_flags"].append(
                f"Approval took {outcome.actual_approval_days} days — longer than typical"
            )
        elif outcome.actual_approval_days <= 7:
            analysis["success_factors"].append(
                f"Quick approval in {outcome.actual_approval_days} days"
            )

    # Approval result
    if _ev(outcome.approval_result) == "rejected":
        analysis["risk_flags"].append("Event was rejected")
        if outcome.rejection_reasons:
            for reason in outcome.rejection_reasons[:3]:
                analysis["risk_flags"].append(f"Rejection reason: {reason}")

    return analysis


async def _generate_summary(
    event: EventRecord, outcome: EventOutcome, analysis: dict
) -> str:
    """Generate a structured text summary using AI or fallback."""
    prompt = f"""Summarize this completed university event in 3-4 sentences for institutional memory:

Event: {event.title} ({_ev(event.event_type)})
Approval: {_ev(outcome.approval_result)}
Budget target: {outcome.budget_target}, Actual spend: {outcome.actual_spend}
Budget variance: {outcome.budget_variance_pct:.1f}% {'over' if (outcome.budget_variance_pct or 0) > 0 else 'under'} budget
Expected attendance: {outcome.expected_audience}, Actual: {outcome.actual_audience}
Sponsors pitched: {outcome.sponsors_pitched}, Confirmed: {outcome.sponsors_confirmed}
Approval took: {outcome.actual_approval_days} days
Lessons: {outcome.lessons_learned or 'None recorded'}
Risk flags: {', '.join(analysis.get('risk_flags', [])) or 'None'}
Success factors: {', '.join(analysis.get('success_factors', [])) or 'None'}

Write a concise factual summary focused on what future event planners should know.
Do not include opinions or recommendations — just the facts."""

    try:
        summary = await gemini_provider.generate_text(
            prompt=prompt, max_tokens=500, temperature=0.2,
        )
        return summary.strip()
    except Exception as e:
        logger.warning("AI summary generation failed: %s — using fallback", e)
        return _fallback_summary(event, outcome, analysis)


def _fallback_summary(
    event: EventRecord, outcome: EventOutcome, analysis: dict
) -> str:
    """Generate a structured summary without AI."""
    parts = [
        f"{event.title} ({_ev(event.event_type)}) — {_ev(outcome.approval_result)}."
    ]
    if outcome.budget_variance_pct is not None:
        direction = "over" if outcome.budget_variance_pct > 0 else "under"
        parts.append(f"Budget was {abs(outcome.budget_variance_pct):.0f}% {direction} target.")
    if outcome.actual_audience and outcome.expected_audience:
        if outcome.actual_audience > outcome.expected_audience:
            parts.append(f"Attendance ({outcome.actual_audience}) exceeded the {outcome.expected_audience} expected.")
        else:
            parts.append(f"Attendance ({outcome.actual_audience}) fell short of {outcome.expected_audience} expected.")
    if outcome.sponsors_confirmed and outcome.sponsors_pitched:
        parts.append(f"Secured {outcome.sponsors_confirmed} of {outcome.sponsors_pitched} sponsors pitched.")
    if outcome.lessons_learned:
        parts.append(f"Key takeaway: {outcome.lessons_learned[:200]}")
    return " ".join(parts)


async def _extract_lessons(
    event: EventRecord, outcome: EventOutcome, analysis: dict
) -> list[str]:
    """Extract actionable lessons from the outcome."""
    lessons = []

    # From user-provided lessons
    if outcome.lessons_learned:
        lessons.append(outcome.lessons_learned)

    # From analysis
    for flag in analysis.get("risk_flags", []):
        lessons.append(f"Watch out: {flag}")

    for factor in analysis.get("success_factors", []):
        lessons.append(f"What worked: {factor}")

    # Specific actionable insights
    if outcome.overspent_categories:
        for cat in outcome.overspent_categories:
            lessons.append(f"Consider increasing {cat} budget allocation")

    if outcome.budget_variance_pct and outcome.budget_variance_pct > 20:
        lessons.append("Build in a larger contingency buffer for this type of event")

    if outcome.actual_approval_days and outcome.actual_approval_days > 21:
        lessons.append(f"Start approval process earlier — this event took {outcome.actual_approval_days} days")

    return lessons[:10]  # Cap at 10 lessons
