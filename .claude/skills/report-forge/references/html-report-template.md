# HTML Report Template — Structure & Data Contract

The migrator emits three files per report into `HTMLReportsFolder/`:
`{report_key}.html`, `{report_key}.js`, `{report_key}.md`. This document defines the
contract they must follow.

## Runtime data contract

At runtime the .NET host runs the report's data service **with the report's parameters
applied as data filters**, then injects one global **before** the report JS runs. The
rows are already the filtered result set — the template never filters them:

```js
window.REPORT_DATA = {
  // The filter values the host applied for THIS render. Keys are camelCase and match
  // the filter-form input names 1:1 (e.g. fromDate, toDate, minAge, maxAge, status).
  // {} when the report has no user filters.
  parameters: { fromDate: "2026-01-01", toDate: "2026-12-31", minAge: 0, maxAge: 120 },
  // One object per already-filtered row; keys = ViewModel/DTO properties in camelCase.
  rows: [ /* ... */ ],
  narrative: "",                                  // LLM summary; may be empty
  meta: { generatedAt: "2026-07-06T10:00:00Z", executedBy: "jdoe", rowCount: 0 }
};
```

Rules:
- **The host filters the data, not the template.** `rows` is the post-filter result set.
  The JS must **never** re-implement the report's WHERE/parameter logic — no client-side
  date/age/status filtering, no re-running server query logic. Render `rows` as given.
  (Why: SSRS reports here are rendered from *fed* data — the RDL's SQL `WHERE` does not
  execute — so the host applies parameters in code and hands over filtered rows. The HTML
  template must follow the same model.)
- **Derived fields (full name, `"Yes"/"No"`, Age, BMI, etc.) arrive pre-computed** in
  `rows` — render as-is.
- JS handles only **view-level** concerns: date/number formatting, aggregate summaries
  (e.g. `Total: rows.length`), grouping/ordering for display, and conditional formatting.
- Render **only** from `window.REPORT_DATA` plus the filter round-trip below. No `fetch`/
  XHR/WebSocket, no external CSS/JS/fonts/images/CDN. Self-contained and offline-openable.
- If `REPORT_DATA` is absent or `rows` is empty, render a visible empty state.

## Filters (interactive) — only when the report has user parameters

If the thought file's **Parameters** section lists user-facing filters, the template
renders a real filter form so the user can change them and regenerate. The form
**round-trips to the host** (which re-queries with the new values and re-injects
`REPORT_DATA`); the template still never filters locally.

Contract:
- Emit a `<form data-filter-form>` containing one control per parameter, its `name` equal
  to the parameter key (camelCase, matching `REPORT_DATA.parameters`), plus an **Apply
  filters** submit button. Choose the control from the parameter's type: `date` →
  `<input type="date">`, integer → `<input type="number">`, enum → `<select>` with the
  allowed values, string → `<input type="text">`.
- On load, the JS **populates each control's value from `REPORT_DATA.parameters`** so the
  form reflects the applied filters.
- On submit, the JS **merges the control values into the current page's query string and
  reloads** (`location.search`), preserving any existing routing params (e.g. `report=`).
  Do **not** rely on a plain form GET (that would drop routing params). Example:
  ```js
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var qs = new URLSearchParams(location.search);
    form.querySelectorAll("[name]").forEach(function (el) { qs.set(el.name, el.value); });
    location.search = qs.toString();   // host re-filters and re-injects REPORT_DATA
  });
  ```
- Also render a read-only **applied-filters echo** line for print/context.
- Reports with **no** parameters omit the form entirely.

**Host responsibility (document this in the `.md`):** the endpoint that serves the
template must accept the parameter names as query-string values, apply them as data
filters, and set `REPORT_DATA.parameters` to the applied values. (The generated HTML is
host-agnostic; it only reads/writes the query string.)

## `{report_key}.html` skeleton

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title><!-- Report Title --></title>
  <style>/* small, neutral, print-friendly styles; no external assets */</style>
</head>
<body>
  <main class="report" id="report">
    <header class="report__header">
      <h1 class="report__title"><!-- Report Title --></h1>

      <!-- Only when the report has parameters. Inputs named after parameter keys. -->
      <form class="report__filterform" data-filter-form>
        <!-- e.g. <label>Visit from <input type="date" name="fromDate"></label> -->
        <!-- e.g. <label>Min age <input type="number" name="minAge" min="0"></label> -->
        <button type="submit">Apply filters</button>
      </form>

      <p class="report__filters" data-filters><!-- read-only applied-filters echo --></p>
    </header>

    <section class="report__summary" data-summary hidden></section>
    <section class="report__narrative" data-narrative hidden></section>

    <table class="report__table">
      <thead><tr><!-- <th scope="col"> per column --></tr></thead>
      <tbody data-rows></tbody>
    </table>

    <p class="report__empty" data-empty hidden>No data available.</p>

    <footer class="report__footer">
      <span data-generated></span>
      <span data-executed-by></span>
    </footer>
  </main>

  <!-- REPORT_DATA -->
  <script src="{report_key}.js" defer></script>
</body>
</html>
```

**The `<!-- REPORT_DATA -->` marker is required and must appear immediately before the
`<script src>` tag.** The host replaces this exact comment with an inline
`<script>window.REPORT_DATA = {…};</script>`. Being a plain (non-deferred) inline script
before the deferred report JS, the data is set first. Keep the comment byte-for-byte. If
left in place (opened standalone), the JS falls back to an empty dataset / empty state.

Use stable `data-*` hooks (`data-rows`, `data-summary`, `data-narrative`, `data-filters`,
`data-filter-form`, `data-generated`, `data-executed-by`, `data-empty`).

## `{report_key}.js` shape

```js
(function () {
  "use strict";

  function getData() {
    return window.REPORT_DATA || { parameters: {}, rows: [], narrative: "", meta: {} };
  }

  // Populate filter inputs from applied parameters, and reload via the query string
  // on submit (host re-filters). NEVER filter rows here.
  function wireFilterForm(params) {
    var form = document.querySelector("[data-filter-form]");
    if (!form) return;
    Object.keys(params || {}).forEach(function (k) {
      var el = form.querySelector('[name="' + k + '"]');
      if (el != null && params[k] != null) el.value = params[k];
    });
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var qs = new URLSearchParams(location.search);
      form.querySelectorAll("[name]").forEach(function (el) { qs.set(el.name, el.value); });
      location.search = qs.toString();
    });
  }

  // --- report-specific view transforms (formatting, grouping, aggregates) ---

  document.addEventListener("DOMContentLoaded", function () {
    var data = getData();
    var rows = Array.isArray(data.rows) ? data.rows : [];   // already filtered by host
    wireFilterForm(data.parameters || {});
    // render filters echo, summary, grouped/formatted rows, footer; empty-state if !rows.length
  });
})();
```

## `{report_key}.md` outline
- **Purpose** — what the report answers.
- **Columns** — each column and its meaning.
- **Filters / parameters** — each user filter, its control type, and **which query-string
  key the host must accept and how it filters the data**.
- **Business rules implemented** — view-level transforms, grouping, conditional formatting.
- **Data contract** — the `REPORT_DATA` shape (row keys + parameter keys). State clearly
  that rows arrive pre-filtered.
- **Deviations from source** — anything intentionally different from the original report.
