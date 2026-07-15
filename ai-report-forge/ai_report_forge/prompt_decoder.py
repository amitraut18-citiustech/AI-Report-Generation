import json
import logging
import re

import anthropic
from ollama import Client as OllamaClient

from . import prompt_log
from .config import settings
from .context_loader import AppContext

log = logging.getLogger(__name__)

# Below this confidence the local decode is treated as failed and, when a
# Claude API key is configured, retried on Claude.
FALLBACK_CONFIDENCE = 0.3

SYSTEM_PROMPT = """\
You are a report routing and query specification system for a healthcare application.

AVAILABLE REPORTS:
{report_summaries}

DATABASE SCHEMA (tables, columns, and relationships):
{schema_context}

ALLOWED FILTER OPERATORS:
- equals: exact match (strings are case-insensitive)
- notEquals: not equal
- contains: substring match (strings only)
- greaterThan: > (numbers and dates)
- greaterThanOrEqual: >= (numbers and dates)
- lessThan: < (numbers and dates)
- lessThanOrEqual: <= (numbers and dates)

Given the user's question:
1. Which report best matches (return the report key)
2. What is the primary entity to query
3. What table-qualified filters to apply
4. What joins are needed (only when filtering on a related table)

FILTER RULES:
- Each filter MUST specify which "table" the field belongs to
- Use exact field names and table names from the DATABASE SCHEMA
- For filtering on related tables (e.g., facility name when querying patients), use the
  related table's fields and include a join. Example: to filter patients by facility name,
  add a join to Facilities and filter on table="Facilities", field="Name"
- Do NOT use FK integer columns (FacilityId, PatientId, ProviderId) for text-based filters —
  use the related table's display fields via a join instead
- For date filters, use ISO format values (e.g., "2026-01-01"). All filter values MUST be
  strings, even for numbers — e.g. "60" not 60
- For boolean fields, use "true" or "false"
- Only include filters the user explicitly asked for

NAME FILTER RULES:
- A single name like "Ethan" or "Mia" is a FIRST NAME — filter on field "FirstName"
- A single name like "Garcia" or "Thompson" is a LAST NAME — filter on field "LastName"
- If ambiguous, use "contains" on BOTH FirstName and LastName is NOT possible — pick the
  most likely field. Common first names (Ethan, Mia, Noah, Ava, Liam, Sophia, Olivia, Lucas)
  should filter on "FirstName"
- For a full name like "Ava Patel", create TWO filters: FirstName equals "Ava" AND
  LastName equals "Patel"

GENDER RULES:
- "female", "females", "women", "woman" → Gender equals "Female"
- "male", "males", "men", "man" → Gender equals "Male"
- NEVER use notEquals for gender words. "women" is Gender equals "Female",
  NOT Gender notEquals "Female"

LOCATION RULES:
- A city name ("in Dallas", "from Houston", "Austin patients") → filter on
  table="Facilities", field="City"
- A full facility name ("Austin General Hospital", "Dallas Transplant Clinic")
  → filter on table="Facilities", field="Name"
- A 2-letter state ("in TX") → filter on table="Facilities", field="State"

DATE RANGE RULES:
- "in January 2026" means: greaterThanOrEqual "2026-01-01" AND lessThanOrEqual "2026-01-31"
- "between January and March 2026" means: greaterThanOrEqual "2026-01-01" AND
  lessThanOrEqual "2026-03-31"
- "after X" ALWAYS means greaterThan (later than X). "after March 2026" →
  greaterThan "2026-03-31". NEVER lessThan for "after"
- "before X" ALWAYS means lessThan (earlier than X). "before February 2026" →
  lessThan "2026-02-01". NEVER greaterThan for "before"
- Always use the DateOfVisit field for transplant event date filters

OPERATOR RULES:
- Use "equals" when the user asks FOR something: "show autologous" → equals "Autologous"
- Use "notEquals" ONLY when the user explicitly asks to EXCLUDE something: "exclude autologous"
- "outpatient" means IsInpatient equals "false". "inpatient" means IsInpatient equals "true"
- For status filters, prefer "equals" with the exact value: "inactive patients" →
  Status equals "Inactive", NOT Status notEquals "Active"

CRITICAL:
- NEVER use placeholder values like "UNKNOWN", "<facility_id>", or "<value>" in filters.
  If you cannot determine a filter value from the user's question, do NOT include that filter.
- Only include filters that directly correspond to what the user asked for.
- The "template" field must match the report key: patient → "patient.html",
  transplant_event → "transplant_event.html",
  patient_clinical_summary → "patient_clinical_summary.html"

If no report matches, return report="UNKNOWN" with confidence=0 and empty query.

Respond with ONLY valid JSON, no other text:
{{
  "report": "<report_key>",
  "query": {{
    "entity": "<PrimaryTableName>",
    "joins": [
      {{"table": "<RelatedTable>", "localKey": "<FK column>", "foreignKey": "Id"}}
    ],
    "filters": [
      {{"table": "<TableName>", "field": "<FieldName>", "operator": "<op>", "value": "<val>"}}
    ]
  }},
  "template": "<template_file>",
  "confidence": <0.0-1.0>
}}"""


