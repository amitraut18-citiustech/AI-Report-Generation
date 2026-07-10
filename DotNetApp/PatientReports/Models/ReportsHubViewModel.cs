namespace PatientReports.Models;

// Backs the unified Reports hub (report dropdown + single Generate button).
// Only the selected report's data is populated.
public class ReportsHubViewModel
{
    public string? SelectedReport { get; set; }

    public List<PatientReportViewModel>? PatientRows { get; set; }
    public List<TransplantEventReportViewModel>? TransplantRows { get; set; }
    public ClinicalSummaryViewModel? Clinical { get; set; }

    // Options for the report dropdown: value -> display label.
    public static readonly (string Value, string Label)[] AvailableReports =
    {
        ("patient", "Patient Report"),
        ("transplant", "Transplant Event Report"),
        ("clinical", "Patient Clinical Summary"),
    };
}
