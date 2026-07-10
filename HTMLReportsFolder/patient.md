# Patient Report

**Report key:** `patient`

## Purpose
A flat listing of all patients with their demographic and contact details, ordered by
last name. It answers: "Who are our patients and how do we reach them?" There is no
filtering, grouping, aggregation, or summary — every patient row is shown exactly once.

## Columns
Rendered left-to-right in this exact order:

| # | Header | Row key (`rows[].`) | Meaning | Formatting |
|---|--------|---------------------|---------|------------|
| 1 | First Name | `firstName` | Patient first name | as-is |
| 2 | Last Name | `lastName` | Patient last name; also the incoming sort key | as-is |
| 3 | Gender | `gender` | Patient gender | as-is |
| 4 | Date of Birth | `dateOfBirth` | Patient date of birth | short date (`M/d/yyyy`) |
| 5 | Contact Number | `contactNumber` | Contact number | as-is |
| 6 | Email | `email` | Email address | as-is |
| 7 | Phone Number | `phoneNumber` | Phone number | as-is |

## Parameters / filters
**None.** The report takes no arguments and returns all patient rows. No "filters applied"
strip is shown (the `[data-filters]` element stays hidden).

## Business rules implemented
- **No filtering** — all patient rows are rendered.
- **Ordering** — rows arrive already ordered ascending by `lastName` from the data
  service. The JS **preserves incoming order** and does not re-sort.
- **Date of Birth formatting** — `dateOfBirth` is formatted to match the Razor view's
  `DateTime.ToShortDateString()`, i.e. the default en-US pattern `M/d/yyyy` with no
  leading zeros. All other columns render directly.
- **No aggregations / summary** — no summary banner or totals card (footer shows a simple
  patient count derived from `meta.rowCount`, purely as chrome).
- **No conditional formatting / suppression** — none defined in the source.

## Data contract
This report renders only from `window.REPORT_DATA`:

```js
window.REPORT_DATA = {
  parameters: {},                 // report takes no parameters
  rows: [
    {
      firstName: "Jane",
      lastName: "Doe",
      gender: "Female",
      dateOfBirth: "1985-04-12",  // ISO-8601 or any Date-parseable string
      contactNumber: "555-0100",
      email: "jane.doe@example.com",
      phoneNumber: "555-0101"
    }
    // ...more rows, already ordered by lastName ascending
  ],
  narrative: "",                   // optional LLM summary; shown only if non-empty
  meta: { generatedAt: "2026-07-10T10:00:00Z", executedBy: "jdoe", rowCount: 1 }
};
```

- Row keys mirror `PatientReportViewModel` in camelCase. **No derived fields.**
- If `REPORT_DATA` is missing or `rows` is empty, a visible "No data available." empty
  state is shown and the table is hidden, so the HTML can be opened standalone for review.
- Fully self-contained: no network calls and no external CSS/JS/fonts/images.

## Deviations from source
- **Last column header** — uses "Phone Number" (the Razor view label), not the RDL's
  "Phone". Per the thought file, the Razor label is authoritative for the .NET app. See
  the flagged ambiguity below.
- **Footer** — the original Razor view has no footer; a neutral footer (generated
  timestamp, executed-by, patient count) is added from `meta` as standard report chrome.
  It carries no business logic.
- **Styling** — Bootstrap `table table-striped table-bordered table-dark` from the Razor
  view is reproduced with equivalent self-contained inline CSS (striped rows, bordered
  cells, dark header) since no external assets are permitted.

## Open questions carried from the thought file
- Minor label discrepancy: RDL header reads "Phone" while the Razor view reads "Phone
  Number". Implemented as "Phone Number" (Razor assumed authoritative) — please confirm.
- The EF Core database provider is not evident in the source files. It does not affect
  this static template (rendering is provider-agnostic), noted for completeness only.
