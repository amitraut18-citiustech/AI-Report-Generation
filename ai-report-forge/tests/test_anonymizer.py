from ai_report_forge.anonymizer import Anonymizer, remap_narrative
from ai_report_forge.context_loader import PhiMarkers


def _make_phi():
    return PhiMarkers(
        raw={},
        columns=[
            {"table": "Patients", "column": "FirstName", "strategy": "pseudonymize"},
            {"table": "Patients", "column": "LastName", "strategy": "pseudonymize"},
            {"table": "Patients", "column": "DateOfBirth", "strategy": "age_range"},
            {"table": "Patients", "column": "MRN", "strategy": "sequential_id"},
            {"table": "Patients", "column": "SSN", "strategy": "redact"},
            {"table": "Patients", "column": "Address", "strategy": "region_only"},
        ],
    )


def test_pseudonymize_replaces_names():
    anon = Anonymizer(_make_phi())
    rows = [
        {"FirstName": "John", "LastName": "Smith", "Gender": "Male"},
        {"FirstName": "Jane", "LastName": "Doe", "Gender": "Female"},
        {"FirstName": "John", "LastName": "Smith", "Gender": "Male"},
    ]
    result = anon.anonymize(rows, "Patients")

    assert result.anonymized_rows[0]["FirstName"] == "Patient_001"
    assert result.anonymized_rows[0]["LastName"] == "Patient_001"
    assert result.anonymized_rows[1]["FirstName"] == "Patient_002"
    assert result.anonymized_rows[2]["FirstName"] == "Patient_001"
    assert result.anonymized_rows[0]["Gender"] == "Male"


def test_age_range():
    anon = Anonymizer(_make_phi())
    rows = [{"DateOfBirth": "1985-03-15", "Gender": "Male"}]
    result = anon.anonymize(rows, "Patients")

    age_range = result.anonymized_rows[0]["DateOfBirth"]
    assert "-" in age_range
    decade = int(age_range.split("-")[0])
    assert 30 <= decade <= 50


def test_sequential_id():
    anon = Anonymizer(_make_phi())
    rows = [
        {"MRN": "MRN-001", "Gender": "M"},
        {"MRN": "MRN-002", "Gender": "F"},
        {"MRN": "MRN-001", "Gender": "M"},
    ]
    result = anon.anonymize(rows, "Patients")

    assert result.anonymized_rows[0]["MRN"] == "P_001"
    assert result.anonymized_rows[1]["MRN"] == "P_002"
    assert result.anonymized_rows[2]["MRN"] == "P_001"


def test_redact():
    anon = Anonymizer(_make_phi())
    rows = [{"SSN": "123-45-6789", "Gender": "Male"}]
    result = anon.anonymize(rows, "Patients")

    assert result.anonymized_rows[0]["SSN"] == "[REDACTED]"


def test_region_only_state_code():
    anon = Anonymizer(_make_phi())
    rows = [{"Address": "123 Main St, Austin TX", "Gender": "M"}]
    result = anon.anonymize(rows, "Patients")

    assert result.anonymized_rows[0]["Address"] == "TX"


def test_region_only_two_letter_passthrough():
    anon = Anonymizer(_make_phi())
    rows = [{"Address": "CA", "Gender": "M"}]
    result = anon.anonymize(rows, "Patients")

    assert result.anonymized_rows[0]["Address"] == "CA"


def test_none_values_pass_through():
    anon = Anonymizer(_make_phi())
    rows = [{"FirstName": None, "Gender": "Male"}]
    result = anon.anonymize(rows, "Patients")

    assert result.anonymized_rows[0]["FirstName"] is None


def test_unknown_table_passes_through():
    anon = Anonymizer(_make_phi())
    rows = [{"Name": "Test", "Value": 42}]
    result = anon.anonymize(rows, "UnknownTable")

    assert result.anonymized_rows[0]["Name"] == "Test"
    assert result.mapping == {}


def test_remap_narrative():
    mapping = {
        "pseudo:FirstName": {"John": "Patient_001", "Jane": "Patient_002"},
        "seq:MRN": {"MRN-001": "P_001"},
    }
    narrative = "Patient_001 had the highest count. P_001 was admitted first."
    result = remap_narrative(narrative, mapping)

    assert "John" in result
    assert "MRN-001" in result
    assert "Patient_001" not in result
    assert "P_001" not in result
