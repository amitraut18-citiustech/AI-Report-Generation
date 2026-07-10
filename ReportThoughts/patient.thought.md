# Report Thought: Patient Report

**Report key:** patient

## Source
- **Legacy format:** .NET MVC (RDL + Razor)
- **Description:** A flat listing of all patients with their demographic and contact details, sorted by last name.
- **Source files:**
  | Role | File |
  |------|------|
  | Controller action | Controllers/ReportsController.cs → PatientReport() |
  | Data service | DataServices/PatientDataService.cs → GetPatientReportAsync() |
  | ViewModel | Models/PatientReportViewModel.cs |
  | EF entities | Models/Patient.cs |
  | DbContext | Data/ApplicationDbContext.cs |
  | Razor view | Views/Reports/PatientReport.cshtml |
  | RDL (layout hint) | Reports/PatientReport.rdl (skeletal — layout only, no dataset/fields) |

## Database Context
- **Provider:** EF Core (DbContext `ApplicationDbContext`; connection provider not specified in these files — inferred generic EF Core).
- **Entities/tables used:** Patients (single table; no joins or includes).
- **Fields (from the ViewModel — authoritative):**
  | Field | .NET type | Direct / derived | Meaning |
  |-------|-----------|------------------|---------|
  | FirstName | string | direct (Patients.FirstName) | Patient first name (required, max 100) |
  | LastName | string | direct (Patients.LastName) | Patient last name (required, max 100); also the sort key |
  | Gender | string | direct (Patients.Gender) | Patient gender (max 20) |
  | DateOfBirth | DateTime | direct (Patients.DateOfBirth) | Patient date of birth |
  | ContactNumber | string | direct (Patients.ContactNumber) | Contact number (max 30) |
  | Email | string | direct (Patients.Email) | Email address (max 200) |
  | PhoneNumber | string | direct (Patients.PhoneNumber) | Phone number (max 30) |
- **Relationships:** Patient has a one-to-many collection of TransplantEvents (TransplantEvents.PatientId → Patients.Id, cascade delete). This relationship is NOT used by the Patient report — no navigation is traversed.

## Data Access
- **Method:** PatientDataService.GetPatientReportAsync() — async.
- **Query (plain English):** Selects all rows from the Patients DbSet (no Where filter), projects each into a PatientReportViewModel with the seven fields above, and orders the result by LastName ascending. Returns a List<PatientReportViewModel>.
- **Projection / derived fields:** None derived — every field is a straight one-to-one copy from the Patient entity.
- **Read-only:** Yes (AsNoTracking).
- **Original LINQ (verbatim, for reference):**
  ```csharp
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
  ```

## Business Logic
- No filtering — all patient rows are returned.
- Ordering: ascending by LastName.
- No aggregations, counts, or summary totals.
- Formatting: DateOfBirth is rendered with `.ToShortDateString()` in the Razor view; all other fields render as-is.
- **Derived fields:** None.
- **Legacy RDL expressions (if any):** _None._ The RDL is a skeletal layout stub (static title textbox "Patient Report" and a header-row-only tablix with column labels First Name, Last Name, Gender, Date of Birth, Contact Number, Email, Phone). It contains no DataSet, Fields, parameters, or expressions.

## Conditional Logic
- _None._ No visibility/Hidden expressions, row suppression, or conditional formatting.

## Grouping & Sorting
- **Grouping:** _None._
- **Sorting:** OrderBy LastName (ascending).

## Parameters
_None — returns all rows._ The controller action takes no arguments, there are no query-string inputs, and the RDL declares no `<ReportParameter>`.

## Layout
- **Title:** "Patient Report" (Razor `<h2 class="mb-4">`; also ViewData["Title"]. RDL title textbox matches: 16pt bold, centered).
- **Summary / cards:** _None._
- **Table columns (in order, with header labels):** First Name, Last Name, Gender, Date of Birth, Contact Number, Email, Phone Number. Rendered as a Bootstrap `table table-striped table-bordered` with a `table-dark` header. (RDL uses "Phone" as the last header label; Razor uses "Phone Number" — Razor is authoritative for the .NET app.)
- **Per-column formatting:** Date of Birth via `@item.DateOfBirth.ToShortDateString()`; all other columns rendered directly.
- **Header/Footer:** _None_ in the Razor view. The RDL declares an empty 0.5in PageHeader (PrintOnFirstPage/PrintOnLastPage true) with no content, and sets RepeatColumnHeaders/RepeatRowHeaders true (column headers repeat on new pages).

## Open Questions
- The EF Core database provider (SQLite vs SQL Server, etc.) is not evident in the files provided — the connection string / DI registration lives elsewhere (e.g. Program.cs). Confirm if the provider matters for migration.
- Minor label discrepancy: RDL header reads "Phone" while the Razor view reads "Phone Number". Assumed the Razor label ("Phone Number") is authoritative — please confirm.
