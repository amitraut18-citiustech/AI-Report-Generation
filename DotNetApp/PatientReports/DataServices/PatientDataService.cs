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
}
