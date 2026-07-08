using Microsoft.EntityFrameworkCore;
using PatientReports.Models;

namespace PatientReports.Data;

public static class SeedData
{
    public static async Task InitializeAsync(IServiceProvider serviceProvider)
    {
        using var scope = serviceProvider.CreateScope();
        var context = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();

        await context.Database.EnsureCreatedAsync();

        if (await context.Patients.AnyAsync())
        {
            return;
        }

        var patient1 = new Patient
        {
            FirstName = "Ava",
            LastName = "Patel",
            Gender = "Female",
            DateOfBirth = new DateTime(1988, 4, 12),
            ContactNumber = "555-0101",
            Email = "ava.patel@example.com",
            PhoneNumber = "555-0102"
        };

        var patient2 = new Patient
        {
            FirstName = "Noah",
            LastName = "Garcia",
            Gender = "Male",
            DateOfBirth = new DateTime(1975, 9, 23),
            ContactNumber = "555-0115",
            Email = "noah.garcia@example.com",
            PhoneNumber = "555-0116"
        };

        context.Patients.AddRange(patient1, patient2);
        await context.SaveChangesAsync();

        context.TransplantEvents.AddRange(
            new TransplantEvent
            {
                PatientId = patient1.Id,
                DateOfVisit = new DateTime(2026, 1, 15),
                DateOfPreviousVisit = new DateTime(2025, 12, 10),
                TransplantDate = new DateTime(2025, 11, 20),
                InfusionDate = new DateTime(2025, 11, 22),
                EventId = "EVT-1001",
                IsInpatient = true
            },
            new TransplantEvent
            {
                PatientId = patient2.Id,
                DateOfVisit = new DateTime(2026, 2, 5),
                DateOfPreviousVisit = new DateTime(2025, 11, 25),
                TransplantDate = new DateTime(2025, 10, 18),
                InfusionDate = new DateTime(2025, 10, 19),
                EventId = "EVT-2002",
                IsInpatient = false
            });

        await context.SaveChangesAsync();
    }
}
