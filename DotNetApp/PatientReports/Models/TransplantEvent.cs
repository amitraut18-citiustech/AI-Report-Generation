namespace PatientReports.Models;

public class TransplantEvent
{
    public int Id { get; set; }
    public int PatientId { get; set; }
    public DateTime DateOfVisit { get; set; }
    public DateTime DateOfPreviousVisit { get; set; }
    public DateTime TransplantDate { get; set; }
    public DateTime InfusionDate { get; set; }
    public string EventId { get; set; } = string.Empty;
    public string TransplantNumber { get; set; } = string.Empty;
    public bool IsInpatient { get; set; }

    public Patient Patient { get; set; } = null!;
}
