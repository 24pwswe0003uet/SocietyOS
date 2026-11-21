"""Document export endpoints — PDF, DOCX, XLSX."""

import uuid

from fastapi import APIRouter
from fastapi.responses import Response
from sqlalchemy import select

from app.core.dependencies import DB, CurrentUser
from app.core.exceptions import NotFoundError, BadRequestError
from app.models.event import EventRecord
from app.models.society import Society
from app.models.university import University
from app.models.proposal import ProposalDoc
from app.models.budget import BudgetPlan
from app.models.sponsorship import SponsorshipPackage
from app.services.documents.pdf_service import generate_proposal_pdf, generate_sponsorship_pdf
from app.services.documents.docx_service import generate_proposal_docx
from app.services.documents.xlsx_service import generate_budget_xlsx

router = APIRouter(prefix="/exports", tags=["Exports"])


def _ev(val) -> str:
    return val.value if hasattr(val, "value") else str(val)


async def _load_event_context(event_id: uuid.UUID, db):
    """Load event + society + university for document generation."""
    result = await db.execute(select(EventRecord).where(EventRecord.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise NotFoundError("Event not found")
    soc_result = await db.execute(select(Society).where(Society.id == event.society_id))
    society = soc_result.scalar_one_or_none()
    uni_result = await db.execute(
        select(University).where(University.id == society.university_id)
    ) if society else None
    university = uni_result.scalar_one_or_none() if uni_result else None
    return event, society, university


@router.get("/{event_id}/proposal/pdf")
async def export_proposal_pdf(event_id: uuid.UUID, user: CurrentUser, db: DB) -> Response:
    """Export proposal as PDF."""
    event, society, university = await _load_event_context(event_id, db)
    result = await db.execute(select(ProposalDoc).where(ProposalDoc.event_id == event_id))
    proposal = result.scalar_one_or_none()
    if not proposal:
        raise NotFoundError("No proposal generated yet")
    pdf_bytes = generate_proposal_pdf(
        title=event.title,
        society=society.name if society else "Unknown",
        university=university.name if university else "Unknown",
        event_type=_ev(event.event_type),
        event_date=event.event_date.isoformat() if event.event_date else "TBD",
        sections=proposal.sections,
    )
    filename = f"{event.title.replace(' ', '_')}_Proposal.pdf"
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/{event_id}/proposal/docx")
async def export_proposal_docx(event_id: uuid.UUID, user: CurrentUser, db: DB) -> Response:
    """Export proposal as DOCX."""
    event, society, university = await _load_event_context(event_id, db)
    result = await db.execute(select(ProposalDoc).where(ProposalDoc.event_id == event_id))
    proposal = result.scalar_one_or_none()
    if not proposal:
        raise NotFoundError("No proposal generated yet")
    docx_bytes = generate_proposal_docx(
        title=event.title,
        society=society.name if society else "Unknown",
        university=university.name if university else "Unknown",
        event_type=_ev(event.event_type),
        event_date=event.event_date.isoformat() if event.event_date else "TBD",
        sections=proposal.sections,
    )
    filename = f"{event.title.replace(' ', '_')}_Proposal.docx"
    return Response(content=docx_bytes,
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/{event_id}/budget/xlsx")
async def export_budget_xlsx(event_id: uuid.UUID, user: CurrentUser, db: DB) -> Response:
    """Export budget as XLSX."""
    event, society, university = await _load_event_context(event_id, db)
    result = await db.execute(select(BudgetPlan).where(BudgetPlan.event_id == event_id))
    budget = result.scalar_one_or_none()
    if not budget:
        raise NotFoundError("No budget generated yet")
    xlsx_bytes = generate_budget_xlsx(
        title=event.title, currency=event.currency,
        categories=budget.categories, contingency_percent=budget.contingency_percent,
    )
    filename = f"{event.title.replace(' ', '_')}_Budget.xlsx"
    return Response(content=xlsx_bytes,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/{event_id}/sponsorship/pdf")
async def export_sponsorship_pdf(event_id: uuid.UUID, user: CurrentUser, db: DB) -> Response:
    """Export sponsorship package as PDF."""
    event, society, university = await _load_event_context(event_id, db)
    result = await db.execute(select(SponsorshipPackage).where(SponsorshipPackage.event_id == event_id))
    pkg = result.scalar_one_or_none()
    if not pkg:
        raise NotFoundError("No sponsorship package generated yet")
    pdf_bytes = generate_sponsorship_pdf(
        title=event.title, society=society.name if society else "Unknown",
        tiers=pkg.tiers or [], audience_summary=pkg.audience_summary,
        email_drafts=pkg.email_drafts or [],
    )
    filename = f"{event.title.replace(' ', '_')}_Sponsorship.pdf"
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})
