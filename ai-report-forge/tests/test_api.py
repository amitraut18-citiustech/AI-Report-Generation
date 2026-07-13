from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from ai_report_forge.context_loader import AppContext, ReportEntry, SchemaContext, PhiMarkers


@pytest.fixture
def client():
    with patch("ai_report_forge.api.load_context") as mock_load:
        ctx = AppContext()
        ctx.reports["patient"] = ReportEntry(
            report_key="patient",
            title="Patient Report",
            thought_content="...",
            template_file="patient.html",
            fields=[],
            parameters=[],
        )
        ctx.schema = SchemaContext(raw={}, tables=[
            {"name": "Patients", "description": "Patients", "reportable": True,
             "columns": [{"name": "FirstName", "type": "string", "description": "First name"}]}
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
            "content": '{"report": "patient", "query": {"entity": "Patients", "joins": [], "filters": []}, "template": "patient.html", "confidence": 0.9}'
        }
    }
    resp = client.post("/decode-prompt", json={"question": "Show patients"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["report"] == "patient"
    assert data["confidence"] == 0.9
    assert data["query"]["entity"] == "Patients"


@patch("ai_report_forge.prompt_decoder.OllamaClient")
def test_decode_prompt_with_filters(MockClient, client):
    MockClient.return_value.chat.return_value = {
        "message": {
            "content": '{"report": "patient", "query": {"entity": "Patients", "joins": [], "filters": [{"table": "Patients", "field": "FirstName", "operator": "contains", "value": "Ethan"}]}, "template": "patient.html", "confidence": 0.95}'
        }
    }
    resp = client.post("/decode-prompt", json={"question": "Show patients named Ethan"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["report"] == "patient"
    assert len(data["query"]["filters"]) == 1
    assert data["query"]["filters"][0]["table"] == "Patients"
    assert data["query"]["filters"][0]["field"] == "FirstName"


@patch("ai_report_forge.prompt_decoder.OllamaClient")
def test_decode_prompt_with_join(MockClient, client):
    MockClient.return_value.chat.return_value = {
        "message": {
            "content": '{"report": "patient", "query": {"entity": "Patients", "joins": [{"table": "Facilities", "localKey": "FacilityId", "foreignKey": "Id"}], "filters": [{"table": "Facilities", "field": "Name", "operator": "contains", "value": "Austin"}]}, "template": "patient.html", "confidence": 0.9}'
        }
    }
    resp = client.post("/decode-prompt", json={"question": "Patients at Austin General"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["query"]["joins"]) == 1
    assert data["query"]["joins"][0]["table"] == "Facilities"


@patch("ai_report_forge.summarizer.OllamaClient")
def test_summarize_endpoint(MockClient, client):
    MockClient.return_value.chat.return_value = {
        "message": {
            "content": '{"summary": "The most common blood type is O+ with 142 patients.", "chart": {"type": "bar", "title": "By Blood Type", "labels": ["O+"], "values": [142]}}'
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
    assert data["chart"]["type"] == "bar"


@patch("ai_report_forge.summarizer.OllamaClient")
def test_summarize_no_chart(MockClient, client):
    MockClient.return_value.chat.return_value = {
        "message": {
            "content": '{"summary": "Only one patient found with blood type O+.", "chart": null}'
        }
    }
    resp = client.post("/summarize", json={
        "question": "Blood types",
        "results": [{"BloodType": "O+", "Count": 1}],
        "row_count": 1,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["chart"] is None


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
