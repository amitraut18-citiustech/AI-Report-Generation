# Transplant Event Report

## Purpose
Lists every transplant event in the system, one row per event, joined to its patient.
Each row shows the patient name, visit/transplant/infusion dates, event and transplant
identifiers, an inpatient flag, and a repeated overall transplant count. A summary banner
shows the total number of transplant events. There is no filtering — all events are shown.

## Columns
In this exact order (matching the source Razor view):

| # | Header | Source field | Notes |
|---|--------|--------------|-------|
| 1 | Patient | `patientName` | Full name, derived server-side (`FirstName + " " + LastName`). Rendered as-is. |
| 2 | Date of Visit | `dateOfVisit` | Formatted as short date. Rows arrive already ordered ascending by this field. |
| 3 | Date of Previous Visit | `dateOfPreviousVisit` | Formatted as short date. |
| 4 | Transplant Date | `transplantDate` | Formatted as short date. |
| 5 | Infusion Date | `infusionDate` | Formatted as short date. |
| 6 | Event ID | `eventId` | Event identifier text. |
| 7 | Transplant Number | `transplantNumber` | Transplant number/label text. |
| 8 | Total Transplants | (computed) | The overall row count (`rows.length`), repeated identically on every row. |
| 9 | Inpatient | `isInpatient` | `"Yes"`/`"No"` text, derived server-side. Rendered as-is. |

## Parameters / filters
None. The report takes no parameters and returns every transplant event. The filters strip
renders a neutral "No filters applied" note.

## Business rules implemented
- **No filtering / preserve order.** All rows are rendered in the incoming order (the data
  service orders ascending by `dateOfVisit`); the JS does not re-sort.
- **Total Transplants echo.** The "Total Transplants" column prints the overall row count
  (`rows.length`) on every row — an intentional per-row grand-total echo, reproduced exactly
  from the original view (`@Model.Count()`). The same value drives the summary banner
  ("Total Transplants: {count}").
- **Date formatting.** The four date columns are formatted with `toLocaleDateString()` to
  mirror .NET `ToShortDateString()`. Unparseable values are rendered verbatim.
- **Derived fields rendered as-is.** `patientName` and `isInpatient` ("Yes"/"No") are
  computed server-side and are NOT recomputed in the browser.
- **Empty state.** If `REPORT_DATA` is missing or `rows` is empty, the table is hidden and a
  visible "No data available" placeholder is shown. The banner then reads
  "Total Transplants: 0".

## Data contract
The .NET app injects `window.REPORT_DATA` before this report's JS runs:

```js
window.REPORT_DATA = {
  parameters: {},          // none for this report
  rows: [
    {
      patientName: "Jane Doe",
      dateOfVisit: "2026-02-11",
      dateOfPreviousVisit: "2025-11-03",
      transplantDate: "2025-12-01",
      infusionDate: "2025-12-02",
      eventId: "EVT-1007",
      transplantNumber: "2",
      isInpatient: "Yes"
    }
    // ... one object per TransplantEventReportViewModel row, ordered by dateOfVisit asc
  ],
  narrative: "",           // optional LLM summary; hidden when empty
  meta: { generatedAt: "2026-07-06T10:00:00Z", executedBy: "jdoe", rowCount: 0 }
};
```

Row keys mirror `TransplantEventReportViewModel` in camelCase. The report renders only from
`window.REPORT_DATA` — no network calls, no external assets.

### .NET host integration
The HTML contains an injection marker immediately before the report script:

```html
<!-- REPORT_DATA -->
<script src="transplant_event.js" defer></script>
```

At runtime the .NET host serializes `GetTransplantEventReportAsync()` (System.Text.Json →
camelCase, ISO-8601 dates) and replaces the marker with
`<script>window.REPORT_DATA = {…};</script>`. The inline script is non-deferred, so it runs
before the deferred `transplant_event.js`. Serve `transplant_event.html` and
`transplant_event.js` from the same URL path (the `<script src>` is relative).

## Deviations from source
- The original RDL is a skeletal layout stub (title text and hard-coded header cells only,
  no dataset/fields); the Razor view was treated as authoritative for the 9-column layout,
  as recorded in the thought file's Open Questions.
- A footer (generated-on, executed-by, row count) is added for the static-report chrome.
  The original view had no footer content; this is purely additive and driven by
  `REPORT_DATA.meta`.
