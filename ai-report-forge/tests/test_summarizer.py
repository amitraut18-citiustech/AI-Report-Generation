from unittest.mock import patch

from ai_report_forge.summarizer import summarize, _quality_check


def test_quality_check_passes_good_summary():
    summary = "The most common blood type is O+ with 142 patients."
    assert _quality_check(summary) is True


def test_quality_check_fails_short_summary():
    assert _quality_check("OK") is False


def test_quality_check_passes_aggregate_summary():
    """Aggregate summaries without verbatim row values should pass."""
    summary = "The data has been analyzed and shows interesting patterns across multiple dimensions."
    assert _quality_check(summary) is True


@patch("ai_report_forge.summarizer.OllamaClient")
def test_summarize_returns_narrative_with_chart(MockClient):
    MockClient.return_value.chat.return_value = {
        "message": {
            "content": '{"summary": "The most common blood type is O+ with 142 patients, representing 29% of the population.", "chart": {"type": "bar", "title": "Blood Types", "labels": ["O+"], "values": [142]}}'
        }
    }
    result = summarize(
        question="Blood type distribution",
        results=[{"BloodType": "O+", "Count": 142}],
        row_count=1,
    )
    assert result["source"] == "ollama"
    assert result["summary"] is not None
    assert "142" in result["summary"]
    assert result["chart"]["type"] == "bar"


@patch("ai_report_forge.summarizer.OllamaClient")
def test_summarize_plain_text_fallback(MockClient):
    MockClient.return_value.chat.return_value = {
        "message": {
            "content": "The most common blood type is O+ with 142 patients."
        }
    }
    result = summarize(
        question="Blood type distribution",
        results=[{"BloodType": "O+", "Count": 142}],
        row_count=1,
    )
    assert result["source"] == "ollama"
    assert "142" in result["summary"]
    assert "chart" not in result


@patch("ai_report_forge.summarizer.OllamaClient")
def test_summarize_flags_failure_on_bad_response(MockClient):
    MockClient.return_value.chat.return_value = {"message": {"content": '{"summary": "Hi"}'}}
    result = summarize(
        question="Blood types",
        results=[{"BloodType": "O+", "Count": 142}],
        row_count=1,
    )
    assert result["summary"] is None
    assert result["error"] == "quality_check_failed"


@patch("ai_report_forge.summarizer.OllamaClient")
def test_summarize_handles_connection_error(MockClient):
    MockClient.return_value.chat.side_effect = ConnectionError("Ollama down")
    result = summarize(
        question="Blood types",
        results=[{"BloodType": "O+", "Count": 142}],
        row_count=1,
    )
    assert result["summary"] is None
    assert result["error"] == "ollama_unavailable"
