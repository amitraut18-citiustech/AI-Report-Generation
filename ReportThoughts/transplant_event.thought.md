# Report Thought: Transplant Event Report

**Report key:** transplant_event

## Source
- **Legacy format:** SSRS (.rdl) -- rich (has dataset with fields, query, tablix filters, and parameters)
- **Description:** Lists transplant events with their associated patient names, visit dates, transplant details, and inpatient status, optionally filtered by visit date range.
- **Source files:**
  | Role | File |
  |------|------|
  | Report wiring (name -> data -> output) | `Controllers/ReportsController.cs` (route value `"transplant"` -> key `"transplant_event"`) |
  | Data access (query + projection) | `DataServices/PatientDataService.cs` -> `GetTransplantEventReportAsync()` |
  | Row shape (view model / DTO) | `Models/TransplantEventReportViewModel.cs` |
  | Data model / schema | `Models/TransplantEvent.cs`, `Models/Patient.cs` |
  | DB context | `Data/ApplicationDbContext.cs` |
  | View / layout | `Views/Reports/TransplantEventReport.cshtml` + partial `Views/Reports/_TransplantEventReport.cshtml` |
  | Legacy RDL | `Reports/TransplantEventReport.rdl` (rich -- real dataset, fields, tablix filters, parameters) |
  | RDL render-side row model | `RdlRenderService/RowModels.cs` -> `TransplantEventRow` (adds `TotalTransplants`) |
  | RDL render logic | `RdlRenderService/RdlRenderer.cs` (computes `TotalTransplants` per patient) |

## Database Context
- **Provider / data source:** EF Core + SQLite (`db/PatientDB.db`, recreated/seeded on startup)
- **Entities/tables used:** `TransplantEvents` (joined to `Patients` via FK `PatientId`)
- **Fields (from the row shape -- authoritative):**
  | Field | Type | Direct / derived | Meaning |
  |-------|------|------------------|---------|
  | PatientName | string | derived (`Patient.FirstName + " " + Patient.LastName`) | Full name of the patient associated with the event |
  | DateOfVisit | DateTime | direct (`TransplantEvents.DateOfVisit`) | Date the transplant visit occurred |
  | DateOfPreviousVisit | DateTime | direct (`TransplantEvents.DateOfPreviousVisit`) | Date of the patient's previous visit |
  | TransplantDate | DateTime | direct (`TransplantEvents.TransplantDate`) | Date the transplant was performed |
  | InfusionDate | DateTime | direct (`TransplantEvents.InfusionDate`) | Date the infusion was administered |
  | EventId | string | direct (`TransplantEvents.EventId`) | Unique event identifier |
  | TransplantNumber | string | direct (`TransplantEvents.TransplantNumber`) | Transplant number identifier |
  | IsInpatient | string | derived (`bool ? "Yes" : "No"`) | Whether the event was inpatient, converted from boolean to display text |
  | TotalTransplants | int | derived (see note) | Count of transplant events -- see "TotalTransplants discrepancy" in Open Questions |

- **Relationships:**
  - `TransplantEvents.PatientId` -> `Patients.Id` (many-to-one, cascade delete)
  - `TransplantEvents.ProviderId` -> `Providers.Id` (many-to-one, restrict delete) -- not used by this report
  - `TransplantEvents` has a collection of `LabResults` -- not used by this report

## Data Access
- **Method:** `PatientDataService.GetTransplantEventReportAsync()`
- **Query (plain English):** From the `TransplantEvents` table, eagerly load the related `Patient` navigation property. Project each event into a `TransplantEventReportViewModel` with the patient's full name concatenated, all date fields carried through directly, and the boolean `IsInpatient` converted to "Yes"/"No" text. Order the results by `DateOfVisit` ascending. No date-range or other filtering is applied in this method -- all rows are returned.
- **Projection / derived fields:**
  - `PatientName` = `e.Patient.FirstName + " " + e.Patient.LastName` (string concatenation)
  - `IsInpatient` = `e.IsInpatient ? "Yes" : "No"` (boolean to display text)
  - All other fields are direct pass-through from the `TransplantEvent` entity
- **Read-only:** Yes (`AsNoTracking()`)
- **Original query (verbatim, for reference):**
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
- **Derived fields:**
  - `PatientName`: concatenation of `Patient.FirstName`, a space, and `Patient.LastName`.
  - `IsInpatient`: the entity stores this as a `bool`; the projection converts it to the string `"Yes"` or `"No"`.
  - `TotalTransplants`: not produced by the data service. The RDL render service (`RdlRenderer.cs`) computes it as the count of rows grouped by `PatientName` (i.e., how many transplant events that patient has). The Razor view instead displays `Model.Count()` -- the total number of all rows -- in every row of this column. These two meanings differ (per-patient count vs. global count).
