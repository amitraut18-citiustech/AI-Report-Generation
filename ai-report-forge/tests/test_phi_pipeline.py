"""Regression tests for the real .NET -> Python PHI pipeline.

The .NET client serializes row keys in camelCase (firstName, patientName, mrn)
while phi-markers.json uses PascalCase. These tests exercise the wire shape
production actually sends, which the original case-sensitive lookup missed.
"""
from ai_report_forge.anonymizer import Anonymizer, remap_narrative, scrub_text
from ai_report_forge.context_loader import PhiMarkers


def _markers():
    return PhiMarkers(columns=[
        {"table": "Patients", "column": "FirstName", "strategy": "pseudonymize"},
        {"table": "Patients", "column": "LastName", "strategy": "pseudonymize"},
        {"table": "Patients", "column": "DateOfBirth", "strategy": "age_range"},
        {"table": "Patients", "column": "Email", "strategy": "redact"},
        {"table": "Patients", "column": "MRN", "strategy": "sequential_id"},
        {"table": "_viewmodel", "column": "PatientName", "strategy": "pseudonymize"},
        {"table": "_viewmodel", "column": "Mrn", "strategy": "sequential_id"},
    ])


def test_camelcase_rows_are_anonymized():
    rows = [{
        "firstName": "John",
        "lastName": "Smith",
        "dateOfBirth": "1980-05-01T00:00:00",
        "email": "john@example.com",
        "mrn": "MRN-001",
        "gender": "Male",
    }]
    result = Anonymizer(_markers()).anonymize(rows, "Patients")
    row = result.anonymized_rows[0]
    assert row["firstName"].startswith("Patient_")
    assert row["lastName"].startswith("Patient_")
    assert row["email"] == "[REDACTED]"
    assert row["mrn"].startswith("P_")
    assert "-" in row["dateOfBirth"] and "1980" not in row["dateOfBirth"]
    assert row["gender"] == "Male"
    # No original PHI value survives anywhere in the payload
    flat = str(result.anonymized_rows)
    for phi in ("John", "Smith", "john@example.com", "MRN-001", "1980"):
        assert phi not in flat


def test_camelcase_viewmodel_rows_are_anonymized():
    rows = [{"patientName": "Ethan Brooks", "mrn": "MRN-77", "isInpatient": "Yes"}]
    result = Anonymizer(_markers()).anonymize(rows, "TransplantEvents")
    row = result.anonymized_rows[0]
    assert row["patientName"].startswith("Patient_")
    assert row["mrn"].startswith("P_")


def test_unconfigured_sensitive_column_falls_back_to_redaction():
    # phoneNumber has no marker in _markers(); the safety-net pattern catches it.
    rows = [{"phoneNumber": "555-1234", "facilityName": "General Hospital"}]
    result = Anonymizer(_markers()).anonymize(rows, "Patients")
    assert result.anonymized_rows[0]["phoneNumber"] == "[REDACTED]"
    # Non-identifier columns are untouched
    assert result.anonymized_rows[0]["facilityName"] == "General Hospital"


def test_question_scrubbing_replaces_known_phi():
    rows = [{"firstName": "John", "lastName": "Smith"}]
    result = Anonymizer(_markers()).anonymize(rows, "Patients")
    scrubbed = scrub_text("show me john Smith's visit history", result.mapping)
    assert "john" not in scrubbed.lower().replace("patient_", "")
    assert "Smith" not in scrubbed
    assert "Patient_" in scrubbed


def test_remap_narrative_handles_backslash_in_original():
    mapping = {"pseudo:Patient:FirstName": {r"O\1Brien": "Patient_001"}}
    out = remap_narrative("Patient_001 was seen twice.", mapping)
    assert out == r"O\1Brien was seen twice."
