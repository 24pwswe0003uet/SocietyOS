"""Event dashboard, task CRUD, approval updates, and sharing endpoints."""

import secrets
import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Body
from sqlalchemy import select

from app.core.dependencies import DB, CurrentUser
from app.core.exceptions import NotFoundError, ForbiddenError, BadRequestError
from app.models.event import EventRecord
from app.models.society import Society, SocietyMembership
from app.models.university import University
from app.models.proposal import ProposalDoc
from app.models.budget import BudgetPlan
from app.models.sponsorship import SponsorshipPackage
from app.models.task import ApprovalStep, Task
from app.models.event_outcome import EventOutcome
from app.schemas.common import SuccessResponse

router = APIRouter(tags=["Dashboard"])


def _ev(val) -> str:
    """Safely get enum value or return string."""
    return val.value if hasattr(val, 'value') else str(val)

# In-memory share tokens (production: use a DB table)
_share_tokens: dict[str, uuid.UUID] = {}


# ---------------------------------------------------------------------------
# PART A — Full Dashboard
# ---------------------------------------------------------------------------
@router.get("/events/{event_id}/dashboard")
async def get_event_dashboard(
    event_id: uuid.UUID, user: CurrentUser, db: DB
) -> SuccessResponse:
    """Comprehensive dashboard: event info, approvals, tasks, budget, sponsors."""
    event, society, university = await _load_event_full(event_id, db)

    # Proposal/Budget/Sponsorship existence
    has_proposal = (await db.execute(select(ProposalDoc.id).where(ProposalDoc.event_id == event_id))).scalar_one_or_none() is not None
    has_budget = (await db.execute(select(BudgetPlan.id).where(BudgetPlan.event_id == event_id))).scalar_one_or_none() is not None
    has_sponsorship = (await db.execute(select(SponsorshipPackage.id).where(SponsorshipPackage.event_id == event_id))).scalar_one_or_none() is not None

    # Budget data
    budget_data = None
    if has_budget:
        bud = (await db.execute(select(BudgetPlan).where(BudgetPlan.event_id == event_id))).scalar_one()
        budget_data = {
            "planned": float(event.budget_target) if event.budget_target else 0,
            "allocated": sum(c.get("subtotal", 0) for c in (bud.categories or [])),
            "currency": event.currency,
            "categories": [{"name": c["name"], "amount": c.get("subtotal", 0)} for c in (bud.categories or [])],
            "warnings": bud.warnings or [],
        }

    # Approval steps
    approvals_result = await db.execute(
        select(ApprovalStep).where(ApprovalStep.event_id == event_id).order_by(ApprovalStep.step_order)
    )
    approval_steps = approvals_result.scalars().all()
    today = date.today()

    approval_data = []
    for s in approval_steps:
        status_val = _ev(s.status)
        rag = "amber"  # default: pending
        if status_val == "approved":
            rag = "green"
        elif status_val == "rejected" or status_val == "overdue":
            rag = "red"
        elif s.deadline and s.deadline < today and status_val == "pending":
            rag = "red"  # overdue
        approval_data.append({
            "id": str(s.id), "step_order": s.step_order, "authority": s.authority,
            "role": s.role, "deadline": s.deadline.isoformat() if s.deadline else None,
            "required_documents": s.required_documents, "status": status_val,
            "rag": rag, "notes": s.notes,
        })

    # Tasks
    tasks_result = await db.execute(select(Task).where(Task.event_id == event_id).order_by(Task.due_date))
    all_tasks = tasks_result.scalars().all()
    task_data = [{
        "id": str(t.id), "title": t.title, "description": t.description,
        "team": t.team, "assigned_to": t.assigned_to,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "priority": _ev(t.priority), "status": _ev(t.status),
        "dependencies": t.dependencies,
        "overdue": bool(t.due_date and t.due_date < today and _ev(t.status) not in ("completed", "review")),
    } for t in all_tasks]

    tasks_by_status = {}
    for t in task_data:
        tasks_by_status.setdefault(t["status"], []).append(t)

    # Upcoming deadlines (next 7 days)
    upcoming = []
    for s in approval_steps:
        if s.deadline and today <= s.deadline <= date(today.year, today.month, today.day + 7 if today.day < 25 else today.day):
            upcoming.append({"type": "approval", "title": s.authority, "date": s.deadline.isoformat()})
    for t in all_tasks:
        if t.due_date and today <= t.due_date and _ev(t.status) not in ("completed",):
            upcoming.append({"type": "task", "title": t.title, "date": t.due_date.isoformat()})
    upcoming.sort(key=lambda x: x["date"])

    return SuccessResponse(
        data={
            "event": {
                "id": str(event.id), "title": event.title, "status": _ev(event.status),
                "event_type": _ev(event.event_type),
                "event_date": event.event_date.isoformat() if event.event_date else None,
                "description": event.description,
                "budget_target": float(event.budget_target) if event.budget_target else None,
                "currency": event.currency, "audience_size": event.audience_size,
            },
            "society": {"id": str(society.id), "name": society.name} if society else None,
            "university": {"name": university.name} if university else None,
            "documents": {"has_proposal": has_proposal, "has_budget": has_budget, "has_sponsorship": has_sponsorship},
            "budget": budget_data,
            "approvals": {
                "total": len(approval_data),
                "approved": sum(1 for a in approval_data if a["status"] == "approved"),
                "steps": approval_data,
            },
            "tasks": {
                "total": len(task_data),
                "completed": sum(1 for t in task_data if t["status"] == "completed"),
                "overdue": sum(1 for t in task_data if t.get("overdue")),
                "by_status": {k: len(v) for k, v in tasks_by_status.items()},
                "items": task_data,
            },
            "upcoming_deadlines": upcoming[:10],
        },
        message="Dashboard loaded",
    )


