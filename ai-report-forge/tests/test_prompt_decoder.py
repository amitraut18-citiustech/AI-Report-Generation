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


# --- filter sanitization guardrails (small-model decode corrections) ---
from ai_report_forge.prompt_decoder import _sanitize_filters


def test_sanitize_flips_inverted_gender_filter():
    filters = [{"table": "Patients", "field": "Gender", "operator": "notEquals", "value": "Female"}]
    _sanitize_filters("Which of our patients are women?", filters)
    assert filters[0]["operator"] == "equals"


def test_sanitize_keeps_explicit_exclusion():
    filters = [{"table": "Patients", "field": "Gender", "operator": "notEquals", "value": "Female"}]
    _sanitize_filters("show all patients except female ones", filters)
    assert filters[0]["operator"] == "notEquals"


def test_sanitize_moves_bare_city_to_city_field():
    filters = [{"table": "Facilities", "field": "Name", "operator": "equals", "value": "Dallas"}]
    _sanitize_filters("clinical summary for patients in Dallas", filters)
    assert filters[0]["field"] == "City"


def test_sanitize_keeps_full_facility_name():
    filters = [{"table": "Facilities", "field": "Name", "operator": "equals", "value": "Austin General Hospital"}]
    _sanitize_filters("patients from Austin General Hospital", filters)
    assert filters[0]["field"] == "Name"


def test_sanitize_drops_hallucinated_inpatient_filter():
    filters = [
        {"table": "TransplantEvents", "field": "IsInpatient", "operator": "equals", "value": "false"},
        {"table": "TransplantEvents", "field": "DonorType", "operator": "notEquals", "value": "Autologous"},
    ]
    _sanitize_filters("exclude autologous transplant events", filters)
    assert len(filters) == 1
    assert filters[0]["field"] == "DonorType"


def test_sanitize_keeps_justified_inpatient_filter():
    filters = [{"table": "TransplantEvents", "field": "IsInpatient", "operator": "equals", "value": "false"}]
    _sanitize_filters("show outpatient transplant events", filters)
    assert len(filters) == 1


def test_sanitize_keeps_justified_status_filter():
    filters = [{"table": "Patients", "field": "Status", "operator": "equals", "value": "Inactive"}]
    _sanitize_filters("show me inactive patients", filters)
    assert len(filters) == 1
