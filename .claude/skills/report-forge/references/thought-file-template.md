# Thought File Template

Every thought file lives at `ReportThoughts/{report_key}.thought.md` and follows the
structure below. Keep headings exactly as shown so downstream tooling and the migrator can
locate sections reliably. Fill every section; if a section does not apply, write
`_None._` rather than deleting it.

---

```markdown
# Report Thought: <Human Report Title>

**Report key:** <report_key>

## Source
- **Legacy format:** SSRS (.rdl) | Crystal (.rpt via .md) — note if the RDL is skeletal or rich
- **Description:** <one-line summary of what the report shows>
- **Source files:** _(roles are generic; the actual files depend on the host stack — see the
  application migration context. Fill in whichever exist.)_
  | Role | File |
  |------|------|
  | Report wiring (name → data → output) | <route / action / registry entry> |
  | Data access (query + projection) | <data method / query> |
  | Row shape (view model / DTO) | <the object the renderer receives> |
  | Data model / schema | <entities / schema definition> |
  | View / layout | <view template, if any> |
  | Legacy RDL | Reports/<Name>.rdl <"(skeletal)" if no dataset/fields> |

## Database Context
- **Provider / data source:** <e.g. EF Core + SQLite | SQL Server | REST | ...>
- **Entities/tables used:** <e.g. Patients; TransplantEvents (joined to Patient)>
- **Fields (from the row shape — authoritative):**
  | Field | Type | Direct / derived | Meaning |
  |-------|------|------------------|---------|
  | LastName | string | direct (Patients.LastName) | Patient last name |
  | PatientName | string | derived (`FirstName + " " + LastName`) | Full name |
  | IsInpatient | string | derived (`bool ? "Yes" : "No"`) | Inpatient flag as text |
  | ... | ... | ... | ... |
- **Relationships:** <FK relationships, e.g. TransplantEvents.PatientId → Patients.Id (many-to-one)>

## Data Access
- **Method:** <data method / query entry point>
- **Query (plain English):** <source table(s)/set(s), joins, filters, ordering>
- **Projection / derived fields:** <each computed field and its exact expression>
- **Read-only:** <yes/no>
- **Original query (verbatim, for reference):**
  ```
  <paste the projection + ordering in the host language (LINQ / SQL / etc.)>
  ```

## Business Logic
- <Filters, ordering, aggregations/counts (e.g. a row-count summary), formatting.>
- **Derived fields:** <full-name concatenation, bool→Yes/No, etc.>
- **Legacy RDL expressions (if any):** <decode `=Parameters!X.Value-3`, IIF/CASE, Sum/Count>
  _None._ if the RDL is a skeletal layout stub.

## Conditional Logic
- <Visibility (`Hidden`) expressions, row suppression, conditional formatting.>
- _None._ if not present.

## Grouping & Sorting
- **Grouping:** <group expressions, or _None._>
- **Sorting:** <sort expressions, or _None._>

## Parameters
_From controller/action parameters, query-string inputs, or RDL `<ReportParameter>`s.
If the report currently takes none, write `_None — returns all rows._`_

For each **user-facing filter**, record the control type (so the migrator can render the
right input) and exactly **what it filters and how** (so the host can apply it in code —
remember the RDL's SQL `WHERE` does not run at render time; the host filters the fed data).

| Name | Type | Control | Default | Filters what (how) |
|------|------|---------|---------|--------------------|
| FromDate | DateTime | date | 2026-01-01 | DateOfVisit >= value |
| ToDate | DateTime | date | 2026-12-31 | DateOfVisit <= value |
| MinAge | Integer | number | 0 | patient Age >= value |
| MaxAge | Integer | number | 120 | patient Age <= value |
| Status | String | select(All,Active,Inactive) | All | patient Status == value (All = no filter) |

Note **chrome parameters** (e.g. `dateFormat`, `rptUser`) separately — they affect display
only and are **not** filter controls.

## Layout
- **Title:** <text — from the view heading / RDL title>
- **Summary / cards:** <e.g. "Total Transplants: {count}", or _None._>
- **Table columns (in order, with header labels):** <as rendered in the source view>
- **Per-column formatting:** <e.g. dates → short date, bool→Yes/No>
- **Header/Footer:** <generated-on, executed-by, filters strip, page number — or _None._>

## Open Questions
- <Anything ambiguous the reviewer must confirm. "_None._" if fully understood.>
```

---

## Notes for the researcher
- The **row shape** (view model / DTO) is the authoritative source of the Fields table; the
  **data access** code is the authoritative source of query logic and derived fields. A
  skeletal `.rdl` is only a layout hint — do not treat an empty RDL as "no fields"; a rich
  `.rdl` is a primary source too.
- Capture derived fields exactly (concatenations, `bool ? "Yes" : "No"`, formatting) — the
  migrator reproduces them.
- Distinguish **filter parameters** (change the data) from **chrome parameters**
  (date format, executed-by) that only affect display.
- The **Fields** table + **Data Access** section drive the migrator's row-object shape and
  its transforms — be complete and precise.
