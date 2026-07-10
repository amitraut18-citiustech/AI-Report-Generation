---
name: report-forge
description: >-
  Build-time (Phase 1) migration of legacy SSRS/Crystal reports into the AI Report
  Forge platform. Use this when the user wants to analyze existing report definitions
  (.rdl / .rpt docs), produce reviewable "thought files" capturing each report's
  business logic, generate static HTML+JS report templates from those thought files,
  or build the SQL Server schema-mapping / PHI-marker artifacts that Phase 2 consumes.
  Triggers on: "migrate reports", "analyze this rdl", "generate thought file",
  "build html report", "report forge", "schema mapping", "phi markers".
---

# Report Forge — Phase 1 (Build-Time Report Migration)

Phase 1 is a **build-time** workflow that runs inside the .NET report project during
development. It replaces the SSRS/Crystal Reports authoring cycle with an AI pipeline
that reads legacy report definitions and emits static, version-controlled artifacts.
Nothing here runs at runtime — the outputs are committed to the repo and later loaded
by the Phase 2 Python "brain" service.

> Full architecture and rationale: [../../plan/ai-driven-reporting-poc.md](../../plan/ai-driven-reporting-poc.md)

## The pipeline

```
A report "bundle" (see below)
        │
        │  1a RESEARCH  ── report-researcher agent
        ▼
ReportThoughts/*.thought.md            ← reviewable business-logic analysis
        │
        │  1b MIGRATION ── report-migrator agent
        ▼
HTMLReportsFolder/*.html + *.js + *.md ← static templates + docs
        
DataSchemaMapping/schema-mapping.json  ← 1c SCHEMA ── schema-mapper agent
DataSchemaMapping/phi-markers.json
```

Two sub-phases are deliberately separated so a developer can **verify Claude's
understanding (the thought file) before any code is generated**. A misread formula
is cheap to fix in a thought file and expensive to debug in generated HTML.

## A report is a *bundle*, not just a `.rdl`

In a real .NET reporting app (e.g. `DotNetApp/PatientReports/`), an `.rdl`/`.rdlc` is
often **skeletal** — just a Tablix with hard-coded header labels and no dataset, fields,
query, or parameters. **The report's real logic lives in .NET code.** Treat each report as
a bundle of correlated sources and read all that exist:

| Concern | Where it actually lives | Example |
|---|---|---|
| Query / filters / joins / ordering | **Data service** (EF Core LINQ, ADO, Dapper) | `DataServices/PatientDataService.cs` |
| Derived / formatted fields | Data service projection | `PatientName = FirstName + " " + LastName`; `IsInpatient ? "Yes" : "No"` |
| Row shape & column set | **ViewModel** returned to the view | `Models/*ReportViewModel.cs` |
| DB schema, keys, relationships | **EF entities + DbContext** | `Models/Patient.cs`, `Data/ApplicationDbContext.cs` |
| Layout, headers, formatting, summaries | **Razor view** (and/or `.rdl`) | `Views/Reports/*.cshtml` |
| Report wiring (name → data → view) | **Controller action** | `Controllers/ReportsController.cs` |
| Legacy layout hints only | `.rdl` / `.rdlc` (may be near-empty) | `Reports/*.rdl` |

The `.rdl` is a **secondary** input here — use it for layout/title hints. The **ViewModel +
data service** are the source of truth for fields and business logic.

## When to use which sub-phase

| User intent | Sub-phase | Agent | Output |
|---|---|---|---|
| "Understand / analyze this report", "what does X.rdl do" | 1a Research | `report-researcher` | `ReportThoughts/{name}.thought.md` |
| "Generate the HTML report", "migrate the thought files" | 1b Migration | `report-migrator` | `HTMLReportsFolder/{name}.{html,js,md}` |
| "Build the schema mapping / PHI markers" | 1c Schema | `schema-mapper` | `DataSchemaMapping/*.json` |
| "Migrate report X end-to-end" | 1a → 1b | both, in sequence | thought file, then HTML set |

## How to run it

Always go **research → review → migrate**. Do not skip straight to HTML.

0. **Discover the report bundle.** For a .NET app, start from the controller
   (`Controllers/*ReportsController.cs`): each action is one report. Trace it to its data
   service method, the ViewModel it returns, the Razor view, the EF entities/DbContext it
   touches, and any matching `.rdl`. Collect these paths per report before researching.
1. **Research.** For each report, delegate to the `report-researcher` agent (Agent tool,
   `subagent_type: report-researcher`), one agent per report so they run in parallel.
   Give it the **full bundle of file paths** (controller action, data service, ViewModel,
   EF models, DbContext, Razor view, `.rdl`) and the target `ReportThoughts/` directory.
   It writes `{report_name}.thought.md`.
2. **Pause for review.** Present the thought file(s) to the user and ask them to confirm
   the extracted logic before generating code. This checkpoint is the whole point of the
   two-phase split — do not silently proceed to migration.
3. **Migrate.** Once thought files are approved, delegate to `report-migrator`
   (`subagent_type: report-migrator`), one per thought file. It writes the `.html`, `.js`,
   and `.md` set into `HTMLReportsFolder/`.
4. **Schema (independent).** Delegate to `schema-mapper` to produce
   `schema-mapping.json` and `phi-markers.json`. This can run any time; it does not
   depend on the reports.

Naming: derive a `snake_case` report key from the report name (e.g.
`GenericTransplantListReport.rdl` → `generic_transplant_list`). Use the **same key**
across all artifacts for a report so Phase 2 can correlate them.

## Conventions (must hold across all artifacts)

- **One key per report**, `snake_case`, reused for the thought file, HTML/JS/md files,
  and the `report` field Phase 2 routes to.
- **Thought files are the source of truth** for business logic. If migration reveals a
  gap, fix the thought file and re-run migration — never encode logic only in HTML.
- **No live DB calls in Phase 1.** These templates are populated by .NET at runtime with
  a `data` object + `narrative` string. Generated JS must render from an injected data
  contract, never fetch.
- **PHI is marked, never invented.** Only flag a column as PHI when the schema/name makes
  it clearly identifying. When unsure, flag it `true` and note the uncertainty — the
  anonymizer errs safe.

## Reference material

- [references/thought-file-template.md](references/thought-file-template.md) — canonical
  thought-file structure with a worked example.
- [references/html-report-template.md](references/html-report-template.md) — the HTML+JS
  data-binding contract the migrator must follow.
- [references/schema-mapping-example.md](references/schema-mapping-example.md) — shape of
  `schema-mapping.json` and `phi-markers.json`.