def decode_prompt(question: str, ctx: AppContext, provider: str = "local") -> dict:
    system = SYSTEM_PROMPT.format(
        report_summaries=ctx.report_summaries_text(),
        schema_context=ctx.schema_text(),
    )

    if provider == "claude":
        result = _decode_with_claude(question, system)
        result["source"] = "claude"
        _log_decode(question, provider, result)
        return result

    if settings.force_decode_fallback:
        # Demo/testing knob (FORCE_DECODE_FALLBACK in .env): skip the local
        # model and pretend it failed, so the fallback path runs on cue.
        log.warning("FORCE_DECODE_FALLBACK is enabled — skipping local decode")
        result = _unknown_response("Local decode skipped (FORCE_DECODE_FALLBACK)")
    else:
        result = _decode_with_ollama(question, system)

    # Local decode failed or was too uncertain — retry on Claude when configured.
    fallback_attempted = False
    if _needs_fallback(result) and settings.anthropic_api_key:
        fallback_attempted = True
        log.info(
            "Local decode failed (report=%s, confidence=%.2f) — falling back to Claude",
            result["report"], result["confidence"],
        )
        claude_result = _decode_with_claude(question, system)
        if not _needs_fallback(claude_result):
            # Distinct source so the UI can show that the local model failed
            # and Claude stepped in, vs. the user explicitly asking Claude.
            claude_result["source"] = "claude_fallback"
            _log_decode(question, provider, claude_result, fallback_attempted)
            return claude_result

    result["source"] = "ollama"
    _log_decode(question, provider, result, fallback_attempted)
    return result


def _log_decode(
    question: str, provider: str, result: dict, fallback_attempted: bool = False
) -> None:
    prompt_log.record({
        "kind": "decode",
        "provider": provider,
        "source": result.get("source"),
        "succeeded": not _needs_fallback(result),
        "fallbackAttempted": fallback_attempted,
        "sentQuestion": question,
        "report": result.get("report"),
        "note": (
            "Decode sends the question text as-is — filter values (e.g. patient "
            "names) must be extracted from it. No database rows are sent."
        ),
    })


def _needs_fallback(result: dict) -> bool:
    return result["report"] == "UNKNOWN" or result["confidence"] < FALLBACK_CONFIDENCE


def _decode_with_ollama(question: str, system: str) -> dict:
    try:
        client = OllamaClient(
            host=settings.ollama_base_url,
            timeout=settings.ollama_timeout,
        )
        response = client.chat(
            model=settings.ollama_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": question},
            ],
            options={"temperature": 0.1},
            keep_alive=settings.ollama_keep_alive,
        )
    except Exception:
        log.exception("Ollama call failed during prompt decoding")
        return _unknown_response("Ollama unavailable")

    raw_text = response["message"]["content"].strip()
    result = _parse_response(raw_text)
    # The sanitizer compensates for known small-model decode errors; it is
    # only applied to the local model's output.
    _sanitize_filters(question, result["query"]["filters"])
    return result


def _decode_with_claude(question: str, system: str) -> dict:
    """Decode the question with the Claude API.

    Note: decoding inherently sends the user's question to the cloud — filter
    values (e.g. patient names) must be extracted from it, so it cannot be
    anonymized the way /summarize data is. No database rows ever leave here.
    """
    if not settings.anthropic_api_key:
        return _unknown_response(
            "Claude is not configured — set ANTHROPIC_API_KEY in ai-report-forge/.env"
        )

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": question}],
        )
        raw_text = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()
    except anthropic.APIStatusError as exc:
        log.exception("Claude API call failed during prompt decoding")
        # Surface the API's own reason (auth, billing, rate limit) — this is
        # operator-facing config feedback, not user data.
        detail = getattr(getattr(exc, "body", None), "get", lambda *_: None)("error")
        message = (detail or {}).get("message") if isinstance(detail, dict) else None
        return _unknown_response(f"Claude API error: {message or exc.status_code}")
    except Exception:
        log.exception("Claude API call failed during prompt decoding")
        return _unknown_response("Claude API unavailable")

    if not raw_text:
        return _unknown_response("Claude returned an empty response")
    return _parse_response(raw_text)


