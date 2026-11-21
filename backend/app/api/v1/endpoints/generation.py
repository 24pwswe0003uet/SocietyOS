"""Event generation endpoint — triggers orchestrator with SSE streaming."""

import json
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.core.dependencies import DB, CurrentUser
from app.core.exceptions import NotFoundError, ForbiddenError
from app.models.event import EventRecord
from app.models.society import SocietyMembership, MemberRole
from app.models.proposal import ProposalDoc
from app.models.budget import BudgetPlan
from app.models.sponsorship import SponsorshipPackage
from app.models.task import ApprovalStep, Task
from app.schemas.common import SuccessResponse
from app.services.agents.orchestrator import run_generation

router = APIRouter(prefix="/events", tags=["Generation"])


def _ev(val) -> str:
    return val.value if hasattr(val, "value") else str(val)


@router.post("/{event_id}/generate-all")
async def generate_all(
    event_id: uuid.UUID, user: CurrentUser, db: DB
) -> StreamingResponse:
    """Trigger full event package generation with SSE progress streaming."""
    result = await db.execute(select(EventRecord).where(EventRecord.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise NotFoundError("Event not found")

    mem_result = await db.execute(
        select(SocietyMembership).where(
            SocietyMembership.user_id == user.id,
            SocietyMembership.society_id == event.society_id,
            SocietyMembership.role.in_([
                MemberRole.PRESIDENT, MemberRole.ADMIN, MemberRole.EVENT_ORGANIZER
            ]),
        )
    )
    if not mem_result.scalars().first():
        raise ForbiddenError("You don't have permission to generate for this event")

    async def sse_stream():
        from app.db.session import async_session_factory
        async with async_session_factory() as gen_db:
            try:
                async for update in run_generation(event_id, gen_db):
                    data = json.dumps(update.to_dict())
                    yield f"data: {data}\n\n"
            except Exception as exc:
                data = json.dumps({"agent": "orchestrator", "status": "error", "message": str(exc)})
                yield f"data: {data}\n\n"

    return StreamingResponse(
        sse_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/{event_id}/proposal")
async def get_proposal(event_id: uuid.UUID, user: CurrentUser, db: DB) -> SuccessResponse:
    result = await db.execute(select(ProposalDoc).where(ProposalDoc.event_id == event_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError("No proposal generated yet")
    return SuccessResponse(
        data={"id": str(doc.id), "event_id": str(doc.event_id), "sections": doc.sections, "version": doc.version},
        message="Proposal retrieved",
    )


@router.get("/{event_id}/budget")
async def get_budget(event_id: uuid.UUID, user: CurrentUser, db: DB) -> SuccessResponse:
    result = await db.execute(select(BudgetPlan).where(BudgetPlan.event_id == event_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise NotFoundError("No budget generated yet")
    return SuccessResponse(
        data={"id": str(plan.id), "event_id": str(plan.event_id), "categories": plan.categories, "total_amount": plan.total_amount, "warnings": plan.warnings, "version": plan.version},
        message="Budget retrieved",
    )


@router.get("/{event_id}/sponsorship")
async def get_sponsorship(event_id: uuid.UUID, user: CurrentUser, db: DB) -> SuccessResponse:
    result = await db.execute(select(SponsorshipPackage).where(SponsorshipPackage.event_id == event_id))
    pkg = result.scalar_one_or_none()
    if not pkg:
        raise NotFoundError("No sponsorship package generated yet")
    return SuccessResponse(
        data={"id": str(pkg.id), "event_id": str(pkg.event_id), "tiers": pkg.tiers, "audience_summary": pkg.audience_summary, "email_drafts": pkg.email_drafts, "version": pkg.version},
        message="Sponsorship package retrieved",
    )


@router.put("/{event_id}/proposal")
async def update_proposal(event_id: uuid.UUID, body: dict, user: CurrentUser, db: DB) -> SuccessResponse:
    result = await db.execute(select(ProposalDoc).where(ProposalDoc.event_id == event_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError("No proposal to edit")
    if "sections" in body:
        doc.sections = body["sections"]
        doc.version += 1
    await db.flush()
    return SuccessResponse(data={"id": str(doc.id), "sections": doc.sections, "version": doc.version}, message=f"Proposal saved (version {doc.version})")


@router.put("/{event_id}/budget")
async def update_budget(event_id: uuid.UUID, body: dict, user: CurrentUser, db: DB) -> SuccessResponse:
    result = await db.execute(select(BudgetPlan).where(BudgetPlan.event_id == event_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise NotFoundError("No budget to edit")
    if "categories" in body:
        plan.categories = body["categories"]
    if "contingency_percent" in body:
        plan.contingency_percent = body["contingency_percent"]
    subtotal = sum(sum(item.get("total", 0) for item in cat.get("items", [])) for cat in plan.categories)
    contingency = subtotal * (plan.contingency_percent / 100)
    plan.total_amount = {"subtotal": subtotal, "contingency": contingency, "grand_total": subtotal + contingency, "currency": body.get("currency", "PKR")}
    warnings = []
    grand = subtotal + contingency
    if grand > 0:
        for cat in plan.categories:
            cat_total = cat.get("subtotal", sum(i.get("total", 0) for i in cat.get("items", [])))
            if cat_total / grand > 0.4:
                warnings.append(f"{cat['name']} exceeds 40% of total budget ({cat_total / grand * 100:.0f}%)")
    plan.warnings = warnings
    plan.version += 1
    await db.flush()
    return SuccessResponse(data={"id": str(plan.id), "categories": plan.categories, "total_amount": plan.total_amount, "warnings": plan.warnings, "version": plan.version}, message=f"Budget saved (version {plan.version})")


@router.put("/{event_id}/sponsorship")
async def update_sponsorship(event_id: uuid.UUID, body: dict, user: CurrentUser, db: DB) -> SuccessResponse:
    result = await db.execute(select(SponsorshipPackage).where(SponsorshipPackage.event_id == event_id))
    pkg = result.scalar_one_or_none()
    if not pkg:
        raise NotFoundError("No sponsorship package to edit")
    if "tiers" in body:
        pkg.tiers = body["tiers"]
    if "audience_summary" in body:
        pkg.audience_summary = body["audience_summary"]
    if "email_drafts" in body:
        pkg.email_drafts = body["email_drafts"]
    pkg.version += 1
    await db.flush()
    return SuccessResponse(data={"id": str(pkg.id), "tiers": pkg.tiers, "version": pkg.version}, message=f"Sponsorship saved (version {pkg.version})")


@router.get("/{event_id}/approvals")
async def get_approvals(event_id: uuid.UUID, user: CurrentUser, db: DB) -> SuccessResponse:
    result = await db.execute(select(ApprovalStep).where(ApprovalStep.event_id == event_id).order_by(ApprovalStep.step_order))
    steps = result.scalars().all()
    return SuccessResponse(
        data=[{"id": str(s.id), "step_order": s.step_order, "authority": s.authority,
               "role": s.role, "deadline": s.deadline.isoformat() if s.deadline else None,
               "required_documents": s.required_documents, "status": _ev(s.status), "notes": s.notes} for s in steps],
        message="Approval steps retrieved",
    )


@router.get("/{event_id}/tasks")
async def get_tasks(event_id: uuid.UUID, user: CurrentUser, db: DB) -> SuccessResponse:
    result = await db.execute(select(Task).where(Task.event_id == event_id).order_by(Task.due_date))
    tasks = result.scalars().all()
    return SuccessResponse(
        data=[{"id": str(t.id), "title": t.title, "description": t.description,
               "team": t.team, "assigned_to": t.assigned_to,
               "due_date": t.due_date.isoformat() if t.due_date else None,
               "priority": _ev(t.priority), "status": _ev(t.status), "dependencies": t.dependencies} for t in tasks],
        message="Tasks retrieved",
    )
