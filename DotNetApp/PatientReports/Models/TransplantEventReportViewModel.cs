namespace PatientReports.Models;

public class TransplantEventReportViewModel
{
    public string PatientName { get; set; } = string.Empty;
    public DateTime DateOfVisit { get; set; }
    public DateTime DateOfPreviousVisit { get; set; }
    public DateTime TransplantDate { get; set; }
    public DateTime InfusionDate { get; set; }
    public string EventId { get; set; } = string.Empty;
    public string TransplantNumber { get; set; } = string.Empty;
    public string DonorType { get; set; } = string.Empty;
    public string IsInpatient { get; set; } = string.Empty;
}
