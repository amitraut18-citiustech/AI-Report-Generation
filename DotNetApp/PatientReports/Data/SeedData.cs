using Microsoft.EntityFrameworkCore;
using PatientReports.Models;

namespace PatientReports.Data;

public static class SeedData
{
    public static async Task InitializeAsync(IServiceProvider serviceProvider)
    {
        using var scope = serviceProvider.CreateScope();
        var context = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();

        await context.Database.EnsureDeletedAsync();
        await context.Database.EnsureCreatedAsync();

        if (await context.Patients.AnyAsync())
        {
            return;
        }

        // --- Facilities ---
        var austin = new Facility { Name = "Austin General Hospital", City = "Austin", State = "TX", FacilityType = "Hospital", IsActive = true };
        var dallas = new Facility { Name = "Dallas Transplant Clinic", City = "Dallas", State = "TX", FacilityType = "Clinic", IsActive = true };
        var houston = new Facility { Name = "Houston Medical Center", City = "Houston", State = "TX", FacilityType = "Hospital", IsActive = true };
        context.Facilities.AddRange(austin, dallas, houston);
        await context.SaveChangesAsync();

        // --- Providers ---
        var drReed = new Provider { FirstName = "Sarah", LastName = "Reed", Specialty = "Hematology", NPI = "1000000001", FacilityId = austin.Id };
        var drKhan = new Provider { FirstName = "Omar", LastName = "Khan", Specialty = "Oncology", NPI = "1000000002", FacilityId = austin.Id };
        var drNguyen = new Provider { FirstName = "Linda", LastName = "Nguyen", Specialty = "Nephrology", NPI = "1000000003", FacilityId = dallas.Id };
        var drCarter = new Provider { FirstName = "James", LastName = "Carter", Specialty = "Cardiology", NPI = "1000000004", FacilityId = houston.Id };
        var drSharma = new Provider { FirstName = "Priya", LastName = "Sharma", Specialty = "Immunology", NPI = "1000000005", FacilityId = houston.Id };
        context.Providers.AddRange(drReed, drKhan, drNguyen, drCarter, drSharma);
        await context.SaveChangesAsync();

        // --- Patients ---
        var ava = new Patient
        {
            FirstName = "Ava", LastName = "Patel", Gender = "Female", DateOfBirth = new DateTime(1988, 4, 12),
            ContactNumber = "555-0101", Email = "ava.patel@example.com", PhoneNumber = "555-0102",
            MRN = "MRN-00001", Status = "Active", HeightCm = 165, WeightKg = 78, FacilityId = austin.Id
        };
        var noah = new Patient
        {
            FirstName = "Noah", LastName = "Garcia", Gender = "Male", DateOfBirth = new DateTime(1957, 9, 23),
            ContactNumber = "555-0115", Email = "noah.garcia@example.com", PhoneNumber = "555-0116",
            MRN = "MRN-00002", Status = "Active", HeightCm = 178, WeightKg = 95, FacilityId = austin.Id
        };
        var mia = new Patient
        {
            FirstName = "Mia", LastName = "Thompson", Gender = "Female", DateOfBirth = new DateTime(1972, 1, 30),
            ContactNumber = "555-0121", Email = "mia.thompson@example.com", PhoneNumber = "555-0122",
            MRN = "MRN-00003", Status = "Active", HeightCm = 160, WeightKg = 52, FacilityId = dallas.Id
        };
        var liam = new Patient
        {
            FirstName = "Liam", LastName = "Walker", Gender = "Male", DateOfBirth = new DateTime(1994, 11, 5),
            ContactNumber = "555-0131", Email = "liam.walker@example.com", PhoneNumber = "555-0132",
            MRN = "MRN-00004", Status = "Inactive", HeightCm = 182, WeightKg = 70, FacilityId = dallas.Id
        };
        var ethan = new Patient
        {
            FirstName = "Ethan", LastName = "Brooks", Gender = "Male", DateOfBirth = new DateTime(1980, 3, 14),
            ContactNumber = "555-0141", Email = "ethan.brooks@example.com", PhoneNumber = "555-0142",
            MRN = "MRN-00005", Status = "Active", HeightCm = 175, WeightKg = 88, FacilityId = houston.Id
        };
        var olivia = new Patient
        {
            FirstName = "Olivia", LastName = "Martinez", Gender = "Female", DateOfBirth = new DateTime(1965, 7, 22),
            ContactNumber = "555-0151", Email = "olivia.martinez@example.com", PhoneNumber = "555-0152",
            MRN = "MRN-00006", Status = "Active", HeightCm = 162, WeightKg = 68, FacilityId = houston.Id
        };
        var lucas = new Patient
        {
            FirstName = "Lucas", LastName = "Kim", Gender = "Male", DateOfBirth = new DateTime(2000, 1, 9),
            ContactNumber = "555-0161", Email = "lucas.kim@example.com", PhoneNumber = "555-0162",
            MRN = "MRN-00007", Status = "Active", HeightCm = 170, WeightKg = 64, FacilityId = austin.Id
        };
        var sophia = new Patient
        {
            FirstName = "Sophia", LastName = "Chen", Gender = "Female", DateOfBirth = new DateTime(1990, 5, 30),
            ContactNumber = "555-0171", Email = "sophia.chen@example.com", PhoneNumber = "555-0172",
            MRN = "MRN-00008", Status = "Inactive", HeightCm = 158, WeightKg = 55, FacilityId = dallas.Id
        };
        context.Patients.AddRange(ava, noah, mia, liam, ethan, olivia, lucas, sophia);
        await context.SaveChangesAsync();

        // --- Diagnoses (sub-table per patient) ---
        context.Diagnoses.AddRange(
            new Diagnosis { PatientId = ava.Id, IcdCode = "C90.0", Description = "Multiple myeloma", Severity = "Severe", DiagnosedDate = new DateTime(2025, 9, 1) },
            new Diagnosis { PatientId = ava.Id, IcdCode = "D64.9", Description = "Anemia, unspecified", Severity = "Moderate", DiagnosedDate = new DateTime(2025, 10, 15) },
            new Diagnosis { PatientId = noah.Id, IcdCode = "C92.0", Description = "Acute myeloid leukemia", Severity = "Severe", DiagnosedDate = new DateTime(2025, 8, 20) },
            new Diagnosis { PatientId = mia.Id, IcdCode = "N18.5", Description = "Chronic kidney disease, stage 5", Severity = "Severe", DiagnosedDate = new DateTime(2025, 7, 3) },
            new Diagnosis { PatientId = liam.Id, IcdCode = "C81.9", Description = "Hodgkin lymphoma", Severity = "Moderate", DiagnosedDate = new DateTime(2025, 6, 12) },
            new Diagnosis { PatientId = ethan.Id, IcdCode = "C91.0", Description = "Acute lymphoblastic leukemia", Severity = "Severe", DiagnosedDate = new DateTime(2025, 5, 2) },
            new Diagnosis { PatientId = olivia.Id, IcdCode = "C90.0", Description = "Multiple myeloma", Severity = "Moderate", DiagnosedDate = new DateTime(2025, 4, 18) },
            new Diagnosis { PatientId = lucas.Id, IcdCode = "D61.9", Description = "Aplastic anemia, unspecified", Severity = "Severe", DiagnosedDate = new DateTime(2025, 11, 8) },
            new Diagnosis { PatientId = sophia.Id, IcdCode = "N18.6", Description = "End stage renal disease", Severity = "Severe", DiagnosedDate = new DateTime(2025, 3, 25) });

        // --- Medications (sub-table per patient) ---
        context.Medications.AddRange(
            new Medication { PatientId = ava.Id, Name = "Lenalidomide", Dosage = "25 mg", Frequency = "Once daily", StartDate = new DateTime(2025, 9, 5), IsActive = true },
            new Medication { PatientId = ava.Id, Name = "Dexamethasone", Dosage = "40 mg", Frequency = "Weekly", StartDate = new DateTime(2025, 9, 5), EndDate = new DateTime(2026, 1, 1), IsActive = false },
            new Medication { PatientId = noah.Id, Name = "Cytarabine", Dosage = "100 mg/m2", Frequency = "Continuous", StartDate = new DateTime(2025, 8, 25), IsActive = true },
            new Medication { PatientId = mia.Id, Name = "Tacrolimus", Dosage = "2 mg", Frequency = "Twice daily", StartDate = new DateTime(2025, 12, 1), IsActive = true },
            new Medication { PatientId = liam.Id, Name = "Brentuximab", Dosage = "1.8 mg/kg", Frequency = "Every 3 weeks", StartDate = new DateTime(2025, 6, 20), IsActive = true },
            new Medication { PatientId = ethan.Id, Name = "Vincristine", Dosage = "1.4 mg/m2", Frequency = "Weekly", StartDate = new DateTime(2025, 5, 10), IsActive = true },
            new Medication { PatientId = olivia.Id, Name = "Bortezomib", Dosage = "1.3 mg/m2", Frequency = "Twice weekly", StartDate = new DateTime(2025, 4, 20), IsActive = true },
            new Medication { PatientId = lucas.Id, Name = "Cyclosporine", Dosage = "5 mg/kg", Frequency = "Twice daily", StartDate = new DateTime(2025, 11, 12), IsActive = true },
            new Medication { PatientId = sophia.Id, Name = "Sevelamer", Dosage = "800 mg", Frequency = "Three times daily", StartDate = new DateTime(2025, 3, 28), EndDate = new DateTime(2025, 12, 1), IsActive = false });
        await context.SaveChangesAsync();

        // --- Transplant events (sub-table per patient) + lab results (sub-table per event) ---
        var e1 = new TransplantEvent
        {
            PatientId = ava.Id, ProviderId = drReed.Id, DateOfVisit = new DateTime(2026, 1, 15), DateOfPreviousVisit = new DateTime(2025, 12, 10),
            TransplantDate = new DateTime(2025, 11, 20), InfusionDate = new DateTime(2025, 11, 22), DischargeDate = new DateTime(2025, 12, 2),
            EventId = "EVT-1001", TransplantNumber = "TX-1001", DonorType = "Autologous", IsInpatient = true
        };
        var e2 = new TransplantEvent
        {
            PatientId = ava.Id, ProviderId = drKhan.Id, DateOfVisit = new DateTime(2026, 3, 10), DateOfPreviousVisit = new DateTime(2026, 1, 15),
            TransplantDate = new DateTime(2026, 2, 25), InfusionDate = new DateTime(2026, 2, 26), DischargeDate = null,
            EventId = "EVT-1002", TransplantNumber = "TX-1002", DonorType = "Allogeneic", IsInpatient = false
        };
        var e3 = new TransplantEvent
        {
            PatientId = noah.Id, ProviderId = drKhan.Id, DateOfVisit = new DateTime(2026, 2, 5), DateOfPreviousVisit = new DateTime(2025, 11, 25),
            TransplantDate = new DateTime(2025, 10, 18), InfusionDate = new DateTime(2025, 10, 19), DischargeDate = new DateTime(2025, 11, 1),
            EventId = "EVT-2002", TransplantNumber = "TX-2002", DonorType = "Allogeneic", IsInpatient = true
        };
        var e4 = new TransplantEvent
        {
            PatientId = mia.Id, ProviderId = drNguyen.Id, DateOfVisit = new DateTime(2026, 1, 28), DateOfPreviousVisit = new DateTime(2025, 12, 20),
            TransplantDate = new DateTime(2025, 12, 15), InfusionDate = new DateTime(2025, 12, 16), DischargeDate = new DateTime(2025, 12, 22),
            EventId = "EVT-3003", TransplantNumber = "TX-3003", DonorType = "Allogeneic", IsInpatient = true
        };
        var e5 = new TransplantEvent
        {
            PatientId = liam.Id, ProviderId = drNguyen.Id, DateOfVisit = new DateTime(2026, 2, 18), DateOfPreviousVisit = new DateTime(2026, 1, 10),
            TransplantDate = new DateTime(2026, 1, 30), InfusionDate = new DateTime(2026, 1, 31), DischargeDate = new DateTime(2026, 2, 4),
            EventId = "EVT-4004", TransplantNumber = "TX-4004", DonorType = "Autologous", IsInpatient = false
        };
        var e6 = new TransplantEvent
        {
            PatientId = ethan.Id, ProviderId = drCarter.Id, DateOfVisit = new DateTime(2026, 4, 5), DateOfPreviousVisit = new DateTime(2026, 2, 20),
            TransplantDate = new DateTime(2026, 1, 15), InfusionDate = new DateTime(2026, 1, 16), DischargeDate = new DateTime(2026, 1, 25),
            EventId = "EVT-5005", TransplantNumber = "TX-5005", DonorType = "Allogeneic", IsInpatient = true
        };
        var e7 = new TransplantEvent
        {
            PatientId = olivia.Id, ProviderId = drSharma.Id, DateOfVisit = new DateTime(2025, 10, 12), DateOfPreviousVisit = new DateTime(2025, 8, 1),
            TransplantDate = new DateTime(2025, 9, 1), InfusionDate = new DateTime(2025, 9, 2), DischargeDate = new DateTime(2025, 9, 10),
            EventId = "EVT-6006", TransplantNumber = "TX-6006", DonorType = "Autologous", IsInpatient = true
        };
        var e8 = new TransplantEvent
        {
            PatientId = olivia.Id, ProviderId = drSharma.Id, DateOfVisit = new DateTime(2026, 1, 20), DateOfPreviousVisit = new DateTime(2025, 10, 12),
            TransplantDate = new DateTime(2025, 12, 5), InfusionDate = new DateTime(2025, 12, 6), DischargeDate = null,
            EventId = "EVT-6007", TransplantNumber = "TX-6007", DonorType = "Allogeneic", IsInpatient = false
        };
        var e9 = new TransplantEvent
        {
            PatientId = lucas.Id, ProviderId = drReed.Id, DateOfVisit = new DateTime(2026, 6, 15), DateOfPreviousVisit = new DateTime(2026, 4, 1),
            TransplantDate = new DateTime(2026, 3, 10), InfusionDate = new DateTime(2026, 3, 11), DischargeDate = new DateTime(2026, 3, 20),
            EventId = "EVT-7008", TransplantNumber = "TX-7008", DonorType = "Allogeneic", IsInpatient = true
        };
        var e10 = new TransplantEvent
        {
            PatientId = sophia.Id, ProviderId = drNguyen.Id, DateOfVisit = new DateTime(2025, 12, 22), DateOfPreviousVisit = new DateTime(2025, 10, 30),
            TransplantDate = new DateTime(2025, 11, 15), InfusionDate = new DateTime(2025, 11, 16), DischargeDate = new DateTime(2025, 11, 25),
            EventId = "EVT-8009", TransplantNumber = "TX-8009", DonorType = "Living Donor", IsInpatient = true
        };
        var e11 = new TransplantEvent
        {
            PatientId = noah.Id, ProviderId = drKhan.Id, DateOfVisit = new DateTime(2025, 11, 30), DateOfPreviousVisit = new DateTime(2025, 9, 15),
            TransplantDate = new DateTime(2025, 8, 20), InfusionDate = new DateTime(2025, 8, 21), DischargeDate = new DateTime(2025, 8, 30),
            EventId = "EVT-2003", TransplantNumber = "TX-2003", DonorType = "Allogeneic", IsInpatient = false
        };
        var e12 = new TransplantEvent
        {
            PatientId = mia.Id, ProviderId = drNguyen.Id, DateOfVisit = new DateTime(2026, 5, 5), DateOfPreviousVisit = new DateTime(2026, 1, 28),
            TransplantDate = new DateTime(2026, 4, 10), InfusionDate = new DateTime(2026, 4, 11), DischargeDate = new DateTime(2026, 4, 20),
            EventId = "EVT-3004", TransplantNumber = "TX-3004", DonorType = "Allogeneic", IsInpatient = true
        };
        context.TransplantEvents.AddRange(e1, e2, e3, e4, e5, e6, e7, e8, e9, e10, e11, e12);
        await context.SaveChangesAsync();

        // Reference ranges chosen so some values fall out of range (drives conditional formatting).
        context.LabResults.AddRange(
            new LabResult { TransplantEventId = e1.Id, TestName = "Hemoglobin", Value = 9.2, Unit = "g/dL", ReferenceLow = 12.0, ReferenceHigh = 16.0, TakenDate = new DateTime(2026, 1, 15) },
            new LabResult { TransplantEventId = e1.Id, TestName = "WBC", Value = 3.1, Unit = "10^9/L", ReferenceLow = 4.0, ReferenceHigh = 11.0, TakenDate = new DateTime(2026, 1, 15) },
            new LabResult { TransplantEventId = e1.Id, TestName = "Platelets", Value = 210, Unit = "10^9/L", ReferenceLow = 150, ReferenceHigh = 400, TakenDate = new DateTime(2026, 1, 15) },
            new LabResult { TransplantEventId = e2.Id, TestName = "Hemoglobin", Value = 13.4, Unit = "g/dL", ReferenceLow = 12.0, ReferenceHigh = 16.0, TakenDate = new DateTime(2026, 3, 10) },
            new LabResult { TransplantEventId = e2.Id, TestName = "Creatinine", Value = 1.9, Unit = "mg/dL", ReferenceLow = 0.6, ReferenceHigh = 1.3, TakenDate = new DateTime(2026, 3, 10) },
            new LabResult { TransplantEventId = e3.Id, TestName = "Hemoglobin", Value = 8.1, Unit = "g/dL", ReferenceLow = 12.0, ReferenceHigh = 16.0, TakenDate = new DateTime(2026, 2, 5) },
            new LabResult { TransplantEventId = e3.Id, TestName = "WBC", Value = 12.6, Unit = "10^9/L", ReferenceLow = 4.0, ReferenceHigh = 11.0, TakenDate = new DateTime(2026, 2, 5) },
            new LabResult { TransplantEventId = e4.Id, TestName = "Creatinine", Value = 3.4, Unit = "mg/dL", ReferenceLow = 0.6, ReferenceHigh = 1.3, TakenDate = new DateTime(2026, 1, 28) },
            new LabResult { TransplantEventId = e4.Id, TestName = "Potassium", Value = 5.8, Unit = "mmol/L", ReferenceLow = 3.5, ReferenceHigh = 5.1, TakenDate = new DateTime(2026, 1, 28) },
            new LabResult { TransplantEventId = e5.Id, TestName = "Hemoglobin", Value = 14.0, Unit = "g/dL", ReferenceLow = 12.0, ReferenceHigh = 16.0, TakenDate = new DateTime(2026, 2, 18) },
            new LabResult { TransplantEventId = e5.Id, TestName = "Platelets", Value = 130, Unit = "10^9/L", ReferenceLow = 150, ReferenceHigh = 400, TakenDate = new DateTime(2026, 2, 18) },
            new LabResult { TransplantEventId = e6.Id, TestName = "WBC", Value = 2.4, Unit = "10^9/L", ReferenceLow = 4.0, ReferenceHigh = 11.0, TakenDate = new DateTime(2026, 4, 5) },
            new LabResult { TransplantEventId = e6.Id, TestName = "Platelets", Value = 95, Unit = "10^9/L", ReferenceLow = 150, ReferenceHigh = 400, TakenDate = new DateTime(2026, 4, 5) },
            new LabResult { TransplantEventId = e7.Id, TestName = "Hemoglobin", Value = 10.5, Unit = "g/dL", ReferenceLow = 12.0, ReferenceHigh = 16.0, TakenDate = new DateTime(2025, 10, 12) },
            new LabResult { TransplantEventId = e8.Id, TestName = "Creatinine", Value = 1.1, Unit = "mg/dL", ReferenceLow = 0.6, ReferenceHigh = 1.3, TakenDate = new DateTime(2026, 1, 20) },
            new LabResult { TransplantEventId = e9.Id, TestName = "WBC", Value = 13.8, Unit = "10^9/L", ReferenceLow = 4.0, ReferenceHigh = 11.0, TakenDate = new DateTime(2026, 6, 15) },
            new LabResult { TransplantEventId = e9.Id, TestName = "Hemoglobin", Value = 11.2, Unit = "g/dL", ReferenceLow = 12.0, ReferenceHigh = 16.0, TakenDate = new DateTime(2026, 6, 15) },
            new LabResult { TransplantEventId = e10.Id, TestName = "Potassium", Value = 6.1, Unit = "mmol/L", ReferenceLow = 3.5, ReferenceHigh = 5.1, TakenDate = new DateTime(2025, 12, 22) },
            new LabResult { TransplantEventId = e10.Id, TestName = "Creatinine", Value = 4.2, Unit = "mg/dL", ReferenceLow = 0.6, ReferenceHigh = 1.3, TakenDate = new DateTime(2025, 12, 22) },
            new LabResult { TransplantEventId = e11.Id, TestName = "Hemoglobin", Value = 9.8, Unit = "g/dL", ReferenceLow = 12.0, ReferenceHigh = 16.0, TakenDate = new DateTime(2025, 11, 30) },
            new LabResult { TransplantEventId = e12.Id, TestName = "Creatinine", Value = 0.9, Unit = "mg/dL", ReferenceLow = 0.6, ReferenceHigh = 1.3, TakenDate = new DateTime(2026, 5, 5) });
        await context.SaveChangesAsync();
    }
}
