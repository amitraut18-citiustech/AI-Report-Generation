namespace PatientReports.Models;

// Backs the unified Reports hub (report dropdown + single Generate button).
// The selected report renders via the RdlView iframe.
public class ReportsHubViewModel
{
    public string? SelectedReport { get; set; }

    // Visit-date range filter (transplant + clinical reports).
    public string? FromDate { get; set; }
    public string? ToDate { get; set; }

    // Patient age range filter (clinical report only).
    public string? MinAge { get; set; }
    public string? MaxAge { get; set; }

    public string? Question { get; set; }
    public string? BrainError { get; set; }

    /// <summary>Which model decoded the question: "ollama" or "claude".</summary>
    public string? DecodedBy { get; set; }
    public List<QueryFilter> AppliedFilters { get; set; } = new();

    /// <summary>
    /// Base64-encoded QuerySpec JSON, passed via query string so it survives
    /// the redirect chain and reaches the iframe request (unlike TempData,
    /// which is cookie-based and races with the iframe's HTTP request).
    /// </summary>
    public string? QuerySpecB64 { get; set; }

    public static readonly (string Value, string Label)[] AvailableReports =
    {
        ("patient", "Patient Report"),
        ("transplant", "Transplant Event Report"),
        ("clinical", "Patient Clinical Summary"),
    };
}
