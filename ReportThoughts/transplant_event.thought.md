# Report Thought: Transplant Event Report

**Report key:** transplant_event

## Source
- **Legacy format:** .NET MVC (RDL + Razor)
- **Description:** Lists every transplant event in the system, one row per event, joined to its patient, with visit/transplant/infusion dates, identifiers, an inpatient flag, and a total-transplant count banner.
- **Source files:**
  | Role | File |
  |------|------|
  | Controller action | Controllers/ReportsController.cs → TransplantEventReport() |
  | Data service | DataServices/PatientDataService.cs → GetTransplantEventReportAsync() |
  | ViewModel | Models/TransplantEventReportViewModel.cs |
  | EF entities | Models/TransplantEvent.cs, Models/Patient.cs |
  | DbContext | Data/ApplicationDbContext.cs |
  | Razor view | Views/Reports/TransplantEventReport.cshtml |
  | RDL (layout hint) | Reports/TransplantEventReport.rdl (skeletal — layout only, no dataset/fields) |

## Database Context
- **Provider:** EF Core (DbContext = ApplicationDbContext). Concrete provider not shown in these files; DbSets are `Patients` and `TransplantEvents`.
- **Entities/tables used:** TransplantEvents (primary), Patients (via `Include(e => e.Patient)`).
- **Fields (from the ViewModel — authoritative):**
  | Field | .NET type | Direct / derived | Meaning |
  |-------|-----------|------------------|---------|
  | PatientName | string | derived (`e.Patient.FirstName + " " + e.Patient.LastName`) | Patient full name |
  | DateOfVisit | DateTime | direct (TransplantEvents.DateOfVisit) | Date of the current visit |
  | DateOfPreviousVisit | DateTime | direct (TransplantEvents.DateOfPreviousVisit) | Date of the prior visit |
  | TransplantDate | DateTime | direct (TransplantEvents.TransplantDate) | Date of transplant |
  | InfusionDate | DateTime | direct (TransplantEvents.InfusionDate) | Date of infusion |
  | EventId | string | direct (TransplantEvents.EventId) | Event identifier (required, max 50) |
  | TransplantNumber | string | direct (TransplantEvents.TransplantNumber) | Transplant number/label (max 50) |
  | IsInpatient | string | derived (`e.IsInpatient ? "Yes" : "No"`) | Inpatient flag rendered as text |
- **Relationships:** TransplantEvents.PatientId → Patients.Id (many-to-one). `TransplantEvent.HasOne(Patient).WithMany(TransplantEvents).HasForeignKey(PatientId)`, `OnDelete = Cascade`. Patient keyed on Id; TransplantEvent keyed on Id.

## Data Access
- **Method:** PatientDataService.GetTransplantEventReportAsync() — async.
- **Query (plain English):** Reads all rows from the TransplantEvents DbSet, eager-loads the related Patient (`Include`), projects into TransplantEventReportViewModel, and orders ascending by DateOfVisit. No `Where` filter — returns every transplant event.
- **Projection / derived fields:**
  - `PatientName = e.Patient.FirstName + " " + e.Patient.LastName`
  - `IsInpatient = e.IsInpatient ? "Yes" : "No"`
  - All other fields projected 1:1 from the TransplantEvent entity.
- **Read-only:** Yes — `AsNoTracking()`.
- **Original LINQ (verbatim, for reference):**
  ```csharp
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
  ```

## Business Logic
- Returns all transplant events (no filtering); ordered by DateOfVisit ascending.
- Aggregation: the view displays a total row count via `@Model.Count()` — shown both in the "Total Transplants" info banner and repeated in every row's "Total Transplants" column.
- **Derived fields:** PatientName = full-name concatenation (`FirstName + " " + LastName`); IsInpatient = boolean rendered as `"Yes"`/`"No"`.
- **Legacy RDL expressions (if any):** _None._ The RDL is a skeletal layout stub — static title text and hard-coded column-header cells only, no dataset, fields, or value expressions.

## Conditional Logic
- _None._ No visibility/`Hidden` expressions, no row suppression, no conditional formatting. (The only conditional is the `IsInpatient` bool→text conversion, captured under Derived fields.)

## Grouping & Sorting
- **Grouping:** _None._
- **Sorting:** OrderBy DateOfVisit ascending.

## Parameters
_None — returns all rows._ The controller action takes no arguments and the data service method accepts no parameters; there are no query-string inputs or RDL `<ReportParameter>` elements.

## Layout
- **Title:** "Transplant Event Report" (Razor `<h2>`; RDL Title textbox 16pt bold centered).
- **Summary / cards:** Info banner (`alert alert-info`) reading `Total Transplants: {Model.Count()}`.
- **Table columns (in order, with header labels):**
  1. Patient — PatientName
  2. Date of Visit — DateOfVisit
  3. Date of Previous Visit — DateOfPreviousVisit
  4. Transplant Date — TransplantDate
  5. Infusion Date — InfusionDate
  6. Event ID — EventId
  7. Transplant Number — TransplantNumber
  8. Total Transplants — `@Model.Count()` (same total repeated in every row)
  9. Inpatient — IsInpatient
- **Per-column formatting:** All four date columns via `ToShortDateString()`; IsInpatient already "Yes"/"No" text; Total Transplants is the overall row count printed on each row.
- **Header/Footer:** Razor: none beyond the `<h2>` and banner. RDL: a 0.5in PageHeader defined (PrintOnFirstPage/PrintOnLastPage true) but empty; tablix has RepeatColumnHeaders/RepeatRowHeaders true. No generated-on, executed-by, filter strip, or page-number content.

## Open Questions
- The "Total Transplants" column repeats the overall `@Model.Count()` on every data row (identical to the banner value). Confirm this is intended (a per-row grand-total echo) rather than a per-patient count, since the migrated report should reproduce it exactly.
- RDL column-header order lists 8 data columns plus "Total Transplants" but the Razor view renders 9 columns; the RDL is skeletal and the Razor view was treated as authoritative for column order. Confirm the Razor rendering is the intended layout.
