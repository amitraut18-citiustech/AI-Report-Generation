using System;

namespace RdlRenderService
{
    // Mirrors PatientReports.Models.PatientReportViewModel field-for-field.
    public class PatientRow
    {
        public string FirstName { get; set; }
        public string LastName { get; set; }
        public string Gender { get; set; }
        public DateTime DateOfBirth { get; set; }
        public string ContactNumber { get; set; }
        public string Email { get; set; }
        public string PhoneNumber { get; set; }
    }

    // Mirrors PatientReports.Models.TransplantEventReportViewModel field-for-field,
    // plus TotalTransplants which RdlRenderer computes (count of rows sharing the
    // same PatientName) before binding, since RDL grouping would reorder rows.
    public class TransplantEventRow
    {
        public string PatientName { get; set; }
        public DateTime DateOfVisit { get; set; }
        public DateTime DateOfPreviousVisit { get; set; }
        public DateTime TransplantDate { get; set; }
        public DateTime InfusionDate { get; set; }
        public string EventId { get; set; }
        public string TransplantNumber { get; set; }
        public string IsInpatient { get; set; }
        public int TotalTransplants { get; set; }
    }

    // Mirrors PatientReports.Models.ClinicalFlatRow, minus the fields the RDL
    // never references (TransplantNumber/TransplantDate/InfusionDate/DischargeDate/LabTakenDate).
    public class ClinicalFlatRow
    {
        public string FacilityName { get; set; }
        public string FacilityCity { get; set; }
        public string FacilityState { get; set; }

        public int PatientId { get; set; }
        public string Mrn { get; set; }
        public string PatientName { get; set; }
        public string Gender { get; set; }
        public DateTime DateOfBirth { get; set; }
        public double HeightCm { get; set; }
        public double WeightKg { get; set; }
        public string Status { get; set; }

        public string EventId { get; set; }
        public string DonorType { get; set; }
        public DateTime DateOfVisit { get; set; }
        public DateTime DateOfPreviousVisit { get; set; }
        public bool IsInpatient { get; set; }

        public string ProviderName { get; set; }
        public string Specialty { get; set; }

        public string PrimaryDiagnosis { get; set; }
        public int ActiveMedCount { get; set; }

        public string LabTestName { get; set; }
        public double? LabValue { get; set; }
        public string LabUnit { get; set; }
        public double? RefLow { get; set; }
        public double? RefHigh { get; set; }
    }
}
