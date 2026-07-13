import json
import logging

from ollama import Client as OllamaClient

from .config import settings
from .context_loader import AppContext

log = logging.getLogger(__name__)

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
- For date filters, use ISO format values (e.g., "2026-01-01")
- For boolean fields, use "true" or "false"
- Only include filters the user explicitly asked for

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


def decode_prompt(question: str, ctx: AppContext) -> dict:
    system = SYSTEM_PROMPT.format(
        report_summaries=ctx.report_summaries_text(),
        schema_context=ctx.schema_text(),
    )

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
        )
    except Exception:
        log.exception("Ollama call failed during prompt decoding")
        return _unknown_response("Ollama unavailable")

    raw_text = response["message"]["content"].strip()
    return _parse_response(raw_text)


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
    valid_filters = [
        f for f in filters
        if isinstance(f, dict) and "table" in f and "field" in f and "operator" in f and "value" in f
    ]

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


def _unknown_response(message: str) -> dict:
    return {
        "report": "UNKNOWN",
        "query": {"entity": "", "joins": [], "filters": []},
        "parameters": {},
        "template": None,
        "confidence": 0.0,
        "message": message,
    }
