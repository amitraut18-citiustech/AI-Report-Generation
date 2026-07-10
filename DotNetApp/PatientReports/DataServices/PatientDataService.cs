using Microsoft.EntityFrameworkCore;
using PatientReports.Data;
using PatientReports.Models;

namespace PatientReports.DataServices;

public class PatientDataService
{
    private readonly ApplicationDbContext _context;

    public PatientDataService(ApplicationDbContext context)
    {
        _context = context;
    }

    public async Task<List<PatientReportViewModel>> GetPatientReportAsync()
    {
        return await _context.Patients
            .AsNoTracking()
            .Select(p => new PatientReportViewModel
            {
                FirstName = p.FirstName,
                LastName = p.LastName,
                Gender = p.Gender,
                DateOfBirth = p.DateOfBirth,
                ContactNumber = p.ContactNumber,
                Email = p.Email,
                PhoneNumber = p.PhoneNumber
            })
            .OrderBy(p => p.LastName)
            .ToListAsync();
    }

    public async Task<List<TransplantEventReportViewModel>> GetTransplantEventReportAsync()
    {
        return await _context.TransplantEvents
            .AsNoTracking()
            .Include(e => e.Patient)
            .Select(e => new TransplantEventReportViewModel
            {
                PatientName = e.Patient.FirstName + " " + e.Patient.LastName,
                DateOfVisit = e.DateOfVisit,
                DateOfPreviousVisit = e.DateOfPreviousVisit,
                TransplantDate = e.TransplantDate,
                InfusionDate = e.InfusionDate,
                EventId = e.EventId,
                TransplantNumber = e.TransplantNumber,
                IsInpatient = e.IsInpatient ? "Yes" : "No"
            })
            .OrderBy(e => e.DateOfVisit)
            .ToListAsync();
    }

    // Mirrors PatientClinicalSummaryReport.rdl: a multi-table graph grouped
    // Facility -> Patient -> Event -> Lab, with the same calculated columns.
    public async Task<ClinicalSummaryViewModel> GetClinicalSummaryAsync()
    {
        var facilities = await _context.Facilities
            .AsNoTracking()
            .Include(f => f.Patients).ThenInclude(p => p.TransplantEvents).ThenInclude(te => te.Provider)
            .Include(f => f.Patients).ThenInclude(p => p.TransplantEvents).ThenInclude(te => te.LabResults)
            .Include(f => f.Patients).ThenInclude(p => p.Diagnoses)
            .Include(f => f.Patients).ThenInclude(p => p.Medications)
            .OrderBy(f => f.Name)
            .ToListAsync();

        var model = new ClinicalSummaryViewModel();

        foreach (var f in facilities)
        {
            var fs = new FacilitySummary
            {
                FacilityName = f.Name,
                City = f.City,
                State = f.State
            };

            foreach (var p in f.Patients.OrderBy(p => p.LastName).ThenBy(p => p.FirstName))
            {
                var age = CalculateAge(p.DateOfBirth);
                var bmi = p.HeightCm > 0
                    ? Math.Round(p.WeightKg / Math.Pow(p.HeightCm / 100.0, 2), 1)
                    : 0;

                var ps = new PatientSummary
                {
                    PatientName = p.FirstName + " " + p.LastName,
                    MRN = p.MRN,
                    Gender = p.Gender,
                    Age = age,
                    BMI = bmi,
                    BmiCategory = BmiCategory(bmi),
                    PrimaryDiagnosis = PrimaryDiagnosis(p),
                    ActiveMedCount = p.Medications.Count(m => m.IsActive)
                };

                var anyInpatient = false;
                var patientOutOfRange = 0;

                foreach (var te in p.TransplantEvents.OrderBy(te => te.DateOfVisit))
                {
                    if (te.IsInpatient) anyInpatient = true;

                    var es = new EventSummary
                    {
                        EventId = te.EventId,
                        DateOfVisit = te.DateOfVisit,
                        ProviderName = te.Provider != null ? te.Provider.FirstName + " " + te.Provider.LastName : "-",
                        Specialty = te.Provider?.Specialty ?? string.Empty,
                        DonorType = te.DonorType,
                        IsInpatient = te.IsInpatient,
                        DaysSincePreviousVisit = (te.DateOfVisit - te.DateOfPreviousVisit).Days
                    };

                    foreach (var lr in te.LabResults.OrderBy(l => l.TestName))
                    {
                        var outOfRange = lr.Value < lr.ReferenceLow || lr.Value > lr.ReferenceHigh;
                        if (outOfRange) patientOutOfRange++;

                        es.Labs.Add(new LabSummary
                        {
                            TestName = lr.TestName,
                            Value = lr.Value,
                            Unit = lr.Unit,
                            ReferenceLow = lr.ReferenceLow,
                            ReferenceHigh = lr.ReferenceHigh,
                            Flag = outOfRange ? "OUT" : "OK"
                        });
                    }

                    ps.Events.Add(es);
                    fs.EventCount++;
                    if (te.IsInpatient) fs.InpatientEvents++;
                }

                ps.RiskScore = RiskScore(age, anyInpatient, patientOutOfRange);
                fs.OutOfRangeLabs += patientOutOfRange;
                fs.Patients.Add(ps);
            }

            fs.PatientCount = fs.Patients.Count;
            fs.AvgAge = fs.Patients.Count > 0
                ? (int)Math.Round(fs.Patients.Average(x => x.Age))
                : 0;

            model.Facilities.Add(fs);
        }

        return model;
    }

    private static int CalculateAge(DateTime dob)
    {
        var today = DateTime.Today;
        var age = today.Year - dob.Year;
        if (dob.Date > today.AddYears(-age)) age--;
        return age;
    }

    private static string BmiCategory(double bmi)
    {
        if (bmi == 0) return "N/A";
        if (bmi < 18.5) return "Underweight";
        if (bmi < 25) return "Normal";
        if (bmi < 30) return "Overweight";
        return "Obese";
    }

    private static int RiskScore(int age, bool inpatient, int outOfRangeLabs)
    {
        var score = 0;
        if (age >= 65) score += 2;
        else if (age >= 45) score += 1;
        if (inpatient) score += 2;
        score += outOfRangeLabs;
        return score;
    }

    private static string PrimaryDiagnosis(Patient p)
    {
        int Rank(string severity) => severity switch
        {
            "Severe" => 3,
            "Moderate" => 2,
            _ => 1
        };

        var dx = p.Diagnoses
            .OrderByDescending(d => Rank(d.Severity))
            .ThenByDescending(d => d.DiagnosedDate)
            .FirstOrDefault();

        return dx?.Description ?? "-";
    }
}
