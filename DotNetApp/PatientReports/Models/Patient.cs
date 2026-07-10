namespace PatientReports.Models;

public class Patient
{
    public int Id { get; set; }
    public string FirstName { get; set; } = string.Empty;
    public string LastName { get; set; } = string.Empty;
    public string Gender { get; set; } = string.Empty;
    public DateTime DateOfBirth { get; set; }
    public string ContactNumber { get; set; } = string.Empty;
    public string Email { get; set; } = string.Empty;
    public string PhoneNumber { get; set; } = string.Empty;

    public string MRN { get; set; } = string.Empty;         // Medical Record Number
    public string Status { get; set; } = "Active";          // Active, Inactive
    public double HeightCm { get; set; }
    public double WeightKg { get; set; }

    public int FacilityId { get; set; }
    public Facility Facility { get; set; } = null!;

    public ICollection<TransplantEvent> TransplantEvents { get; set; } = new List<TransplantEvent>();
    public ICollection<Diagnosis> Diagnoses { get; set; } = new List<Diagnosis>();
    public ICollection<Medication> Medications { get; set; } = new List<Medication>();
}
