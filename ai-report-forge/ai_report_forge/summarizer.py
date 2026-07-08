import json
import logging

import ollama

from .config import settings

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

Keep the tone professional and factual. Do not speculate beyond what the data shows."""

MIN_SUMMARY_LENGTH = 20


def summarize(
    question: str,
    results: list[dict],
    row_count: int,
) -> dict:
    results_json = json.dumps(results[:100], default=str)
    prompt = SUMMARIZE_PROMPT.format(
        question=question,
        results_json=results_json,
        row_count=row_count,
    )

    try:
        response = ollama.chat(
            model=settings.ollama_model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.3},
        )
    except Exception:
        log.exception("Ollama call failed during summarization")
        return {"summary": None, "source": "ollama", "error": "ollama_unavailable"}

    summary = response["message"]["content"].strip()

    if not _quality_check(summary, results):
        log.warning("Ollama summary failed quality check, flagging for fallback")
        return {"summary": None, "source": "ollama", "error": "quality_check_failed"}

    return {"summary": summary, "source": "ollama"}


def _quality_check(summary: str, results: list[dict]) -> bool:
    if len(summary) < MIN_SUMMARY_LENGTH:
        return False

    result_values = set()
    for row in results[:20]:
        for v in row.values():
            result_values.add(str(v).lower())

    matched = sum(1 for v in result_values if v in summary.lower())
    if len(result_values) > 0 and matched == 0:
        return False

    return True
