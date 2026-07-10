namespace PatientReports.Models;

public class Facility
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string City { get; set; } = string.Empty;
    public string State { get; set; } = string.Empty;
    public string FacilityType { get; set; } = string.Empty; // Hospital, Clinic
    public bool IsActive { get; set; } = true;

    public ICollection<Patient> Patients { get; set; } = new List<Patient>();
    public ICollection<Provider> Providers { get; set; } = new List<Provider>();
}
