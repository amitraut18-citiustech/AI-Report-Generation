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
- **Type:** SSRS (.rdl) | Crystal (.rpt via .md)
- **File:** <relative/path/to/source>
- **Description:** <the report's own <Description>, or a one-line summary>

## Database Context
- **Data Source:** <name> (<"fed DataSet — CommandText Not Used" | connection info>)
- **Dataset(s):** <DataSet name(s)>
- **Fields:**
  | Field | Type | Meaning |
  |-------|------|---------|
  | MRN | System.String | Medical Record Number (identifier) |
  | ... | ... | ... |
- **Inferred entities/tables:** <tables the fields imply, marked "inferred">
- **Relationships:** <FK relationships if determinable, else _None._>

## Queries
- **Main Query:** <the real SQL if present; otherwise:>
  _No embedded SQL — dataset is fed by the .NET app. Expected input shape:_ <describe rows>

## Business Logic
- <Decode every non-trivial expression to plain English.>
- **Example — relative-year columns:** `GF_Transplants_0..3` = graft-failure retransplants
  for reporting year and the three prior years (`ReportingYear`, `-1`, `-2`, `-3`).
- **Calculated fields / aggregations:** <Sum/Count/CASE/IIF logic>

## Conditional Logic
- <Visibility (`Hidden`) expressions, row suppression, conditional formatting.>
- _None._ if not present.

## Grouping & Sorting
- **Grouping:** <group expressions, or _None._>
- **Sorting:** <sort expressions, or _None._>

## Parameters
| Name | Type | Default | User-facing? | Purpose |
|------|------|---------|--------------|---------|
| ReportingYear | Integer | 2026 | yes | Filter: reporting year |
| dateFormat | String | M/d/yyyy | no | Report chrome |
| rptUser | String | — | no | Footer: executed-by |

## Layout
- **Title:** <text>
- **Summary / cards:** <e.g. "Number of patients">
- **Table columns (in order):** <header list>
- **Header/Footer:** <generated-on expr, page-number expr, filters strip, executed-by>

## Open Questions
- <Anything ambiguous the reviewer must confirm. "_None._" if fully understood.>
```

---

## Notes for the researcher
- Decode expressions; never leave a raw `=...` in the file uninterpreted.
- Distinguish **filter parameters** (change the data) from **chrome parameters**
  (`rptUser`, `dateFormat`) that only affect display.
- The **Fields** table drives the migrator's row-object shape — be complete and precise.
