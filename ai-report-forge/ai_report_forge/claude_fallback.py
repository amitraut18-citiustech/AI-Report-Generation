import json
import logging

import anthropic

from .anonymizer import Anonymizer, AnonymizationResult, remap_narrative
from .config import settings
from .context_loader import PhiMarkers

log = logging.getLogger(__name__)

SUMMARIZE_PROMPT = """\
You are a healthcare data analyst. Summarize the following query results
in a way that is useful for a non-technical healthcare professional.

USER QUESTION: "{question}"
QUERY RESULTS (JSON): {results_json}
TOTAL ROWS: {row_count}

Provide:
1. A 2-3 sentence executive summary highlighting key findings
2. Notable patterns or outliers
3. Any data quality observations (e.g., NULL values, unexpected distributions)

Keep the tone professional and factual. Do not speculate beyond what the data shows.

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
        narrative = response.content[0].text.strip()
    except Exception:
        log.exception("Claude API call failed")
        return {
            "summary": "Unable to generate summary — both local and cloud LLM failed.",
            "source": "claude",
            "anonymized": True,
            "error": "claude_api_failed",
        }

    final_narrative = remap_narrative(narrative, anon_result.mapping)

    return {
        "summary": final_narrative,
        "source": "claude",
        "anonymized": True,
    }
