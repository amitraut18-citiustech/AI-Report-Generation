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
         "columns": [{"name": "BloodType", "type": "string", "description": "Blood type"},
                      {"name": "Gender", "type": "string", "description": "Gender"}]}
    ])
    return ctx


def test_parse_valid_json_with_query():
    raw = '{"report": "patient", "query": {"entity": "Patients", "joins": [], "filters": [{"table": "Patients", "field": "Gender", "operator": "equals", "value": "Female"}]}, "parameters": {}, "template": "patient.html", "confidence": 0.92}'
    result = _parse_response(raw)
    assert result["report"] == "patient"
    assert result["confidence"] == 0.92
    assert result["query"]["entity"] == "Patients"
    assert len(result["query"]["filters"]) == 1
    assert result["query"]["filters"][0]["table"] == "Patients"
    assert result["query"]["filters"][0]["field"] == "Gender"


def test_parse_json_with_joins():
    raw = '{"report": "patient", "query": {"entity": "Patients", "joins": [{"table": "Facilities", "localKey": "FacilityId", "foreignKey": "Id"}], "filters": [{"table": "Facilities", "field": "Name", "operator": "contains", "value": "Austin"}]}, "template": "patient.html", "confidence": 0.95}'
    result = _parse_response(raw)
    assert len(result["query"]["joins"]) == 1
    assert result["query"]["joins"][0]["table"] == "Facilities"
    assert result["query"]["filters"][0]["table"] == "Facilities"
    assert result["query"]["filters"][0]["field"] == "Name"


def test_parse_json_no_query():
    raw = '{"report": "patient", "parameters": {}, "template": "patient.html", "confidence": 0.85}'
    result = _parse_response(raw)
    assert result["report"] == "patient"
    assert result["query"]["entity"] == ""
    assert result["query"]["filters"] == []
    assert result["query"]["joins"] == []


def test_parse_json_in_code_block():
    raw = '```json\n{"report": "patient", "query": {"entity": "Patients", "joins": [], "filters": []}, "template": "patient.html", "confidence": 0.85}\n```'
    result = _parse_response(raw)
    assert result["report"] == "patient"


def test_parse_invalid_json_returns_unknown():
    raw = "I think you should look at the patient report"
    result = _parse_response(raw)
    assert result["report"] == "UNKNOWN"
    assert result["confidence"] == 0.0
    assert result["query"]["filters"] == []


def test_parse_malformed_filters_ignored():
    raw = '{"report": "patient", "query": {"entity": "Patients", "joins": [], "filters": [{"field": "Name"}, {"bad": true}]}, "template": "patient.html", "confidence": 0.8}'
    result = _parse_response(raw)
    assert result["query"]["filters"] == []


@patch("ai_report_forge.prompt_decoder.OllamaClient")
def test_decode_calls_ollama(MockClient):
    mock_instance = MockClient.return_value
    mock_instance.chat.return_value = {
        "message": {
            "content": '{"report": "patient", "query": {"entity": "Patients", "joins": [], "filters": []}, "template": "patient.html", "confidence": 0.9}'
        }
    }
    ctx = _make_ctx()
    result = decode_prompt("Show patients", ctx)

    assert result["report"] == "patient"
    mock_instance.chat.assert_called_once()


@patch("ai_report_forge.prompt_decoder.OllamaClient")
def test_decode_handles_ollama_failure(MockClient):
    MockClient.return_value.chat.side_effect = ConnectionError("Ollama down")
    ctx = _make_ctx()
    result = decode_prompt("Show patients", ctx)

    assert result["report"] == "UNKNOWN"
    assert "message" in result
    assert result["query"]["filters"] == []
