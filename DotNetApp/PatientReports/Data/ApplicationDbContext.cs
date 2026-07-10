using Microsoft.EntityFrameworkCore;
using PatientReports.Models;

namespace PatientReports.Data;

public class ApplicationDbContext : DbContext
{
    public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options) : base(options)
    {
    }

    public DbSet<Patient> Patients => Set<Patient>();
    public DbSet<TransplantEvent> TransplantEvents => Set<TransplantEvent>();
    public DbSet<Facility> Facilities => Set<Facility>();
    public DbSet<Provider> Providers => Set<Provider>();
    public DbSet<Diagnosis> Diagnoses => Set<Diagnosis>();
    public DbSet<Medication> Medications => Set<Medication>();
    public DbSet<LabResult> LabResults => Set<LabResult>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Facility>(entity =>
        {
            entity.HasKey(f => f.Id);
            entity.Property(f => f.Name).IsRequired().HasMaxLength(200);
            entity.Property(f => f.City).HasMaxLength(100);
            entity.Property(f => f.State).HasMaxLength(2);
            entity.Property(f => f.FacilityType).HasMaxLength(50);
        });

        modelBuilder.Entity<Provider>(entity =>
        {
            entity.HasKey(p => p.Id);
            entity.Property(p => p.FirstName).IsRequired().HasMaxLength(100);
            entity.Property(p => p.LastName).IsRequired().HasMaxLength(100);
            entity.Property(p => p.Specialty).HasMaxLength(100);
            entity.Property(p => p.NPI).HasMaxLength(20);
            entity.HasOne(p => p.Facility)
                .WithMany(f => f.Providers)
                .HasForeignKey(p => p.FacilityId)
                .OnDelete(DeleteBehavior.Restrict);
        });

        modelBuilder.Entity<Patient>(entity =>
        {
            entity.HasKey(p => p.Id);
            entity.Property(p => p.FirstName).IsRequired().HasMaxLength(100);
            entity.Property(p => p.LastName).IsRequired().HasMaxLength(100);
            entity.Property(p => p.Gender).HasMaxLength(20);
            entity.Property(p => p.ContactNumber).HasMaxLength(30);
            entity.Property(p => p.Email).HasMaxLength(200);
            entity.Property(p => p.PhoneNumber).HasMaxLength(30);
            entity.Property(p => p.MRN).HasMaxLength(20);
            entity.Property(p => p.Status).HasMaxLength(20);
            entity.HasOne(p => p.Facility)
                .WithMany(f => f.Patients)
                .HasForeignKey(p => p.FacilityId)
                .OnDelete(DeleteBehavior.Restrict);
        });

        modelBuilder.Entity<TransplantEvent>(entity =>
        {
            entity.HasKey(t => t.Id);
            entity.Property(t => t.EventId).IsRequired().HasMaxLength(50);
            entity.Property(t => t.TransplantNumber).HasMaxLength(50);
            entity.Property(t => t.DonorType).HasMaxLength(30);
            entity.HasOne(t => t.Patient)
                .WithMany(p => p.TransplantEvents)
                .HasForeignKey(t => t.PatientId)
                .OnDelete(DeleteBehavior.Cascade);
            entity.HasOne(t => t.Provider)
                .WithMany(pr => pr.TransplantEvents)
                .HasForeignKey(t => t.ProviderId)
                .OnDelete(DeleteBehavior.Restrict);
        });

        modelBuilder.Entity<Diagnosis>(entity =>
        {
            entity.HasKey(d => d.Id);
            entity.Property(d => d.IcdCode).IsRequired().HasMaxLength(10);
            entity.Property(d => d.Description).HasMaxLength(200);
            entity.Property(d => d.Severity).HasMaxLength(20);
            entity.HasOne(d => d.Patient)
                .WithMany(p => p.Diagnoses)
                .HasForeignKey(d => d.PatientId)
                .OnDelete(DeleteBehavior.Cascade);
        });

        modelBuilder.Entity<Medication>(entity =>
        {
            entity.HasKey(m => m.Id);
            entity.Property(m => m.Name).IsRequired().HasMaxLength(150);
            entity.Property(m => m.Dosage).HasMaxLength(50);
            entity.Property(m => m.Frequency).HasMaxLength(50);
            entity.HasOne(m => m.Patient)
                .WithMany(p => p.Medications)
                .HasForeignKey(m => m.PatientId)
                .OnDelete(DeleteBehavior.Cascade);
        });

        modelBuilder.Entity<LabResult>(entity =>
        {
            entity.HasKey(l => l.Id);
            entity.Property(l => l.TestName).IsRequired().HasMaxLength(100);
            entity.Property(l => l.Unit).HasMaxLength(20);
            entity.HasOne(l => l.TransplantEvent)
                .WithMany(t => t.LabResults)
                .HasForeignKey(l => l.TransplantEventId)
                .OnDelete(DeleteBehavior.Cascade);
        });
    }
}