# ---------------------------------------------------------------------------
# PART B — Approval status updates
# ---------------------------------------------------------------------------
@router.put("/events/{event_id}/approvals/{step_id}")
async def update_approval_step(
    event_id: uuid.UUID, step_id: uuid.UUID, body: dict,
    user: CurrentUser, db: DB,
) -> SuccessResponse:
    """Update an approval step's status or notes."""
    result = await db.execute(
        select(ApprovalStep).where(ApprovalStep.id == step_id, ApprovalStep.event_id == event_id)
    )
    step = result.scalar_one_or_none()
    if not step:
        raise NotFoundError("Approval step not found")

    allowed_statuses = {"pending", "submitted", "approved", "rejected"}
    if "status" in body:
        if body["status"] not in allowed_statuses:
            raise BadRequestError(f"Invalid status. Allowed: {allowed_statuses}")
        step.status = body["status"]
    if "notes" in body:
        step.notes = body["notes"]

    await db.flush()
    return SuccessResponse(
        data={"id": str(step.id), "status": _ev(step.status), "notes": step.notes},
        message="Approval step updated",
    )


# ---------------------------------------------------------------------------
# PART C — Task CRUD
# ---------------------------------------------------------------------------
@router.post("/events/{event_id}/tasks")
async def create_task(
    event_id: uuid.UUID, body: dict, user: CurrentUser, db: DB,
) -> SuccessResponse:
    """Create a new task on the event's task board."""
    result = await db.execute(select(EventRecord).where(EventRecord.id == event_id))
    if not result.scalar_one_or_none():
        raise NotFoundError("Event not found")

    due = None
    if body.get("due_date"):
        try:
            due = date.fromisoformat(body["due_date"])
        except (ValueError, TypeError):
            pass

    task = Task(
        event_id=event_id,
        title=body.get("title", "Untitled task"),
        description=body.get("description", ""),
        team=body.get("team", "General"),
        assigned_to=body.get("assigned_to"),
        due_date=due,
        priority=body.get("priority", "medium"),
        status="todo",
        dependencies=body.get("dependencies", []),
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)

    return SuccessResponse(
        data={"id": str(task.id), "title": task.title, "status": _ev(task.status)},
        message="Task created",
    )


