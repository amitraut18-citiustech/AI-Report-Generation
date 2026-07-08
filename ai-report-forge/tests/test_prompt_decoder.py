from unittest.mock import patch

from ai_report_forge.context_loader import AppContext, ReportEntry, SchemaContext
from ai_report_forge.prompt_decoder import decode_prompt, _parse_response


def _make_ctx():
    ctx = AppContext()
    ctx.reports["blood_type_distribution"] = ReportEntry(
        report_key="blood_type_distribution",
        title="Blood Type Distribution",
        thought_content="...",
        template_file="blood_type_distribution.html",
        fields=[],
        parameters=[],
    )
    ctx.schema = SchemaContext(raw={}, tables=[
        {"name": "Patients", "description": "Patient records", "reportable": True,
         "columns": [{"name": "BloodType"}, {"name": "Gender"}]}
    ])
    return ctx


def test_parse_valid_json():
    raw = '{"report": "blood_type_distribution", "parameters": {}, "template": "blood_type_distribution.html", "confidence": 0.92}'
    result = _parse_response(raw)
    assert result["report"] == "blood_type_distribution"
    assert result["confidence"] == 0.92
    assert result["template"] == "blood_type_distribution.html"


def test_parse_json_in_code_block():
    raw = '```json\n{"report": "patient_demographics", "parameters": {}, "template": "patient_demographics.html", "confidence": 0.85}\n```'
    result = _parse_response(raw)
    assert result["report"] == "patient_demographics"


def test_parse_invalid_json_returns_unknown():
    raw = "I think you should look at the blood type report"
    result = _parse_response(raw)
    assert result["report"] == "UNKNOWN"
    assert result["confidence"] == 0.0


@patch("ai_report_forge.prompt_decoder.ollama")
def test_decode_calls_ollama(mock_ollama):
    mock_ollama.chat.return_value = {
        "message": {
            "content": '{"report": "blood_type_distribution", "parameters": {}, "template": "blood_type_distribution.html", "confidence": 0.9}'
        }
    }
    ctx = _make_ctx()
    result = decode_prompt("Show blood types", ctx)

    assert result["report"] == "blood_type_distribution"
    mock_ollama.chat.assert_called_once()


@patch("ai_report_forge.prompt_decoder.ollama")
def test_decode_handles_ollama_failure(mock_ollama):
    mock_ollama.chat.side_effect = ConnectionError("Ollama down")
    ctx = _make_ctx()
    result = decode_prompt("Show blood types", ctx)

    assert result["report"] == "UNKNOWN"
    assert "message" in result
