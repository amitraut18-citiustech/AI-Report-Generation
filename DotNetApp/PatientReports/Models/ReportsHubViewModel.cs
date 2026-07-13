namespace PatientReports.Models;

// Backs the unified Reports hub (report dropdown + single Generate button).
// The selected report renders via the RdlView iframe.
public class ReportsHubViewModel
{
    public string? SelectedReport { get; set; }

    // Visit-date range filter, applied by the transplant report's RDL Filter.
    public string? FromDate { get; set; }
    public string? ToDate { get; set; }

    // Options for the report dropdown: value -> display label.
    public static readonly (string Value, string Label)[] AvailableReports =
    {
        ("patient", "Patient Report"),
        ("transplant", "Transplant Event Report"),
        ("clinical", "Patient Clinical Summary"),
    };
}
