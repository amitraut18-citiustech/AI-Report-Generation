# Report Thought: Patient Report

**Report key:** patient

## Source
- **Legacy format:** SSRS (.rdl) -- rich (has a real dataset with fields, query, and tablix with formatting)
- **Description:** A flat listing of all patients with their contact and demographic information, ordered alphabetically by last name.
- **Source files:**
  | Role | File |
  |------|------|
  | Report wiring (name -> data -> output) | `Controllers/ReportsController.cs` -- actions `PatientReport`, `HtmlReport(report="patient")`, `RdlView(report="patient")`, `Download(report="patient")` |
  | Data access (query + projection) | `DataServices/PatientDataService.cs` -- method `GetPatientReportAsync` |
  | Row shape (view model / DTO) | `Models/PatientReportViewModel.cs` |
  | Data model / schema | `Models/Patient.cs`, `Data/ApplicationDbContext.cs` |
  | View / layout | `Views/Reports/PatientReport.cshtml`, `Views/Reports/_PatientReport.cshtml` (shared partial) |
  | Legacy RDL | `Reports/PatientReport.rdl` (rich -- has dataset `dsPatient`, 7 fields, tablix with header/detail rows, alternating row shading, date formatting) |

## Database Context
- **Provider / data source:** EF Core + SQLite (`db/PatientDB.db`, recreated and seeded on startup)
- **Entities/tables used:** `Patients` (single table, no joins)
- **Fields (from the row shape -- authoritative):**
  | Field | Type | Direct / derived | Meaning |
  |-------|------|------------------|---------|
  | FirstName | string | direct (Patients.FirstName) | Patient first name |
  | LastName | string | direct (Patients.LastName) | Patient last name |
  | Gender | string | direct (Patients.Gender) | Patient gender |
  | DateOfBirth | DateTime | direct (Patients.DateOfBirth) | Patient date of birth |
  | ContactNumber | string | direct (Patients.ContactNumber) | Contact phone number |
  | Email | string | direct (Patients.Email) | Email address |
  | PhoneNumber | string | direct (Patients.PhoneNumber) | Phone number |
- **Relationships:** The `Patient` entity has FK relationships to `Facility`, `TransplantEvents`, `Diagnoses`, and `Medications`, but none are used by this report. The query reads only from the `Patients` table with no joins or includes.

## Data Access
- **Method:** `PatientDataService.GetPatientReportAsync()`
- **Query (plain English):** Select all patients from the Patients table (no filtering, no joins), project seven columns (FirstName, LastName, Gender, DateOfBirth, ContactNumber, Email, PhoneNumber), and order the results alphabetically by LastName ascending. Uses `AsNoTracking()` for read-only access.
- **Projection / derived fields:** All seven fields are direct column mappings from the Patient entity to the PatientReportViewModel. There are no derived or computed fields.
- **Read-only:** Yes (`AsNoTracking()`)
- **Original query (verbatim, for reference):**
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
- **Filters:** None. All patients are returned.
- **Ordering:** Rows sorted by LastName ascending.
- **Aggregations/counts:** None in the data service. No summary row or row count displayed.
- **Derived fields:** None -- all fields are direct column mappings.
- **Legacy RDL expressions:**
  - `=Format(Fields!DateOfBirth.Value, "MM/dd/yyyy")` -- formats date of birth as month/day/year (e.g., "01/15/1990").
  - `=IIF(RowNumber(Nothing) Mod 2 = 1, "#F2F2F2", "White")` -- alternating row background color: light gray for odd rows, white for even rows (zebra striping).

## Conditional Logic
- Alternating row background color via the RDL IIF expression (see Business Logic above). No visibility toggles, row suppression, or other conditional display.

## Grouping & Sorting
- **Grouping:** None. The tablix has a single `Details` group (one row per patient, no parent group).
- **Sorting:** OrderBy LastName ascending (applied in the LINQ query). The RDL has no additional `<SortExpression>` elements.

## Parameters
_None -- returns all rows._ The report takes no user-facing filter parameters. There are no chrome parameters either.

## Layout
- **Title:** "Patient Report" (from both the RDL title textbox and the Razor view heading)
- **Summary / cards:** _None._
- **Table columns (in order, with header labels):**
  | # | Header Label | Field |
  |---|-------------|-------|
  | 1 | First Name | FirstName |
  | 2 | Last Name | LastName |
  | 3 | Gender | Gender |
  | 4 | Date of Birth | DateOfBirth |
  | 5 | Contact Number | ContactNumber |
  | 6 | Email | Email |
  | 7 | Phone | PhoneNumber |
- **Per-column formatting:**
  - DateOfBirth: formatted as "MM/dd/yyyy" in the RDL; formatted via `ToShortDateString()` in the Razor view (locale-dependent, typically "M/d/yyyy" on US systems).
  - All other columns: plain text, no special formatting.
- **Column widths (from RDL):** 1in, 1in, 0.7in, 1in, 1.2in, 2.4in, 1.2in (total 8.5in).
- **Header style (from RDL):** Dark background (#212529), bold white text, left-padded 6pt, vertically centered. Consistent with the Razor partial's `table-dark` Bootstrap class.
- **Detail row style (from RDL):** Alternating background (odd rows #F2F2F2, even rows white), left-padded 6pt, vertically centered. Consistent with the Razor partial's `table-striped` Bootstrap class.
- **Title style (from RDL):** Segoe UI, 16pt, bold, color #1f3864, center-aligned.
- **Header/Footer:**
  - RDL defines a 0.5in page header (prints on first and last pages) but it contains no report items (empty header band).
  - No page footer defined in the RDL.
  - The Razor view adds no header or footer content beyond the title.

## Open Questions
_None._
