# Application Migration Context — PatientReports

This file holds the **application-specific** facts the Report Forge plugin needs to migrate
*this* project's reports. The plugin itself is generic (works with any SSRS report project);
everything particular to this codebase lives here (and in the per-report thought files).

The `report-researcher` and `report-migrator` agents read this file first, then apply the
plugin's generic process using these specifics.

## Host application

- **Stack:** ASP.NET Core MVC on **.NET 8**, Entity Framework Core + **SQLite** (`db/PatientDB.db`,
  recreated and seeded on startup via `SeedData`).
- **Project:** `DotNetApp/PatientReports/`.
- Reports are surfaced two ways at runtime:
  1. **SSRS/RDL** — the real `.rdl` rendered by `DotNetApp/RdlRenderService/` (a **.NET
     Framework 4.8** side-process hosting Microsoft ReportViewer `LocalReport`; the main app
     calls it over HTTP and shows the PDF in an iframe). See `ReportsController.RdlView`.
  2. **Plugin HTML** — the generated `HTMLReportsFolder/*.html` templates, populated by
     `ReportsController.HtmlReport` (the SSRS-replacement path). See below.

## A report here is a *bundle* of files

An `.rdl` in this app may be skeletal or rich; the report's real logic is spread across the
.NET code. When researching a report, read every part that exists:

| Concern | Where it lives | Example |
|---|---|---|
| Report wiring (name → data → view) | Controller action | `Controllers/ReportsController.cs` |
| Query / joins / ordering / **filters** | Data service method | `DataServices/PatientDataService.cs` |
| Derived / formatted fields | Data-service projection | `PatientName = First + " " + Last`; `IsInpatient ? "Yes":"No"` |
| Row shape & columns | ViewModel / flat DTO | `Models/*ReportViewModel.cs`, `Models/ClinicalFlatRow.cs` |
| DB schema, keys, relationships | EF entities + DbContext | `Models/*.cs`, `Data/ApplicationDbContext.cs` |
| Layout / headers / summaries | Razor view and/or `.rdl` | `Views/Reports/*.cshtml`, `Reports/*.rdl` |

## Rendering & filter model (important)

- **Fed data, not live SQL.** Both runtime paths render from data the .NET app fetched. For
  the SSRS path, `RdlRenderService` builds a `DataTable` from the fed rows and sets RDL
  parameters — **the RDL's SQL `<CommandText>`/`WHERE` never executes at render time.**
- **The host applies filters in code**, before feeding rows. Filtering lives in the data
  service (e.g. `GetClinicalFlatRowsAsync(fromDate, toDate, minAge, maxAge, status)`), never
  in the RDL or the generated JS. Rows arrive **pre-filtered**.
- SSRS report parameters (`FromDate`, `ToDate`, `MinAge`, `MaxAge`, `Status`, `rptUser`) are
  passed to the RDL only to drive its filter-echo/display; the data was already filtered.
  Note: adding an RDL parameter also requires a matching `ReportParametersLayout` cell, or
  ReportViewer rejects the definition.

## HTML runtime contract (how templates are served here)

`ReportsController.HtmlReport(report, …filters)`:
- resolves the template folder from `ReportForge:HtmlReportsPath` in `appsettings.json`
  (defaults to the repo-root `HTMLReportsFolder/`), with an upward-search fallback,
- runs the report's data service **with the filter query-string values applied**,
- serializes `{ parameters, rows, narrative, meta }` (System.Text.Json, **camelCase**),
- replaces the `<!-- REPORT_DATA -->` marker with `<script>window.REPORT_DATA = {…}</script>`
  and inlines the report's `.js`, then serves a self-contained page.
- **Accepted filter query-string keys** (clinical): `fromDate`, `toDate`, `minAge`, `maxAge`.
  The generated template's filter form reloads this endpoint with those keys.

## Artifact locations

| Artifact | Location |
|---|---|
| Thought files | `ReportThoughts/*.thought.md` (this folder) |
| HTML templates | `HTMLReportsFolder/{key}.{html,js,md}` (repo root) |
| Schema mapping | `DataSchemaMapping/*.json` |
| Legacy `.rdl` | `DotNetApp/PatientReports/Reports/*.rdl` (copied into RdlRenderService at build) |

## Report registry

| Key | Report | Data method | User filters |
|---|---|---|---|
| `patient` | Patient Report | `GetPatientReportAsync` | none |
| `transplant_event` | Transplant Event Report | `GetTransplantEventReportAsync` | Visit date from/to |
| `patient_clinical_summary` | Patient Clinical Summary | `GetClinicalFlatRowsAsync` | Visit date from/to, Min age, Max age |

## Conventions

- Report key: `snake_case`, reused across the `.rdl`, thought file, HTML/JS/md, and the
  `report` route value.
- New reports: add the `.rdl` + data method + (optionally) ViewModel/DTO, then run the
  plugin (research → review → migrate). Update this registry.
