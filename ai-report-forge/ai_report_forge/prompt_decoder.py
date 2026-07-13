import json
import logging

from ollama import Client as OllamaClient

from .config import settings
from .context_loader import AppContext

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a report routing system for a healthcare application.

AVAILABLE REPORTS:
{report_summaries}

DATABASE SCHEMA:
{schema_context}

Given the user's question, determine:
1. Which report best matches (return the report key)
2. What parameters to extract (dates, facilities, filters)
3. Which HTML template to use

If no report matches, return report="UNKNOWN" with confidence=0.

Respond with ONLY valid JSON, no other text:
{{
  "report": "<report_key>",
  "parameters": {{ }},
  "template": "<template_file>",
  "confidence": <0.0-1.0>
}}"""


def decode_prompt(question: str, ctx: AppContext) -> dict:
    system = SYSTEM_PROMPT.format(
        report_summaries=ctx.report_summaries_text(),
        schema_context=ctx.schema_text(),
    )

    try:
        client = OllamaClient(host=settings.ollama_base_url)
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

    return {
        "report": report,
        "parameters": parsed.get("parameters", {}),
        "template": parsed.get("template"),
        "confidence": float(confidence),
    }


def _unknown_response(message: str) -> dict:
    return {
        "report": "UNKNOWN",
        "parameters": {},
        "template": None,
        "confidence": 0.0,
        "message": message,
    }
