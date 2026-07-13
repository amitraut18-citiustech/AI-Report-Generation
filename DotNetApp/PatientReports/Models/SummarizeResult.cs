using System.Text.Json;

namespace PatientReports.Models;

public class SummarizeResult
{
    public string Summary { get; set; } = "";
    public string Source { get; set; } = "";
    public bool Anonymized { get; set; }
    public JsonElement? Chart { get; set; }
}