@router.put("/events/{event_id}/tasks/{task_id}")
async def update_task(
    event_id: uuid.UUID, task_id: uuid.UUID, body: dict,
    user: CurrentUser, db: DB,
) -> SuccessResponse:
    """Update a task's status, assignment, priority, or other fields."""
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.event_id == event_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundError("Task not found")

    for field in ("title", "description", "team", "assigned_to", "priority", "status"):
        if field in body:
            setattr(task, field, body[field])
    if "due_date" in body:
        try:
            task.due_date = date.fromisoformat(body["due_date"]) if body["due_date"] else None
        except (ValueError, TypeError):
            pass

    await db.flush()
    await db.refresh(task)
    return SuccessResponse(
        data={
            "id": str(task.id), "title": task.title, "status": _ev(task.status),
            "assigned_to": task.assigned_to, "priority": _ev(task.priority),
        },
        message="Task updated",
    )


# ---------------------------------------------------------------------------
# PART H — Sharing links
# ---------------------------------------------------------------------------
@router.post("/events/{event_id}/share")
async def create_share_link(
    event_id: uuid.UUID, user: CurrentUser, db: DB,
) -> SuccessResponse:
    """Generate a read-only share token for faculty advisors."""
    result = await db.execute(select(EventRecord).where(EventRecord.id == event_id))
    if not result.scalar_one_or_none():
        raise NotFoundError("Event not found")

    token = secrets.token_urlsafe(32)
    _share_tokens[token] = event_id

    return SuccessResponse(
        data={"token": token, "event_id": str(event_id)},
        message="Share link created",
    )


@router.get("/shared/{token}")
async def get_shared_dashboard(token: str, db: DB) -> SuccessResponse:
    """Read-only dashboard view via share token (no auth required)."""
    event_id = _share_tokens.get(token)
    if not event_id:
        raise NotFoundError("Invalid or expired share link")

    result = await db.execute(select(EventRecord).where(EventRecord.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise NotFoundError("Event not found")

    # Return limited data
    approvals = await db.execute(
        select(ApprovalStep).where(ApprovalStep.event_id == event_id).order_by(ApprovalStep.step_order)
    )
    steps = approvals.scalars().all()

    tasks = await db.execute(select(Task).where(Task.event_id == event_id))
    all_tasks = tasks.scalars().all()

    return SuccessResponse(
        data={
            "event": {"title": event.title, "status": _ev(event.status), "event_date": event.event_date.isoformat() if event.event_date else None},
            "approvals": [{"authority": s.authority, "status": _ev(s.status), "deadline": s.deadline.isoformat() if s.deadline else None} for s in steps],
            "tasks_summary": {"total": len(all_tasks), "completed": sum(1 for t in all_tasks if _ev(t.status) == "completed")},
            "read_only": True,
        },
        message="Shared dashboard (read-only)",
    )


@router.delete("/events/{event_id}/share/{token}")
async def revoke_share_link(
    event_id: uuid.UUID, token: str, user: CurrentUser, db: DB,
) -> SuccessResponse:
    """Revoke a share token."""
    if token in _share_tokens and _share_tokens[token] == event_id:
        del _share_tokens[token]
        return SuccessResponse(data={}, message="Share link revoked")
    raise NotFoundError("Share token not found")


# ---------------------------------------------------------------------------
# Post-event outcome (legacy — redirects to memory endpoint)
# ---------------------------------------------------------------------------
@router.post("/events/{event_id}/outcome")
async def submit_outcome(
    event_id: uuid.UUID, body: dict, user: CurrentUser, db: DB,
) -> SuccessResponse:
    """Submit post-event outcome data. (Legacy — prefer POST /memory/events/{id}/outcome)."""
    from app.schemas.outcome import OutcomeCreate
    from app.api.v1.endpoints.memory import submit_event_outcome
    validated = OutcomeCreate(**body)
    return await submit_event_outcome(event_id, validated, user, db)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _load_event_full(event_id, db):
    result = await db.execute(select(EventRecord).where(EventRecord.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise NotFoundError("Event not found")
    soc = await db.execute(select(Society).where(Society.id == event.society_id))
    society = soc.scalar_one_or_none()
    uni = None
    if society:
        u = await db.execute(select(University).where(University.id == society.university_id))
        uni = u.scalar_one_or_none()
    return event, society, uni
