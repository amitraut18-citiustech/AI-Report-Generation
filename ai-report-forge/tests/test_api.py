from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from ai_report_forge.context_loader import AppContext, ReportEntry, SchemaContext, PhiMarkers


@pytest.fixture
def client():
    with patch("ai_report_forge.api.load_context") as mock_load:
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
            {"name": "Patients", "description": "Patients", "reportable": True,
             "columns": [{"name": "BloodType"}]}
        ])
        ctx.phi = PhiMarkers(raw={}, columns=[
            {"table": "Patients", "column": "FirstName", "strategy": "pseudonymize"},
        ])
        mock_load.return_value = ctx

        from ai_report_forge.api import app
        with TestClient(app) as c:
            yield c


@patch("ai_report_forge.prompt_decoder.OllamaClient")
def test_decode_prompt_endpoint(MockClient, client):
    MockClient.return_value.chat.return_value = {
        "message": {
            "content": '{"report": "blood_type_distribution", "parameters": {}, "template": "blood_type_distribution.html", "confidence": 0.9}'
        }
    }
    resp = client.post("/decode-prompt", json={"question": "Show blood types"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["report"] == "blood_type_distribution"
    assert data["confidence"] == 0.9


@patch("ai_report_forge.summarizer.OllamaClient")
def test_summarize_endpoint(MockClient, client):
    MockClient.return_value.chat.return_value = {
        "message": {
            "content": "The most common blood type is O+ with 142 patients."
        }
    }
    resp = client.post("/summarize", json={
        "question": "Blood type distribution",
        "results": [{"BloodType": "O+", "Count": 142}],
        "row_count": 1,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "ollama"
    assert "142" in data["summary"]


def test_decode_prompt_empty_question(client):
    resp = client.post("/decode-prompt", json={"question": ""})
    assert resp.status_code == 422


@patch("ai_report_forge.api.OllamaClient")
def test_health_endpoint(MockClient, client):
    MockClient.return_value.list.return_value = {"models": []}
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["reports_loaded"] == 1
