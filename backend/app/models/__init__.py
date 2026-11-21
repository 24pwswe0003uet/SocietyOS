"""SQLAlchemy ORM models — import all models here so Alembic discovers them."""

from app.models.user import User  # noqa: F401
from app.models.university import University  # noqa: F401
from app.models.society import Society, SocietyMembership, MemberRole  # noqa: F401
from app.models.event import EventRecord, EventType, EventStatus  # noqa: F401
from app.models.policy import PolicyData, PolicySourceFormat  # noqa: F401
from app.models.proposal import ProposalDoc  # noqa: F401
from app.models.budget import BudgetPlan  # noqa: F401
from app.models.sponsorship import SponsorshipPackage  # noqa: F401
from app.models.task import ApprovalStep, Task, ApprovalStatus, TaskStatus, TaskPriority  # noqa: F401
from app.models.event_outcome import EventOutcome, ApprovalResult  # noqa: F401
