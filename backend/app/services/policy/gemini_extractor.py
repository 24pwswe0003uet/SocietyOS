"""Gemini-powered policy extraction — sends document chunks to AI and gets structured output."""

import logging
from typing import Any

from app.services.ai.gemini import gemini_provider
from app.services.policy.document_chunker import DocumentChunk

logger = logging.getLogger("societyos.policy.gemini")

EXTRACTION_PROMPT = """You are SocietyOS AI, a university event policy analyst.

You are analyzing a university document to extract event-related policy information.
This document is from a {university_name} and was provided as a {source_type}.

{context_note}

Document text ({page_info}):
\"\"\"
{text}
\"\"\"

INSTRUCTIONS:
- Extract ONLY information that is explicitly stated or clearly implied in the text.
- Do NOT invent rules, deadlines, or approval chains that are not in the document.
- For each extracted field, note where in the document you found it (page number, section name, or surrounding context).
- If a field cannot be determined, set it to null.
- Assign a confidence_score between 0.0 and 1.0 for the overall extraction quality:
  - 1.0 = All fields clearly found in the document
  - 0.7-0.9 = Most fields found, some inferred
  - 0.4-0.6 = Partial information, significant gaps
  - 0.0-0.3 = Very little relevant information found

Respond ONLY with valid JSON:

{{
  "approval_chain": {{
    "steps": [
      {{"order": 1, "authority": "Title/name of approving authority", "role": "role_key", "notes": "Any specific requirements for this step"}}
    ]
  }},
  "lead_time_days": null,
  "required_documents": ["list of required documents"],
  "sponsorship_rules": "Description of sponsorship/funding rules, or null",
  "prohibitions": ["list of prohibited activities"],
  "additional_rules": [
    {{"rule": "Any other relevant rule", "source": "Where in the document this was found"}}
  ],
  "confidence_score": 0.0,
  "extraction_warnings": ["List any issues or uncertainties"],
  "source_references": [
    {{"field": "approval_chain", "source": "Page X, Section Y", "excerpt": "Brief quote from the document"}}
  ]
}}
"""

EXTRACTION_SCHEMA = """{
  "approval_chain": {"steps": [{"order":"int","authority":"string","role":"string","notes":"string|null"}]} | null,
  "lead_time_days": "int|null",
  "required_documents": ["string"] | null,
  "sponsorship_rules": "string|null",
  "prohibitions": ["string"] | null,
  "additional_rules": [{"rule":"string","source":"string"}] | null,
  "confidence_score": "float 0.0-1.0",
  "extraction_warnings": ["string"] | null,
  "source_references": [{"field":"string","source":"string","excerpt":"string"}] | null
}"""


async def extract_policy_from_chunk(
    chunk: DocumentChunk,
    university_name: str = "this university",
    source_type: str = "policy document",
    is_prospectus: bool = False,
) -> dict[str, Any]:
    """Send a document chunk to Gemini and extract structured policy data.

    Returns a dict matching the PolicyData fields, or a fallback dict on failure.
    """
    context_note = ""
    if is_prospectus:
        context_note = (
            "This is a university prospectus or student handbook. "
            "Focus on sections about student societies, events, extracurricular activities, "
            "and approval processes. Ignore unrelated academic content."
        )

    page_info = chunk.page_range or f"{chunk.char_count} characters"

    prompt = EXTRACTION_PROMPT.format(
        university_name=university_name,
        source_type=source_type,
        context_note=context_note,
        page_info=page_info,
        text=chunk.text,
    )

    try:
        raw = await gemini_provider.generate_structured(
            prompt=prompt,
            schema_description=EXTRACTION_SCHEMA,
            temperature=0.2,  # Low temperature for factual extraction
            max_tokens=4096,
        )
        return _normalize_extraction(raw)
    except Exception as e:
        logger.error("Gemini extraction failed for chunk %d: %s", chunk.chunk_index, e)
        return _empty_extraction(str(e))


