namespace PatientReports.Models;

public class Diagnosis
{
    public int Id { get; set; }

    public int PatientId { get; set; }
    public Patient Patient { get; set; } = null!;

    public string IcdCode { get; set; } = string.Empty;     // e.g. C90.0
    public string Description { get; set; } = string.Empty;
    public string Severity { get; set; } = string.Empty;    // Mild, Moderate, Severe
    public DateTime DiagnosedDate { get; set; }
}
