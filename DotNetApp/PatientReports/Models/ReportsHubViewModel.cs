namespace PatientReports.Models;

// Backs the unified Reports hub (report dropdown + single Generate button).
// The selected report renders via the RdlView iframe.
public class ReportsHubViewModel
{
    public string? SelectedReport { get; set; }

    // Options for the report dropdown: value -> display label.
    public static readonly (string Value, string Label)[] AvailableReports =
    {
        ("patient", "Patient Report"),
        ("transplant", "Transplant Event Report"),
        ("clinical", "Patient Clinical Summary"),
    };
}
