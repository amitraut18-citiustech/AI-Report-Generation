# Transplant Event Report

## Purpose

Lists transplant events with their associated patient names, visit dates, transplant details, and inpatient status. Optionally filtered by visit date range (filtering is handled server-side by the host runtime query service).

## Columns

| # | Header | Row key (camelCase) | Type | Description |
|---|--------|---------------------|------|-------------|
| 1 | Patient | `patientName` | string | Full name (FirstName + " " + LastName), pre-computed by the host |
| 2 | Date of Visit | `dateOfVisit` | DateTime (ISO string) | Date the transplant visit occurred; formatted MM/dd/yyyy |
| 3 | Previous Visit | `dateOfPreviousVisit` | DateTime (ISO string) | Date of the patient's previous visit; formatted MM/dd/yyyy |
| 4 | Transplant Date | `transplantDate` | DateTime (ISO string) | Date the transplant was performed; formatted MM/dd/yyyy |
| 5 | Infusion Date | `infusionDate` | DateTime (ISO string) | Date the infusion was administered; formatted MM/dd/yyyy |
| 6 | Event ID | `eventId` | string | Unique event identifier |
| 7 | Transplant Number | `transplantNumber` | string | Transplant number identifier |
| 8 | Total Transplants | *(computed in JS)* | int | Per-patient count of transplant events in the result set (not a row field -- computed client-side) |
| 9 | Inpatient | `isInpatient` | string | "Yes" or "No", pre-computed by the host |

## Parameters / Filters

The report supports date-range filtering via `fromDate` and `toDate`. However, filtering is handled entirely by the host runtime query service -- the template does **not** include an interactive filter form. Rows arrive pre-filtered.

If `REPORT_DATA.parameters` contains `fromDate` or `toDate`, the template renders a read-only applied-filters echo showing the active date range.

**Host responsibility:** The endpoint serving this template must accept `fromDate` and `toDate` as query-string parameters, apply them as filters on `DateOfVisit`, and set `REPORT_DATA.parameters` accordingly.

## Business Rules Implemented (JS view-level)

1. **TotalTransplants (per-patient count):** The JS groups `rows` by `patientName` and counts occurrences per patient. Each row's "Total Transplants" cell shows how many events that patient has in the current result set. This matches the RDL render service behavior (`RdlRenderer.cs`), not the Razor view's simplified global `Model.Count()`.

2. **Date formatting:** All four date columns are formatted as `MM/dd/yyyy`, matching the RDL's `=Format(Fields!DateOfVisit.Value, "MM/dd/yyyy")`.

3. **Summary banner:** Displays "Total Transplants: {row count}" above the table -- the total number of rows in the result set, matching the Razor view's info alert.

4. **Alternating row colors:** Odd rows use `#f2f2f2`, even rows use white, matching the RDL's zebra striping expression.

5. **Sort order:** Rows are rendered in the order received. The host data service orders by `DateOfVisit` ascending.

## Data Contract

```js
window.REPORT_DATA = {
  parameters: {
    fromDate: "2026-01-01",   // optional, ISO date string
    toDate: "2026-12-31"      // optional, ISO date string
  },
  rows: [
    {
      patientName: "John Smith",
      dateOfVisit: "2026-03-15T00:00:00",
      dateOfPreviousVisit: "2026-01-10T00:00:00",
      transplantDate: "2026-03-15T00:00:00",
      infusionDate: "2026-03-16T00:00:00",
      eventId: "EVT-001",
      transplantNumber: "TX-100",
      isInpatient: "Yes"
    }
  ],
  narrative: "",              // LLM-generated summary; may be empty (see Narrative Rendering below)
  meta: {
    generatedAt: "2026-07-13T10:00:00Z",
    executedBy: "jdoe",
    rowCount: 1
  }
};
```

Rows arrive **pre-filtered** by the host. The JS never re-implements date-range or other filtering logic.

Note: `totalTransplants` is **not** a row field. The JS computes it by grouping rows by `patientName`.

## Property Name Mapping

| ViewModel (C# PascalCase) | Row key (camelCase) | Notes |
|----------------------------|---------------------|-------|
| PatientName | patientName | Derived: FirstName + " " + LastName |
| DateOfVisit | dateOfVisit | Direct |
| DateOfPreviousVisit | dateOfPreviousVisit | Direct |
| TransplantDate | transplantDate | Direct |
| InfusionDate | infusionDate | Direct |
| EventId | eventId | Direct |
| TransplantNumber | transplantNumber | Direct |
| IsInpatient | isInpatient | Derived: bool -> "Yes"/"No" |

## Narrative Rendering

When `narrative` is non-empty, `renderNarrative()` builds a styled card:

- **Header:** Dark navy bar with an SVG info icon and the label "AI Summary" (`.report__narrative-header`)
- **Body:** The narrative text is split into paragraphs (every two sentences grouped) and rendered as `<p>` elements (`.report__narrative-body`)
- **Chart:** If `window.REPORT_DATA.chart` is present (type, title, labels, values), a Chart.js canvas is inserted after the narrative section (charts are disabled by default via the brain's `ENABLE_CHARTS` setting, so this field is normally absent)

The narrative section is hidden when `narrative` is empty.

## Deviations from Source

1. **"Previous Visit" header:** Uses "Previous Visit" instead of the Razor view's "Date of Previous Visit" for brevity. The RDL also used "Previous Visit". Column context makes the date meaning clear.

2. **TotalTransplants per-patient (not global):** The Razor view showed `Model.Count()` (total row count) in every row of the Total Transplants column. This template follows the RDL render service intent: each row shows the count of events for that specific patient. This is a deliberate correction of the Razor view's oversimplification.

3. **No interactive filter form:** Date filtering is handled by the host runtime query service. The template omits filter controls and only shows a read-only echo of applied filter values.
