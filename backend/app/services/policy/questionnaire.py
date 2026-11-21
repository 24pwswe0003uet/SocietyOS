"""Mode 3: Questionnaire-based policy inference.

Builds PolicyData from 5 user answers. Uses Gemini when available,
falls back to rule-based inference.
"""

import logging
from typing import Any

from app.services.ai.gemini import gemini_provider

logger = logging.getLogger("societyos.policy.questionnaire")

QUESTIONNAIRE_PROMPT = """You are SocietyOS AI, a university event policy analyst.

Based on the following answers from a student society member, infer reasonable
event policy information for their university. Be conservative — clearly note
anything that is inferred rather than confirmed.

ANSWERS:
1. Faculty Advisor: {faculty_advisor}
2. Department: {department}
3. Reports to: {reports_to}
4. Previous events experience: {previous_events}
5. Past rejections: {past_rejections}

INSTRUCTIONS:
- Build a reasonable approval chain based on the reporting structure.
- Infer lead time from past submission timing.
- Infer required documents from past rejection reasons (missing docs = required).
- Keep confidence_score between 0.3 and 0.6 since this is questionnaire-based.
- Mark everything as inferred in source_references.
- In extraction_warnings, note that this is questionnaire-derived and unverified.

Respond with JSON:
{{
  "approval_chain": {{
    "steps": [
      {{"order": 1, "authority": "...", "role": "...", "notes": "Inferred from questionnaire"}}
    ]
  }},
  "lead_time_days": null,
  "required_documents": ["list of likely required documents"],
  "sponsorship_rules": null,
  "prohibitions": ["any known restrictions from past rejections"],
  "additional_rules": null,
  "confidence_score": 0.4,
  "extraction_warnings": ["This policy data is inferred from questionnaire answers and has not been verified against official university documents."],
  "source_references": [{{"field": "all", "source": "Questionnaire responses", "excerpt": "Inferred — not from official document"}}]
}}
"""


async def build_policy_from_questionnaire(
    faculty_advisor: str,
    department: str,
    reports_to: str,
    previous_events: str,
    past_rejections: str,
) -> dict[str, Any]:
    """Build PolicyData from questionnaire answers.

    Tries Gemini first for intelligent inference; falls back to rule-based.
    """
    prompt = QUESTIONNAIRE_PROMPT.format(
        faculty_advisor=faculty_advisor,
        department=department,
        reports_to=reports_to,
        previous_events=previous_events,
        past_rejections=past_rejections,
    )

    try:
        raw = await gemini_provider.generate_structured(
            prompt=prompt,
            schema_description="{}",  # Prompt already includes schema
            temperature=0.3,
            max_tokens=3000,
        )
        # Cap confidence at 0.6 for questionnaire mode
        if isinstance(raw.get("confidence_score"), (int, float)):
            raw["confidence_score"] = min(0.6, max(0.0, float(raw["confidence_score"])))
        else:
            raw["confidence_score"] = 0.4
        return raw
    except Exception as e:
        logger.warning("Gemini unavailable for questionnaire; using rule-based fallback: %s", e)
        return _rule_based_inference(
            faculty_advisor, department, reports_to, previous_events, past_rejections
        )


def _rule_based_inference(
    faculty_advisor: str,
    department: str,
    reports_to: str,
    previous_events: str,
    past_rejections: str,
) -> dict[str, Any]:
    """Deterministic fallback when Gemini is unavailable.

    Uses the standard Pakistani university approval chain pattern from the PRD:
    Faculty Advisor → HOD → Dean of Students → Student Affairs Office
    """
    # Build approval chain based on reporting structure
    steps = [
        {"order": 1, "authority": faculty_advisor or "Faculty Advisor", "role": "faculty_advisor", "notes": "From questionnaire"},
        {"order": 2, "authority": f"Head of Department — {department}", "role": "hod", "notes": "Standard chain"},
    ]

    if reports_to == "student_affairs":
        steps.append({"order": 3, "authority": "Student Affairs Office", "role": "student_affairs", "notes": "Direct reporting"})
    else:
        steps.append({"order": 3, "authority": "Dean of Students", "role": "dean", "notes": "Academic reporting path"})
        steps.append({"order": 4, "authority": "Student Affairs Office", "role": "student_affairs", "notes": "Final approval"})

    # Infer lead time from previous events description
    lead_time = 14  # default
    prev_lower = previous_events.lower()
    if "3 week" in prev_lower or "21 day" in prev_lower:
        lead_time = 21
    elif "month" in prev_lower or "4 week" in prev_lower or "30 day" in prev_lower:
        lead_time = 30
    elif "1 week" in prev_lower or "7 day" in prev_lower:
        lead_time = 7
    elif "2 week" in prev_lower or "14 day" in prev_lower:
        lead_time = 14

    # Infer required documents from rejection reasons
    required_docs = ["Event proposal", "Budget plan"]
    rej_lower = past_rejections.lower()
    if "venue" in rej_lower or "booking" in rej_lower:
        required_docs.append("Venue booking confirmation")
    if "budget" in rej_lower:
        if "Budget plan" not in required_docs:
            required_docs.append("Budget plan")
    if "risk" in rej_lower or "safety" in rej_lower:
        required_docs.append("Risk assessment")
    if "sponsor" in rej_lower:
        required_docs.append("Sponsorship details")

    # Infer prohibitions from rejections
    prohibitions = []
    if "alcohol" in rej_lower:
        prohibitions.append("Alcohol at events")
    if "late" in rej_lower or "deadline" in rej_lower:
        prohibitions.append("Late submissions (strict deadline enforcement)")

    warnings = [
        "This policy data is INFERRED from questionnaire answers.",
        "It has NOT been verified against official university documents.",
        "Please review and verify before relying on this for event planning.",
    ]

    return {
        "approval_chain": {"steps": steps},
        "lead_time_days": lead_time,
        "required_documents": required_docs,
        "sponsorship_rules": None,
        "prohibitions": prohibitions or None,
        "additional_rules": None,
        "confidence_score": 0.35,
        "extraction_warnings": warnings,
        "source_references": [
            {"field": "all", "source": "Questionnaire responses (rule-based fallback)", "excerpt": "Inferred — Gemini unavailable"}
        ],
    }
