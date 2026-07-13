from ai_report_forge.stats import compute_stats


def test_empty_rows():
    assert compute_stats([]) == "Total rows: 0"


def test_categorical_breakdown():
    rows = [
        {"gender": "Female", "status": "Active"},
        {"gender": "Female", "status": "Active"},
        {"gender": "Male", "status": "Inactive"},
    ]
    out = compute_stats(rows)
    assert "Total rows: 3" in out
    assert "gender breakdown: Female: 2, Male: 1" in out
    assert "status breakdown: Active: 2, Inactive: 1" in out


def test_skips_identifier_and_unique_columns():
    rows = [
        {"mrn": "P_001", "patientId": 1, "firstName": "Patient_001"},
        {"mrn": "P_002", "patientId": 2, "firstName": "Patient_002"},
        {"mrn": "P_003", "patientId": 3, "firstName": "Patient_003"},
    ]
    out = compute_stats(rows)
    assert "mrn" not in out
    assert "patientId" not in out
    # firstName is unique per row -> not a useful category
    assert "firstName breakdown" not in out


def test_date_range():
    rows = [
        {"dateOfVisit": "2026-03-10T00:00:00"},
        {"dateOfVisit": "2026-01-15T00:00:00"},
    ]
    out = compute_stats(rows)
    assert "dateOfVisit: earliest 2026-01-15, latest 2026-03-10" in out


def test_skips_fully_redacted_columns():
    rows = [{"email": "[REDACTED]"}, {"email": "[REDACTED]"}]
    out = compute_stats(rows)
    assert "email" not in out


def test_bool_breakdown():
    rows = [{"isInpatient": True}, {"isInpatient": True}, {"isInpatient": False}]
    out = compute_stats(rows)
    assert "isInpatient breakdown: True: 2, False: 1" in out
