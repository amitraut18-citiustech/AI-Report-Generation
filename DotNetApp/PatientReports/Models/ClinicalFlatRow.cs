namespace PatientReports.Models;

// Flat, denormalized row (one per lab result; lab fields null when an event has
// no labs) matching the window.REPORT_DATA contract expected by the generated
// patient_clinical_summary.js template. Property names serialize to the exact
// camelCase keys the template reads (note: "Mrn" -> "mrn").
public class ClinicalFlatRow
{
    public string FacilityName { get; set; } = string.Empty;
    public string FacilityCity { get; set; } = string.Empty;
    public string FacilityState { get; set; } = string.Empty;

    public int PatientId { get; set; }
    public string Mrn { get; set; } = string.Empty;
    public string PatientName { get; set; } = string.Empty;
    public string Gender { get; set; } = string.Empty;
    public DateTime DateOfBirth { get; set; }
    public double HeightCm { get; set; }
    public double WeightKg { get; set; }
    public string Status { get; set; } = string.Empty;

    public string EventId { get; set; } = string.Empty;
    public string DonorType { get; set; } = string.Empty;
    public DateTime DateOfVisit { get; set; }
    public DateTime DateOfPreviousVisit { get; set; }
    public bool IsInpatient { get; set; }

    public string ProviderName { get; set; } = string.Empty;
    public string Specialty { get; set; } = string.Empty;

    public string PrimaryDiagnosis { get; set; } = string.Empty;
    public int ActiveMedCount { get; set; }

    // Lab columns are null for events with no labs (LEFT JOIN semantics).
    public string? LabTestName { get; set; }
    public double? LabValue { get; set; }
    public string? LabUnit { get; set; }
    public double? RefLow { get; set; }
    public double? RefHigh { get; set; }
}
