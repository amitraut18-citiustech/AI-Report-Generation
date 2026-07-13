---
name: report-forge
description: >-
  Build-time (Phase 1) migration of legacy SSRS/Crystal reports into the AI Report
  Forge platform. Use this when the user wants to analyze existing report definitions
  (.rdl / .rpt docs), produce reviewable "thought files" capturing each report's
  business logic, generate static HTML+JS report templates from those thought files,
  or build the database schema-mapping / PHI-marker artifacts that Phase 2 consumes.
  Triggers on: "migrate reports", "analyze this rdl", "generate thought file",
  "build html report", "report forge", "schema mapping", "phi markers".
---

# Report Forge — Phase 1 (Build-Time Report Migration)

Phase 1 is a **build-time** workflow that runs inside the report project during
development. It replaces the SSRS/Crystal Reports authoring cycle with an AI pipeline
that reads legacy report definitions and emits static, version-controlled artifacts.
Nothing here runs at runtime — the outputs are committed to the repo and later loaded
by the Phase 2 runtime service.

This skill is **host-agnostic**: it works with any SSRS report project. Anything specific
to a particular application — its stack, how reports are hosted/rendered/filtered, where
artifacts live, the report registry — is **not** encoded here. It lives in the project's
**application migration context** (see below) and in the per-report thought files.

> Full architecture and rationale: [../../plan/ai-driven-reporting-poc.md](../../plan/ai-driven-reporting-poc.md)

## Application migration context (read this first)

Before researching or migrating, read the project's migration-context doc if present —
by convention `ReportThoughts/_CONTEXT.md` (fall back to a `_CONTEXT`/`README` in the
thought or HTML folder). It records the host stack, the report-bundle file map, the
rendering & filter model, the runtime data-injection contract, artifact locations, and
the report registry for *this* application. The generic guidance below is applied using
those project specifics. If no context doc exists, infer the specifics from the codebase
and write one.

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

A legacy `.rdl`/`.rdlc` is often **skeletal** — a Tablix with hard-coded header labels and
no dataset, fields, query, or parameters — because the report's real logic lives in the
**host application's code** (data access, projection, rendering, view). Treat each report
as a bundle of correlated sources and read every part that exists. The concerns to find:

- **Report wiring** — where a report name maps to its data + output.
- **Query / joins / ordering / filters** — the data-access layer.
- **Derived / formatted fields** — the projection into the row shape.
- **Row shape & columns** — the view model / DTO the renderer receives.
- **Schema, keys, relationships** — the data model behind the query.
- **Layout / headers / summaries** — the view and/or the `.rdl`.

Which files these correspond to is **application-specific** — see the migration-context
doc (`ReportThoughts/_CONTEXT.md`) for this project's exact file map. Where the `.rdl` is
skeletal, treat it as a layout/title hint and take fields + business logic from the host
code; where the `.rdl` is rich (real dataset, query, `Code`, parameters), treat it as a
primary source too.

## When to use which sub-phase

| User intent | Sub-phase | Agent | Output |
|---|---|---|---|
| "Understand / analyze this report", "what does X.rdl do" | 1a Research | `report-researcher` | `ReportThoughts/{name}.thought.md` |
| "Generate the HTML report", "migrate the thought files" | 1b Migration | `report-migrator` | `HTMLReportsFolder/{name}.{html,js,md}` |
| "Build the schema mapping / PHI markers" | 1c Schema | `schema-mapper` | `DataSchemaMapping/*.json` |
| "Migrate report X end-to-end" | 1a → 1b | both, in sequence | thought file, then HTML set |

## How to run it

Always go **research → review → migrate**. Do not skip straight to HTML.

0. **Discover the report bundle.** Use the migration-context doc's report registry and
   file map, or the report sources directly (the `.rdl` files and/or the host app's report
   registry — e.g. its report controller/routes). Collect the bundle of file paths for
   each report before researching.
1. **Research.** For each report, delegate to the `report-researcher` agent (Agent tool,
   `subagent_type: report-researcher`), one agent per report so they run in parallel.
   Give it the **full bundle of file paths** for that report (its `.rdl` plus whatever host
   code defines/renders/filters it) and the target `ReportThoughts/` directory.
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
- **No live DB calls in Phase 1.** These templates are populated by the host app at runtime
  with a `data` object + `narrative` string. Generated JS must render from an injected data
  contract, never fetch.
- **The host filters; the template never does.** Report parameters are applied by the host
  as data filters, and the *already-filtered* rows are injected. SSRS reports are typically
  rendered from *fed* data (the RDL's SQL `WHERE` does not execute at render time), so
  filtering lives in the host's data layer, not the report. When a report has user filters,
  the generated HTML exposes **interactive filter controls** that round-trip to the host via
  the query string; the JS never re-runs the WHERE. The host endpoint serving a template
  must accept the parameter names as query-string values. (This project's concrete
  rendering/filter mechanics are in the migration-context doc.)
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
