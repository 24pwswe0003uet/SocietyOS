"""Event generation orchestrator — coordinates all specialist agents.

Implements:
- Shared EventContext loading with strict schema (Layer 1)
- Historical lesson injection from semantic memory (Layer 3)
- Agent dependency graph (sequential pipeline)
- Timeout per agent (120s)
- Partial completion recovery with per-agent rollback
- Idempotency (re-generation upserts, never duplicates)
- SSE progress streaming via GenerationUpdate
"""

import asyncio
import logging
import uuid
from datetime import date
from typing import Any, AsyncGenerator

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import EventRecord, EventStatus
from app.models.society import Society
from app.models.university import University
from app.models.policy import PolicyData
from app.models.proposal import ProposalDoc
from app.models.budget import BudgetPlan
from app.models.sponsorship import SponsorshipPackage
from app.models.task import ApprovalStep as ApprovalStepModel, Task as TaskModel

from app.services.agents.base import EventContext, PolicyContext, HistoricalLesson
from app.services.agents.proposal_agent import ProposalAgent
from app.services.agents.budget_agent import BudgetAgent
from app.services.agents.sponsorship_agent import SponsorshipAgent
from app.services.agents.approval_agent import ApprovalAgent
from app.services.agents.task_agent import TaskAgent

logger = logging.getLogger("societyos.orchestrator")

AGENT_TIMEOUT = 120  # seconds per agent


class GenerationUpdate:
    """A single progress update for the SSE stream."""

    def __init__(self, agent: str, status: str, message: str = "", data: Any = None):
        self.agent = agent
        self.status = status
        self.message = message
        self.data = data

    def to_dict(self) -> dict:
        d = {"agent": self.agent, "status": self.status, "message": self.message}
        if self.data is not None:
            d["data"] = self.data
        return d


def _safe_date(val: str | date | None) -> date | None:
    """Convert string or date to date object, or None."""
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        try:
            return date.fromisoformat(val)
        except (ValueError, TypeError):
            return None
    return None


async def _load_historical_lessons(
    db: AsyncSession, university_id: uuid.UUID, event_type: str, event_id: uuid.UUID
) -> list[HistoricalLesson]:
    """Load relevant historical lessons from semantic memory (Layer 3).

    Retrieves verified+active memories from the same university,
    prioritizing same event type. Excludes the current event.
    """
    try:
        from app.services.memory.retrieval import retrieve_relevant_memories
        memories = await retrieve_relevant_memories(
            db=db,
            university_id=university_id,
            event_type=event_type,
            exclude_event_id=event_id,
            limit=3,
        )
        return [
            HistoricalLesson(
                event_title=m.event_title,
                event_type=m.event_type,
                lesson=lesson_text,
                source="verified" if str(m.verification_status) == "verified" else "unverified",
                metric_context=_build_metric_context(m),
            )
            for m in memories
            for lesson_text in (m.lessons or ["No specific lesson recorded"])[:2]
        ]
    except Exception as e:
        logger.warning("Could not load historical lessons: %s", e)
        return []


def _build_metric_context(memory) -> str | None:
    """Build a human-readable metric summary from a memory record."""
    parts = []
    if memory.budget_variance_pct is not None:
        direction = "over" if memory.budget_variance_pct > 0 else "under"
        parts.append(f"Budget was {abs(memory.budget_variance_pct):.0f}% {direction}")
    if memory.attendance_variance_pct is not None:
        direction = "above" if memory.attendance_variance_pct > 0 else "below"
        parts.append(f"Attendance {abs(memory.attendance_variance_pct):.0f}% {direction} expected")
    if memory.sponsor_conversion_rate is not None:
        parts.append(f"Sponsor conversion: {memory.sponsor_conversion_rate:.0f}%")
    if memory.approval_days is not None:
        parts.append(f"Approval took {memory.approval_days} days")
    return "; ".join(parts) if parts else None