async def merge_chunk_extractions(extractions: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge extraction results from multiple chunks into a single PolicyData.

    Strategy:
    - approval_chain: Take the most complete chain (most steps).
    - lead_time_days: Take the maximum (most conservative).
    - required_documents: Union of all lists, deduplicated.
    - sponsorship_rules: Concatenate non-null rules.
    - prohibitions: Union of all lists, deduplicated.
    - confidence_score: Average across chunks.
    - source_references: Concatenate all.
    """
    if len(extractions) == 1:
        return extractions[0]

    merged = _empty_extraction()

    # Approval chain: pick the one with the most steps
    best_chain = None
    best_chain_len = 0
    for ext in extractions:
        chain = ext.get("approval_chain")
        if chain and isinstance(chain, dict):
            steps = chain.get("steps", [])
            if len(steps) > best_chain_len:
                best_chain = chain
                best_chain_len = len(steps)
    merged["approval_chain"] = best_chain

    # Lead time: most conservative (maximum)
    lead_times = [e.get("lead_time_days") for e in extractions if e.get("lead_time_days")]
    merged["lead_time_days"] = max(lead_times) if lead_times else None

    # Required documents: deduplicated union
    all_docs = []
    for ext in extractions:
        for doc in (ext.get("required_documents") or []):
            if doc and doc not in all_docs:
                all_docs.append(doc)
    merged["required_documents"] = all_docs or None

    # Sponsorship rules: concatenate
    rules = [e.get("sponsorship_rules") for e in extractions if e.get("sponsorship_rules")]
    merged["sponsorship_rules"] = " ".join(rules) if rules else None

    # Prohibitions: deduplicated union
    all_prohibitions = []
    for ext in extractions:
        for p in (ext.get("prohibitions") or []):
            if p and p not in all_prohibitions:
                all_prohibitions.append(p)
    merged["prohibitions"] = all_prohibitions or None

    # Additional rules
    all_rules = []
    for ext in extractions:
        all_rules.extend(ext.get("additional_rules") or [])
    merged["additional_rules"] = all_rules or None

    # Confidence: average
    scores = [e.get("confidence_score", 0) for e in extractions if e.get("confidence_score") is not None]
    merged["confidence_score"] = round(sum(scores) / len(scores), 2) if scores else 0.0

    # Warnings and references: concatenate
    all_warnings = []
    all_refs = []
    for ext in extractions:
        all_warnings.extend(ext.get("extraction_warnings") or [])
        all_refs.extend(ext.get("source_references") or [])
    merged["extraction_warnings"] = all_warnings or None
    merged["source_references"] = all_refs or None

    return merged


def _normalize_extraction(raw: dict[str, Any]) -> dict[str, Any]:
    """Clean and validate the raw Gemini output."""
    # Clamp confidence
    score = raw.get("confidence_score")
    if isinstance(score, (int, float)):
        raw["confidence_score"] = max(0.0, min(1.0, float(score)))
    else:
        raw["confidence_score"] = 0.5

    # Ensure approval_chain has correct structure
    chain = raw.get("approval_chain")
    if chain and not isinstance(chain, dict):
        raw["approval_chain"] = None
    elif chain and "steps" not in chain:
        raw["approval_chain"] = None

    # Ensure lists are actually lists
    for field in ["required_documents", "prohibitions", "additional_rules",
                  "extraction_warnings", "source_references"]:
        val = raw.get(field)
        if val is not None and not isinstance(val, list):
            raw[field] = None

    return raw


def _empty_extraction(error_msg: str = "") -> dict[str, Any]:
    """Return an empty extraction result."""
    warnings = []
    if error_msg:
        warnings.append(f"Extraction failed: {error_msg}")

    return {
        "approval_chain": None,
        "lead_time_days": None,
        "required_documents": None,
        "sponsorship_rules": None,
        "prohibitions": None,
        "additional_rules": None,
        "confidence_score": 0.0,
        "extraction_warnings": warnings or None,
        "source_references": None,
    }