- **Summary banner:** The Razor partial displays an info banner: "Total Transplants: {count of all rows}" above the table.
- **Row-count per row:** In the Razor view, every row in the "Total Transplants" column shows the global count (`Model.Count()`). In the RDL path, each row shows the count of events for that patient specifically.
- **Legacy RDL expressions:**
  - Date formatting: `=Format(Fields!DateOfVisit.Value, "MM/dd/yyyy")` -- all four date columns use this format.
  - Alternating row color: `=IIF(RowNumber(Nothing) Mod 2 = 1, "#F2F2F2", "White")` -- zebra striping on detail rows.
  - `TotalTransplants` is rendered as `=Fields!TotalTransplants.Value` (the value computed by the render service).

## Conditional Logic
- **Alternating row background:** RDL uses `=IIF(RowNumber(Nothing) Mod 2 = 1, "#F2F2F2", "White")` on every detail cell. Odd rows get light gray (#F2F2F2), even rows get white. The Razor view achieves the same via Bootstrap's `table-striped` class.
- No visibility expressions or row suppression.

## Grouping & Sorting
- **Grouping:** None. The RDL has a `<Group Name="Details">` on the detail row, but this is a standard SSRS detail group (one row per data row), not a true grouping. The group does carry the `FromDate`/`ToDate` filters (see Parameters).
- **Sorting:** Ordered by `DateOfVisit` ascending (applied in the LINQ query). The RDL's embedded SQL also specifies `ORDER BY te.DateOfVisit`, consistent with the data service. No additional sort expressions in the RDL tablix.

## Parameters

| Name | Type | Control | Default | Filters what (how) |
|------|------|---------|---------|--------------------|
| FromDate | DateTime | date | 2026-01-01 (`=CDate("2026-01-01")`) | DateOfVisit >= value (applied as RDL tablix filter, NOT in host data service) |
| ToDate | DateTime | date | 2026-12-31 (`=CDate("2026-12-31")`) | DateOfVisit <= value (applied as RDL tablix filter, NOT in host data service) |

**Important filter-application note:** Unlike the clinical report (where filters are applied in the data service before feeding data), the transplant event report's date filters are applied differently depending on the runtime path:
- **RDL path:** The controller calls `GetTransplantEventReportAsync()` (returns ALL rows, unfiltered), passes `FromDate`/`ToDate` as RDL parameters, and the RDL's tablix-level `<Filter>` elements apply `DateOfVisit >= FromDate` and `DateOfVisit <= ToDate` at render time.
- **HTML path:** The controller calls `GetTransplantEventReportAsync()` (returns ALL rows, unfiltered) and does NOT parse or apply `fromDate`/`toDate` query-string parameters at all. No date filtering occurs.
- **Data service:** `GetTransplantEventReportAsync()` accepts no parameters and returns all rows.

No chrome parameters (no `rptUser`, `dateFormat`, etc.).

## Layout
- **Title:** "Transplant Event Report" (Razor view `ViewData["Title"]` and RDL title textbox; RDL: centered, 16pt bold, Segoe UI, color #1f3864)
- **Summary / cards:** Razor view shows an info-level alert banner: "Total Transplants: {row count}" above the table.
- **Table columns (in order, with header labels):**
  1. Patient
  2. Date of Visit
  3. Previous Visit (RDL header) / Date of Previous Visit (Razor header)
  4. Transplant Date
  5. Infusion Date
  6. Event ID
  7. Transplant Number
  8. Total Transplants
  9. Inpatient
- **Per-column formatting:**
  - All date columns (Date of Visit, Previous Visit, Transplant Date, Infusion Date): RDL uses `MM/dd/yyyy` format; Razor uses `.ToShortDateString()` (locale-dependent).
  - IsInpatient: already converted to "Yes"/"No" text in the projection.
  - PatientName, EventId, TransplantNumber: plain text, no special formatting.
  - TotalTransplants: integer, no special formatting.
- **Header style:** RDL uses dark background (#212529) with bold white text, 6pt left padding, vertically centered. Razor uses Bootstrap `table-dark` class (visually equivalent).
- **Detail row style:** RDL uses alternating #F2F2F2 / White rows, 6pt left padding, vertically centered. Razor uses Bootstrap `table-striped`.
- **Header/Footer:** RDL has a page header (0.5in, prints on first and last pages) but no content defined in it. Page layout is landscape-oriented (11in wide x 8.5in tall). No footer defined.

## Resolved Questions
- **TotalTransplants → per-patient count.** The RDL render path groups by PatientName and counts per patient (`RdlRenderer.cs` lines 26-31). The Razor `Model.Count()` is a simplified global count. The JS template must compute TotalTransplants by grouping rows by PatientName and counting, consistent with the RDL intent.
- **Date filtering → handled by the runtime query service.** The data service returns all rows; date filtering is applied at runtime by the .NET ReportQueryService using the brain's structured query spec. The template does not need its own date filter controls.
- **Header label → "Previous Visit"** (shorter, fits table layout; column context makes the date meaning obvious).
