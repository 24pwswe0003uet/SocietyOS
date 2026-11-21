"""Base agent interface that all specialist agents implement.

Layer 1 — Session Memory: EventContext provides a strict, scoped schema
for passing information between agents during a single generation session.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PolicyContext:
    """Subset of policy data relevant to agents — no raw extraction artifacts."""
    lead_time_days: int | None = None
    required_documents: list[str] = field(default_factory=list)
    sponsorship_rules: str | None = None
    prohibitions: list[str] = field(default_factory=list)
    budget_cap: float | None = None
    venue_restrictions: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class HistoricalLesson:
    """A single lesson from a previous event, with provenance."""
    event_title: str
    event_type: str
    lesson: str
    source: str  # "verified" | "unverified"
    metric_context: str | None = None  # e.g. "budget went 20% over"


@dataclass
class EventContext:
    """Shared context passed to every agent during generation.

    Design principles:
    - Immutable event fields (frozen=False only for historical_lessons injection)
    - Scoped to a single event_id — agents cannot access other events
    - Sensitive data (API keys, user passwords) is never included
    - Policy data is filtered to relevant fields only
    - Historical lessons are injected after context creation, before agents run
    """
    # Event identity
    event_id: str
    event_title: str
    event_type: str
    description: str

    # Event details
    audience_size: int | None = None
    event_date: str | None = None
    duration_days: int = 1
    venue_type: str | None = None
    budget_target: float | None = None
    currency: str = "PKR"

    # Organizational context
    society_name: str = ""
    society_id: str = ""
    university_name: str = ""
    university_id: str = ""
    department: str = ""
    faculty_advisor: str | None = None
    approval_chain: list[dict] = field(default_factory=list)

    # Policy (filtered)
    policy: PolicyContext = field(default_factory=PolicyContext)

    # Layer 3 — injected before agents run
    historical_lessons: list[HistoricalLesson] = field(default_factory=list)

    def summary(self) -> str:
        """Human-readable event summary for agent prompts."""
        parts = [
            f"Event: {self.event_title} ({self.event_type})",
            f"Society: {self.society_name}, {self.department}, {self.university_name}",
            f"Description: {self.description}",
        ]
        if self.audience_size:
            parts.append(f"Expected audience: {self.audience_size}")
        if self.event_date:
            parts.append(f"Date: {self.event_date}")
        if self.duration_days:
            parts.append(f"Duration: {self.duration_days} day(s)")
        if self.venue_type:
            parts.append(f"Venue: {self.venue_type}")
        if self.budget_target:
            parts.append(f"Budget: {self.currency} {self.budget_target:,.0f}")
        if self.faculty_advisor:
            parts.append(f"Faculty Advisor: {self.faculty_advisor}")
        return "\n".join(parts)

    def policy_summary(self) -> str:
        """Human-readable policy constraints for agent prompts."""
        parts = []
        if self.policy.lead_time_days:
            parts.append(f"Required lead time: {self.policy.lead_time_days} days")
        if self.policy.required_documents:
            parts.append(f"Required documents: {', '.join(self.policy.required_documents)}")
        if self.policy.sponsorship_rules:
            parts.append(f"Sponsorship rules: {self.policy.sponsorship_rules}")
        if self.policy.prohibitions:
            parts.append(f"Prohibitions: {', '.join(self.policy.prohibitions)}")
        if self.policy.budget_cap:
            parts.append(f"Budget cap: {self.currency} {self.policy.budget_cap:,.0f}")
        return "\n".join(parts) if parts else "No specific policy constraints found."

    def historical_summary(self) -> str:
        """Format historical lessons for injection into agent prompts."""
        if not self.historical_lessons:
            return ""
        parts = ["\n--- HISTORICAL INSIGHTS (from previous events at this university) ---"]
        for i, lesson in enumerate(self.historical_lessons, 1):
            status = "[VERIFIED]" if lesson.source == "verified" else "[UNVERIFIED]"
            parts.append(f"{i}. {status} From '{lesson.event_title}' ({lesson.event_type}):")
            parts.append(f"   {lesson.lesson}")
            if lesson.metric_context:
                parts.append(f"   Context: {lesson.metric_context}")
        parts.append("--- Use these insights to improve planning, but verify with current policies. ---")
        return "\n".join(parts)

    def full_prompt_context(self) -> str:
        """Complete context string for agent prompts — event + policy + history."""
        sections = [self.summary(), self.policy_summary()]
        hist = self.historical_summary()
        if hist:
            sections.append(hist)
        return "\n\n".join(sections)


class BaseAgent(ABC):
    """Interface for all specialist agents."""

    agent_name: str = "base"

    @abstractmethod
    async def generate(self, context: EventContext) -> dict[str, Any]:
        """Run the agent and return structured output."""
        ...
