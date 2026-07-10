namespace PatientReports.Models;

// Server-side rendering model that mirrors PatientClinicalSummaryReport.rdl:
// grouped Facility -> Patient -> Transplant Event -> Lab result, with the same
// calculated columns (Age, BMI, risk score, lab flags) and facility aggregates.
public class ClinicalSummaryViewModel
{
    public List<FacilitySummary> Facilities { get; set; } = new();
}

public class FacilitySummary
{
    public string FacilityName { get; set; } = string.Empty;
    public string City { get; set; } = string.Empty;
    public string State { get; set; } = string.Empty;

    public List<PatientSummary> Patients { get; set; } = new();

    // Aggregates shown in the "Facility Summary" section.
    public int PatientCount { get; set; }
    public int EventCount { get; set; }
    public int AvgAge { get; set; }
    public int InpatientEvents { get; set; }
    public int OutOfRangeLabs { get; set; }
}

public class PatientSummary
{
    public string PatientName { get; set; } = string.Empty;
    public string MRN { get; set; } = string.Empty;
    public string Gender { get; set; } = string.Empty;
    public int Age { get; set; }
    public double BMI { get; set; }
    public string BmiCategory { get; set; } = string.Empty;
    public int RiskScore { get; set; }
    public string PrimaryDiagnosis { get; set; } = string.Empty;
    public int ActiveMedCount { get; set; }

    public List<EventSummary> Events { get; set; } = new();

    public bool IsHighRisk => RiskScore >= 4;
}

public class EventSummary
{
    public string EventId { get; set; } = string.Empty;
    public DateTime DateOfVisit { get; set; }
    public string ProviderName { get; set; } = string.Empty;
    public string Specialty { get; set; } = string.Empty;
    public string DonorType { get; set; } = string.Empty;
    public bool IsInpatient { get; set; }
    public int DaysSincePreviousVisit { get; set; }

    public List<LabSummary> Labs { get; set; } = new();
}

public class LabSummary
{
    public string TestName { get; set; } = string.Empty;
    public double Value { get; set; }
    public string Unit { get; set; } = string.Empty;
    public double ReferenceLow { get; set; }
    public double ReferenceHigh { get; set; }
    public string Flag { get; set; } = string.Empty;   // OUT or OK

    public bool IsOutOfRange => Flag == "OUT";
}
