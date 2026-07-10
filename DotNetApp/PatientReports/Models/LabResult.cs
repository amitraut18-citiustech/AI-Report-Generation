namespace PatientReports.Models;

public class LabResult
{
    public int Id { get; set; }

    public int TransplantEventId { get; set; }
    public TransplantEvent TransplantEvent { get; set; } = null!;

    public string TestName { get; set; } = string.Empty;    // e.g. Hemoglobin
    public double Value { get; set; }
    public string Unit { get; set; } = string.Empty;        // e.g. g/dL
    public double ReferenceLow { get; set; }
    public double ReferenceHigh { get; set; }
    public DateTime TakenDate { get; set; }
}
