import json
import logging

from ollama import Client as OllamaClient

from .anonymizer import Anonymizer, AnonymizationResult, remap_narrative
from .config import settings
from .context_loader import PhiMarkers

log = logging.getLogger(__name__)

SUMMARIZE_PROMPT = """\
You are a healthcare data analyst. Analyze the following query results
and provide a summary useful for a non-technical healthcare professional.

USER QUESTION: "{question}"
QUERY RESULTS (JSON): {results_json}
TOTAL ROWS: {row_count}{truncation_note}

Respond with ONLY valid JSON, no other text:
{{
  "summary": "2-3 sentence executive summary highlighting key findings, notable patterns or outliers, and any data quality observations. Keep the tone professional and factual.",
  "chart": {{
    "type": "bar or pie or line",
    "title": "Chart title",
    "labels": ["label1", "label2"],
    "values": [number1, number2]
  }}
}}

CHART RULES:
- Use "pie" for proportions/distributions (e.g., gender split, status breakdown)
- Use "bar" for comparisons across categories (e.g., counts by facility, by type)
- Use "line" for trends over time (e.g., visits by month)
- If the data has only 1 row or a chart doesn't make sense, set "chart" to null
- Labels and values must come directly from the data — do not invent numbers
- Keep to 10 or fewer categories; group small categories as "Other" if needed

IMPORTANT: The data has been de-identified. Use the identifiers exactly as they appear
(e.g., Patient_001, P_001). Do not attempt to guess real names or identifiers."""

MIN_SUMMARY_LENGTH = 20


def summarize(
    question: str,
    results: list[dict],
    row_count: int,
    phi_markers: PhiMarkers | None = None,
    table: str = "Patients",
) -> dict:
    # Anonymize data before sending to Ollama (same as the Claude path).
    # Even though Ollama is typically local, this prevents PHI from leaking
    # into logs, model caches, or a future remote deployment.
    anon_result: AnonymizationResult | None = None
    if phi_markers is not None:
        anonymizer = Anonymizer(phi_markers)
        anon_result = anonymizer.anonymize(results, table)
        send_rows = anon_result.anonymized_rows
    else:
        send_rows = results

    sample = send_rows[:100]
    truncation_note = ""
    if row_count > len(sample):
        truncation_note = (
            f"\n(Note: Only the first {len(sample)} rows are shown above. "
            f"Base your aggregate statements on TOTAL ROWS, not the visible sample.)"
        )

    results_json = json.dumps(sample, default=str)
    prompt = SUMMARIZE_PROMPT.format(
        question=question,
        results_json=results_json,
        row_count=row_count,
        truncation_note=truncation_note,
    )

    try:
        client = OllamaClient(
            host=settings.ollama_base_url,
            timeout=settings.ollama_timeout,
        )
        response = client.chat(
            model=settings.ollama_model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.3},
        )
    except Exception:
        log.exception("Ollama call failed during summarization")
        return {"summary": None, "source": "ollama", "error": "ollama_unavailable"}

    raw = response["message"]["content"].strip()
    parsed = _parse_summarize_response(raw)

    # If Ollama produced a valid summary, remap pseudonyms back to real values.
    if parsed.get("summary") and anon_result is not None and anon_result.mapping:
        parsed["summary"] = remap_narrative(parsed["summary"], anon_result.mapping)
        parsed["anonymized"] = True

    return parsed


def _parse_summarize_response(raw: str) -> dict:
    cleaned = raw
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        parsed = json.loads(cleaned)
        summary = parsed.get("summary", "")
        chart = parsed.get("chart")
        if chart and not isinstance(chart, dict):
            chart = None
    except json.JSONDecodeError:
        summary = raw
        chart = None

    if not _quality_check(summary):
        log.warning("Ollama summary failed quality check, flagging for fallback")
        return {"summary": None, "source": "ollama", "error": "quality_check_failed"}

    result = {"summary": summary, "source": "ollama"}
    if chart:
        result["chart"] = chart
    return result


def _quality_check(summary: str) -> bool:
    """Basic quality gate: reject empty or trivially short summaries.

    Previous versions required verbatim row values to appear in the summary,
    which rejected valid aggregate summaries (e.g. "3 patients matched,
    average age 45"). Now we only check for minimum length.
    """
    if not summary or len(summary) < MIN_SUMMARY_LENGTH:
        return False
    return True
