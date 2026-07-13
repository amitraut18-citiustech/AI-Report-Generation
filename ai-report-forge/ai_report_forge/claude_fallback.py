import json
import logging

import anthropic

from .anonymizer import Anonymizer, AnonymizationResult, remap_narrative
from .config import settings
from .context_loader import PhiMarkers

log = logging.getLogger(__name__)

SUMMARIZE_PROMPT = """\
You are a healthcare data analyst. Analyze the following query results
and provide a summary useful for a non-technical healthcare professional.

USER QUESTION: "{question}"
QUERY RESULTS (JSON): {results_json}
TOTAL ROWS: {row_count}

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
- Use "pie" for proportions/distributions, "bar" for comparisons, "line" for trends
- If the data has only 1 row or a chart doesn't make sense, set "chart" to null
- Labels and values must come directly from the data
- Keep to 10 or fewer categories

IMPORTANT: The data has been de-identified. Use the identifiers exactly as they appear
(e.g., Patient_001, P_001). Do not attempt to guess real names or identifiers."""


def summarize_with_claude(
    question: str,
    results: list[dict],
    row_count: int,
    phi_markers: PhiMarkers,
    table: str = "Patients",
) -> dict:
    anonymizer = Anonymizer(phi_markers)
    anon_result: AnonymizationResult = anonymizer.anonymize(results, table)

    results_json = json.dumps(anon_result.anonymized_rows[:100], default=str)
    prompt = SUMMARIZE_PROMPT.format(
        question=question,
        results_json=results_json,
        row_count=row_count,
    )

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
    except Exception:
        log.exception("Claude API call failed")
        return {
            "summary": "Unable to generate summary — both local and cloud LLM failed.",
            "source": "claude",
            "anonymized": True,
            "error": "claude_api_failed",
        }

    try:
        parsed = json.loads(raw)
        narrative = parsed.get("summary", raw)
        chart = parsed.get("chart")
        if chart and not isinstance(chart, dict):
            chart = None
    except json.JSONDecodeError:
        narrative = raw
        chart = None

    final_narrative = remap_narrative(narrative, anon_result.mapping)

    result = {
        "summary": final_narrative,
        "source": "claude",
        "anonymized": True,
    }
    if chart:
        result["chart"] = chart
    return result
