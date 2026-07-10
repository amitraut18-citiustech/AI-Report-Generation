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
- **Legacy format:** .NET MVC (RDL + Razor) | SSRS (.rdl) | Crystal (.rpt via .md)
- **Description:** <one-line summary of what the report shows>
- **Source files:**
  | Role | File |
  |------|------|
  | Controller action | Controllers/ReportsController.cs → <Action>() |
  | Data service | DataServices/<Service>.cs → <Method>() |
  | ViewModel | Models/<Name>ReportViewModel.cs |
  | EF entities | Models/<Entity>.cs |
  | DbContext | Data/ApplicationDbContext.cs |
  | Razor view | Views/Reports/<Name>.cshtml |
  | RDL (layout hint) | Reports/<Name>.rdl <"(skeletal)" if no dataset/fields> |

## Database Context
- **Provider:** <EF Core + SQLite | SQL Server | ...>
- **Entities/tables used:** <e.g. Patients; TransplantEvents (Include Patient)>
- **Fields (from the ViewModel — authoritative):**
  | Field | .NET type | Direct / derived | Meaning |
  |-------|-----------|------------------|---------|
  | LastName | string | direct (Patients.LastName) | Patient last name |
  | PatientName | string | derived (`FirstName + " " + LastName`) | Full name |
  | IsInpatient | string | derived (`bool ? "Yes" : "No"`) | Inpatient flag as text |
  | ... | ... | ... | ... |
- **Relationships:** <FK relationships from DbContext, e.g. TransplantEvents.PatientId → Patients.Id (many-to-one)>

## Data Access
- **Method:** <Service.Method(), async?>
- **Query (plain English):** <source DbSet(s), Include/joins, Where filters, OrderBy/ThenBy>
- **Projection / derived fields:** <each computed field and its exact expression>
- **Read-only:** <AsNoTracking? yes/no>
- **Original LINQ (verbatim, for reference):**
  ```csharp
  <paste the .Select(...) projection and ordering>
  ```

## Business Logic
- <Filters, ordering, aggregations/counts (e.g. a `Model.Count()` summary), formatting.>
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
| Name | Type | Default | User-facing? | Purpose |
|------|------|---------|--------------|---------|
| ReportingYear | Integer | 2026 | yes | Filter: reporting year |
| dateFormat | String | M/d/yyyy | no | Report chrome |

## Layout
- **Title:** <text — from the Razor `<h2>`/RDL title>
- **Summary / cards:** <e.g. "Total Transplants: {count}", or _None._>
- **Table columns (in order, with header labels):** <as rendered in the Razor view>
- **Per-column formatting:** <e.g. dates via ToShortDateString(), bool→Yes/No>
- **Header/Footer:** <generated-on, executed-by, filters strip, page number — or _None._>

## Open Questions
- <Anything ambiguous the reviewer must confirm. "_None._" if fully understood.>
```

---

## Notes for the researcher
- The **ViewModel** is the authoritative source of the Fields table; the **data service**
  is the authoritative source of query logic and derived fields. The `.rdl` is a layout
  hint and is frequently skeletal — do not treat an empty RDL as "no fields."
- Capture derived fields exactly (concatenations, `bool ? "Yes" : "No"`, formatting) — the
  migrator reproduces them.
- Distinguish **filter parameters** (change the data) from **chrome parameters**
  (`dateFormat`, executed-by) that only affect display.
- The **Fields** table + **Data Access** section drive the migrator's row-object shape and
  its transforms — be complete and precise.
