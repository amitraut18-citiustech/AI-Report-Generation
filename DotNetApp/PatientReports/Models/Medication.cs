namespace PatientReports.Models;

public class Medication
{
    public int Id { get; set; }

    public int PatientId { get; set; }
    public Patient Patient { get; set; } = null!;

    public string Name { get; set; } = string.Empty;
    public string Dosage { get; set; } = string.Empty;      // e.g. 500 mg
    public string Frequency { get; set; } = string.Empty;   // e.g. Twice daily
    public DateTime StartDate { get; set; }
    public DateTime? EndDate { get; set; }
    public bool IsActive { get; set; } = true;
}