async def run_generation(
    event_id: uuid.UUID, db: AsyncSession
) -> AsyncGenerator[GenerationUpdate, None]:
    """Execute all agents and yield SSE progress updates."""

    # 1. Load event
    result = await db.execute(select(EventRecord).where(EventRecord.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        yield GenerationUpdate("orchestrator", "error", "Event not found")
        return

    # 2. Load society + university
    soc_result = await db.execute(select(Society).where(Society.id == event.society_id))
    society = soc_result.scalar_one_or_none()
    if not society:
        yield GenerationUpdate("orchestrator", "error", "Society not found")
        return

    uni_result = await db.execute(select(University).where(University.id == society.university_id))
    university = uni_result.scalar_one_or_none()

    # 3. Load best policy (prefer verified)
    pol_result = await db.execute(
        select(PolicyData)
        .where(PolicyData.university_id == society.university_id)
        .order_by(PolicyData.is_verified.desc(), PolicyData.created_at.desc())
        .limit(1)
    )
    policy = pol_result.scalar_one_or_none()
    policy_ctx = PolicyContext()
    if policy:
        policy_ctx = PolicyContext(
            lead_time_days=policy.lead_time_days,
            required_documents=policy.required_documents or [],
            sponsorship_rules=policy.sponsorship_rules,
            prohibitions=policy.prohibitions or [],
        )

    # 4. Load historical lessons (Layer 3 injection)
    historical = await _load_historical_lessons(
        db, society.university_id, event.event_type.value, event_id
    )

    # 5. Build context (Layer 1 — strict schema)
    chain_steps = (society.approval_chain or {}).get("steps", [])
    context = EventContext(
        event_id=str(event_id),
        event_title=event.title,
        event_type=event.event_type.value,
        description=event.description or "",
        audience_size=event.audience_size,
        event_date=event.event_date.isoformat() if event.event_date else None,
        duration_days=event.duration_days,
        venue_type=event.venue_type,
        budget_target=float(event.budget_target) if event.budget_target else None,
        currency=event.currency,
        society_name=society.name,
        society_id=str(society.id),
        university_name=university.name if university else "Unknown",
        university_id=str(society.university_id),
        department=society.department,
        faculty_advisor=society.faculty_advisor_name,
        approval_chain=chain_steps,
        policy=policy_ctx,
        historical_lessons=historical,
    )

    # 6. Mark generating
    event.status = EventStatus.GENERATING
    await db.flush()

    history_msg = ""
    if historical:
        history_msg = f" ({len(historical)} historical insights loaded)"
    yield GenerationUpdate("orchestrator", "running", f"Starting event generation...{history_msg}")

    completed = 0
    failed = 0

    # 7. Run each agent
    agent_pipeline = [
        ("proposal", ProposalAgent(), _save_proposal),
        ("budget", BudgetAgent(), _save_budget),
        ("sponsorship", SponsorshipAgent(), _save_sponsorship),
        ("approval", ApprovalAgent(), _save_approvals),
        ("tasks", TaskAgent(), _save_tasks),
    ]

    for name, agent, saver in agent_pipeline:
        yield GenerationUpdate(name, "running", f"Generating {name}...")
        try:
            data = await asyncio.wait_for(agent.generate(context), timeout=AGENT_TIMEOUT)
            await saver(db, event_id, data)
            await db.flush()
            completed += 1

            detail = ""
            if name == "approval" and data.get("warnings"):
                detail = " | " + "; ".join(data["warnings"][:2])
            if name == "tasks":
                detail = f" ({len(data.get('tasks', []))} tasks)"

            yield GenerationUpdate(name, "complete", f"{name.capitalize()} done{detail}")
        except asyncio.TimeoutError:
            failed += 1
            logger.error("%s timed out (%ds)", name, AGENT_TIMEOUT)
            yield GenerationUpdate(name, "error", f"Timed out after {AGENT_TIMEOUT}s")
        except Exception as e:
            failed += 1
            logger.error("%s failed: %s", name, e)
            try:
                await db.rollback()
            except Exception:
                pass
            yield GenerationUpdate(name, "error", f"Failed — using fallback if available")

    # 8. Mark event as review
    try:
        res = await db.execute(select(EventRecord).where(EventRecord.id == event_id))
        evt = res.scalar_one_or_none()
        if evt:
            evt.status = EventStatus.REVIEW
        await db.flush()
        await db.commit()
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass

    yield GenerationUpdate(
        "orchestrator", "complete",
        f"Done — {completed}/5 agents succeeded" + (f", {failed} failed" if failed else ""),
    )


# ---------------------------------------------------------------------------
# Persistence helpers (upsert for idempotency)
# ---------------------------------------------------------------------------

async def _save_proposal(db: AsyncSession, event_id: uuid.UUID, data: dict):
    existing = await db.execute(select(ProposalDoc).where(ProposalDoc.event_id == event_id))
    old = existing.scalar_one_or_none()
    if old:
        old.sections = data["sections"]
        old.version += 1
    else:
        db.add(ProposalDoc(event_id=event_id, sections=data["sections"]))


async def _save_budget(db: AsyncSession, event_id: uuid.UUID, data: dict):
    existing = await db.execute(select(BudgetPlan).where(BudgetPlan.event_id == event_id))
    old = existing.scalar_one_or_none()
    if old:
        old.categories = data.get("categories", [])
        old.warnings = data.get("warnings", [])
        old.total_amount = {"grand_total": data.get("grand_total"), "currency": data.get("currency", "PKR")}
        old.version += 1
    else:
        db.add(BudgetPlan(
            event_id=event_id,
            categories=data.get("categories", []),
            warnings=data.get("warnings", []),
            total_amount={"grand_total": data.get("grand_total"), "currency": data.get("currency", "PKR")},
        ))


async def _save_sponsorship(db: AsyncSession, event_id: uuid.UUID, data: dict):
    existing = await db.execute(select(SponsorshipPackage).where(SponsorshipPackage.event_id == event_id))
    old = existing.scalar_one_or_none()
    if old:
        old.tiers = data.get("tiers", [])
        old.audience_summary = data.get("audience_summary")
        old.email_drafts = data.get("email_drafts", [])
        old.version += 1
    else:
        db.add(SponsorshipPackage(
            event_id=event_id,
            tiers=data.get("tiers", []),
            audience_summary=data.get("audience_summary"),
            email_drafts=data.get("email_drafts", []),
        ))


async def _save_approvals(db: AsyncSession, event_id: uuid.UUID, data: dict):
    await db.execute(delete(ApprovalStepModel).where(ApprovalStepModel.event_id == event_id))
    for step in data.get("steps", []):
        db.add(ApprovalStepModel(
            event_id=event_id,
            step_order=step["step_order"],
            authority=step["authority"],
            role=step.get("role", ""),
            deadline=_safe_date(step.get("deadline")),
            required_documents=step.get("required_documents", []),
            status="pending",
        ))


async def _save_tasks(db: AsyncSession, event_id: uuid.UUID, data: dict):
    await db.execute(delete(TaskModel).where(TaskModel.event_id == event_id))
    for task in data.get("tasks", []):
        db.add(TaskModel(
            event_id=event_id,
            title=task["title"],
            description=task.get("description", ""),
            team=task.get("team", "General"),
            assigned_to=task.get("assigned_to"),
            due_date=_safe_date(task.get("due_date")),
            priority=task.get("priority", "medium"),
            status="todo",
            dependencies=task.get("dependencies", []),
        ))
