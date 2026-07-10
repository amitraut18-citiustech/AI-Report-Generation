namespace PatientReports.Models;

public class Provider
{
    public int Id { get; set; }
    public string FirstName { get; set; } = string.Empty;
    public string LastName { get; set; } = string.Empty;
    public string Specialty { get; set; } = string.Empty;
    public string NPI { get; set; } = string.Empty; // National Provider Identifier

    public int FacilityId { get; set; }
    public Facility Facility { get; set; } = null!;

    public ICollection<TransplantEvent> TransplantEvents { get; set; } = new List<TransplantEvent>();
}
