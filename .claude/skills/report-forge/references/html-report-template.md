# HTML Report Template — Structure & Data Contract

The migrator emits three files per report into `HTMLReportsFolder/`:
`{report_key}.html`, `{report_key}.js`, `{report_key}.md`. This document defines the
contract they must follow.

## Runtime data contract

At runtime the .NET app runs the report's data service, gets a `List<...ReportViewModel>`,
and injects one global **before** the report JS runs. `rows` mirrors the ViewModel:

```js
window.REPORT_DATA = {
  parameters: { /* resolved filter params, camelCase; {} if the report takes none */ },
  rows: [ /* one object per ViewModel row; keys = ViewModel properties in camelCase */ ],
  narrative: "",                                  // LLM summary; may be empty
  meta: { generatedAt: "2026-07-06T10:00:00Z", executedBy: "jdoe", rowCount: 0 }
};

// Example row for TransplantEventReportViewModel:
// { patientName: "Jane Doe", dateOfVisit: "2026-02-11", dateOfPreviousVisit: "2025-11-03",
//   transplantDate: "2025-12-01", infusionDate: "2025-12-02", eventId: "EVT-1007",
//   transplantNumber: "2", isInpatient: "Yes" }
```

Rules:
- Render **only** from `window.REPORT_DATA`. No `fetch`/XHR/WebSocket, no external
  CSS/JS/fonts/images/CDN. Fully self-contained and offline-openable.
- If `REPORT_DATA` is absent or `rows` is empty, render a visible empty state. This lets a
  developer open the `.html` directly to review layout.
- **Derived fields (full name, `"Yes"/"No"`, etc.) arrive pre-computed in `rows`** — render
  them as-is; do not re-run server-side query logic in JS.
- JS handles only **view-level** concerns: date/number formatting to match the original
  view, aggregate summaries (e.g. `Total Transplants: rows.length`), and any conditional
  formatting/ordering the thought file assigns to the view.

## `{report_key}.html` skeleton

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title><!-- Report Title --></title>
  <style>
    /* Small, neutral, print-friendly styles. No external assets.
       Prefer system fonts; ensure @media print keeps the table readable. */
  </style>
</head>
<body>
  <main class="report" id="report">
    <header class="report__header">
      <h1 class="report__title"><!-- Report Title --></h1>
      <p class="report__filters" data-filters><!-- populated from parameters --></p>
    </header>

    <section class="report__summary" data-summary hidden>
      <!-- summary cards, e.g. total patient count -->
    </section>

    <section class="report__narrative" data-narrative hidden>
      <!-- LLM narrative injected here -->
    </section>

    <table class="report__table">
      <thead>
        <tr><!-- <th scope="col"> per column, in the thought file's order --></tr>
      </thead>
      <tbody data-rows>
        <!-- rows injected by JS -->
      </tbody>
    </table>

    <p class="report__empty" data-empty hidden>No data available.</p>

    <footer class="report__footer">
      <span data-generated></span>
      <span data-executed-by></span>
    </footer>
  </main>
  <script src="{report_key}.js" defer></script>
</body>
</html>
```

Use stable `data-*` hooks (`data-rows`, `data-summary`, `data-narrative`, `data-filters`,
`data-generated`, `data-executed-by`, `data-empty`) so the JS targets them without
brittle selectors.

## `{report_key}.js` shape

```js
(function () {
  "use strict";

  function getData() {
    return window.REPORT_DATA || { parameters: {}, rows: [], narrative: "", meta: {} };
  }

  // --- report-specific transforms (name them after the thought file's logic) ---
  // e.g. function bucketAgeGroup(dob) {...}  function retransplantColumns(rows, year) {...}

  function renderFilters(el, params) { /* ... */ }
  function renderSummary(el, rows) { /* ... */ }
  function renderNarrative(el, text) { /* show only if non-empty */ }
  function renderRows(tbody, rows) { /* build <tr>/<td>; apply conditional formatting */ }
  function renderFooter(data) { /* generatedAt, executedBy */ }
  function renderEmpty(show) { /* toggle empty state / table visibility */ }

  document.addEventListener("DOMContentLoaded", function () {
    var data = getData();
    var rows = Array.isArray(data.rows) ? data.rows : [];
    // apply sort/group/derived-column logic here, then render.
    if (!rows.length) { renderEmpty(true); }
    // ...render sections...
  });
})();
```

## `{report_key}.md` outline
- **Purpose** — what the report answers.
- **Columns** — each column and its meaning.
- **Parameters / filters** — user-facing filters and chrome params.
- **Business rules implemented** — transforms, grouping, conditional formatting.
- **Data contract** — the `REPORT_DATA` shape this report expects (row keys + param keys).
- **Deviations from source** — anything intentionally different from the original SSRS/Crystal report.
