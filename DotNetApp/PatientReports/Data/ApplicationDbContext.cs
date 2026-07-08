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

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Patient>(entity =>
        {
            entity.HasKey(p => p.Id);
            entity.Property(p => p.FirstName).IsRequired().HasMaxLength(100);
            entity.Property(p => p.LastName).IsRequired().HasMaxLength(100);
            entity.Property(p => p.Gender).HasMaxLength(20);
            entity.Property(p => p.ContactNumber).HasMaxLength(30);
            entity.Property(p => p.Email).HasMaxLength(200);
            entity.Property(p => p.PhoneNumber).HasMaxLength(30);
        });

        modelBuilder.Entity<TransplantEvent>(entity =>
        {
            entity.HasKey(t => t.Id);
            entity.Property(t => t.EventId).IsRequired().HasMaxLength(50);
            entity.HasOne(t => t.Patient)
                .WithMany(p => p.TransplantEvents)
                .HasForeignKey(t => t.PatientId)
                .OnDelete(DeleteBehavior.Cascade);
        });
    }
}
