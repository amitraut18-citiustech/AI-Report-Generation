using Microsoft.EntityFrameworkCore;
using PatientReports.Data;
using PatientReports.Models;

namespace PatientReports.DataServices;

public class PatientDataService
{
    private readonly ApplicationDbContext _context;
    private readonly ILogger<PatientDataService> _logger;

    public PatientDataService(ApplicationDbContext context, ILogger<PatientDataService> logger)
    {
        _context = context;
        _logger = logger;
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
                DonorType = e.DonorType,
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

    // Flat, denormalized result set (one row per lab; lab fields null when an
    // event has no labs) that feeds the generated patient_clinical_summary.js
    // template via window.REPORT_DATA. This is the same multi-table graph the
    // SSRS report queries, projected to the template's row contract.
    // Optional filters (used by the SSRS/RDL report path). Rows are filtered here
    // because the RDL is rendered with fed data (its SQL WHERE never executes).
    // fromDate/toDate filter the visit date; minAge/maxAge filter patient age;
    // status filters patient status ("All" or null = no status filter).
    public async Task<List<ClinicalFlatRow>> GetClinicalFlatRowsAsync(
        DateTime? fromDate = null, DateTime? toDate = null,
        int? minAge = null, int? maxAge = null, string? status = null)
    {
        var events = await _context.TransplantEvents
            .AsNoTracking()
            .Include(e => e.Provider)
            .Include(e => e.LabResults)
            .Include(e => e.Patient).ThenInclude(p => p.Facility)
            .Include(e => e.Patient).ThenInclude(p => p.Diagnoses)
            .Include(e => e.Patient).ThenInclude(p => p.Medications)
            .ToListAsync();

        var rows = new List<ClinicalFlatRow>();

        foreach (var e in events)
        {
            var p = e.Patient;

            // Apply the report filters.
            if (fromDate.HasValue && e.DateOfVisit < fromDate.Value) continue;
            if (toDate.HasValue && e.DateOfVisit > toDate.Value) continue;

            var patientAge = CalculateAge(p.DateOfBirth);
            if (minAge.HasValue && patientAge < minAge.Value) continue;
            if (maxAge.HasValue && patientAge > maxAge.Value) continue;

            if (!string.IsNullOrEmpty(status) && status != "All" &&
                !string.Equals(p.Status, status, StringComparison.OrdinalIgnoreCase)) continue;

            var f = p.Facility;
            var primaryDx = PrimaryDiagnosis(p);
            var activeMeds = p.Medications.Count(m => m.IsActive);
            var providerName = e.Provider != null ? e.Provider.FirstName + " " + e.Provider.LastName : "-";
            var specialty = e.Provider?.Specialty ?? string.Empty;

            ClinicalFlatRow Base() => new ClinicalFlatRow
            {
                FacilityName = f.Name,
                FacilityCity = f.City,
                FacilityState = f.State,
                PatientId = p.Id,
                Mrn = p.MRN,
                PatientName = p.FirstName + " " + p.LastName,
                Gender = p.Gender,
                DateOfBirth = p.DateOfBirth,
                HeightCm = p.HeightCm,
                WeightKg = p.WeightKg,
                Status = p.Status,
                EventId = e.EventId,
                DonorType = e.DonorType,
                DateOfVisit = e.DateOfVisit,
                DateOfPreviousVisit = e.DateOfPreviousVisit,
                IsInpatient = e.IsInpatient,
                ProviderName = providerName,
                Specialty = specialty,
                PrimaryDiagnosis = primaryDx,
                ActiveMedCount = activeMeds
            };

            if (e.LabResults.Any())
            {
                foreach (var lr in e.LabResults.OrderBy(l => l.TestName))
                {
                    var row = Base();
                    row.LabTestName = lr.TestName;
                    row.LabValue = lr.Value;
                    row.LabUnit = lr.Unit;
                    row.RefLow = lr.ReferenceLow;
                    row.RefHigh = lr.ReferenceHigh;
                    rows.Add(row);
                }
            }
            else
            {
                rows.Add(Base()); // event with no labs (LEFT JOIN)
            }
        }

        return rows;
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
