from unittest.mock import patch

from ai_report_forge.summarizer import summarize, _quality_check


def test_quality_check_passes_good_summary():
    results = [{"BloodType": "O+", "Count": 142}]
    summary = "The most common blood type is O+ with 142 patients."
    assert _quality_check(summary, results) is True


def test_quality_check_fails_short_summary():
    results = [{"BloodType": "O+", "Count": 142}]
    assert _quality_check("OK", results) is False


def test_quality_check_fails_no_data_reference():
    results = [{"BloodType": "O+", "Count": 142}]
    summary = "The data has been analyzed and shows interesting patterns across multiple dimensions."
    assert _quality_check(summary, results) is False


@patch("ai_report_forge.summarizer.ollama")
def test_summarize_returns_narrative(mock_ollama):
    mock_ollama.chat.return_value = {
        "message": {
            "content": "The most common blood type is O+ with 142 patients, representing 29% of the population."
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


@patch("ai_report_forge.summarizer.ollama")
def test_summarize_flags_failure_on_bad_response(mock_ollama):
    mock_ollama.chat.return_value = {"message": {"content": "Hi"}}
    result = summarize(
        question="Blood types",
        results=[{"BloodType": "O+", "Count": 142}],
        row_count=1,
    )
    assert result["summary"] is None
    assert result["error"] == "quality_check_failed"


@patch("ai_report_forge.summarizer.ollama")
def test_summarize_handles_connection_error(mock_ollama):
    mock_ollama.chat.side_effect = ConnectionError("Ollama down")
    result = summarize(
        question="Blood types",
        results=[{"BloodType": "O+", "Count": 142}],
        row_count=1,
    )
    assert result["summary"] is None
    assert result["error"] == "ollama_unavailable"