# Words that legitimately signal exclusion in the question. If none of these
# appear, a notEquals filter on Gender is almost certainly an inversion error
# by the small local model (e.g. "women" -> Gender notEquals "Female").
_EXCLUSION_RE = re.compile(r"\b(exclude|excluding|except|not|non|other than|without)\b", re.IGNORECASE)

# Tokens that indicate a value is a full facility name rather than a city.
_FACILITY_NAME_RE = re.compile(r"\b(hospital|clinic|center|centre|medical)\b", re.IGNORECASE)

# Fields the model sometimes hallucinates filters for, and the question words
# that would legitimately justify such a filter.
_JUSTIFICATION_RES = {
    "isinpatient": re.compile(r"\b(inpatient|outpatient|admitted|admission|hospitali[sz]ed)\b", re.IGNORECASE),
    "status": re.compile(r"\b(active|inactive|status)\b", re.IGNORECASE),
}


def _sanitize_filters(question: str, filters: list[dict]) -> None:
    """Deterministic corrections for known small-model decode errors.

    The 3B decoder occasionally inverts gender filters ("women" ->
    notEquals Female), puts bare city names into Facilities.Name, and
    hallucinates filters the user never asked for (e.g. IsInpatient).
    These fixes are conservative: they only fire when the question text
    clearly contradicts the decoded filter.
    """
    # Drop hallucinated filters: fields whose presence requires a specific
    # word in the question ("inpatient", "active", ...) that isn't there.
    for f in list(filters):
        justification = _JUSTIFICATION_RES.get(f["field"].lower())
        if justification and not justification.search(question):
            log.info("Dropped unjustified filter: %s.%s %s %s",
                     f["table"], f["field"], f["operator"], f["value"])
            filters.remove(f)

    for f in filters:
        # Gender inversion: notEquals without any exclusion word in the question.
        if (
            f["field"].lower() == "gender"
            and f["operator"] == "notEquals"
            and not _EXCLUSION_RE.search(question)
        ):
            log.info("Sanitized gender filter: notEquals -> equals ('%s')", f["value"])
            f["operator"] = "equals"

        # City-in-Name: a single-word Facilities.Name value with no facility
        # keyword is a city, not a facility name.
        if (
            f["table"].lower() == "facilities"
            and f["field"].lower() == "name"
            and " " not in f["value"].strip()
            and not _FACILITY_NAME_RE.search(f["value"])
        ):
            log.info("Sanitized facility filter: Name -> City ('%s')", f["value"])
            f["field"] = "City"


def _parse_response(raw: str) -> dict:
    cleaned = raw
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        log.warning("Failed to parse Ollama response as JSON: %s", raw[:200])
        return _unknown_response("Response was not valid JSON")

    report = parsed.get("report", "UNKNOWN")
    confidence = parsed.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)):
        confidence = 0.0

    query = parsed.get("query", {})
    if not isinstance(query, dict):
        query = {}

    entity = query.get("entity", "")
    joins = query.get("joins", [])
    if not isinstance(joins, list):
        joins = []
    valid_joins = [
        j for j in joins
        if isinstance(j, dict) and "table" in j and "localKey" in j
    ]

    filters = query.get("filters", [])
    if not isinstance(filters, list):
        filters = []
    valid_filters = []
    for f in filters:
        if not (isinstance(f, dict) and "table" in f and "field" in f and "operator" in f and "value" in f):
            continue
        if _is_placeholder(f["value"]):
            log.info("Stripped placeholder filter: %s.%s = %s", f["table"], f["field"], f["value"])
            continue
        f["value"] = str(f["value"])
        valid_filters.append(f)

    return {
        "report": report,
        "query": {
            "entity": entity,
            "joins": valid_joins,
            "filters": valid_filters,
        },
        "parameters": parsed.get("parameters", {}),
        "template": parsed.get("template"),
        "confidence": float(confidence),
    }


_PLACEHOLDER_RE = re.compile(r"^<.*>$|^UNKNOWN$|^null$|^undefined$|^N/A$", re.IGNORECASE)


def _is_placeholder(value) -> bool:
    s = str(value).strip()
    return bool(_PLACEHOLDER_RE.match(s)) or not s


def _unknown_response(message: str) -> dict:
    return {
        "report": "UNKNOWN",
        "query": {"entity": "", "joins": [], "filters": []},
        "parameters": {},
        "template": None,
        "confidence": 0.0,
        "message": message,
    }
