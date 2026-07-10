---
description: Phase 1a — analyze legacy report(s) into reviewable thought files
argument-hint: [report name, controller, or path; default: discover from the .NET app]
---

Run Report Forge Phase 1a (Research) on: **$ARGUMENTS**
(If no argument is given, discover reports automatically — see step 1.)

Load the `report-forge` skill for conventions, then:

1. **Discover report bundles.** A report is a *bundle* of .NET files, not just an `.rdl`.
   Prefer the .NET app: find the reports controller
   (Grep `Controllers` for `: Controller` in a `*Reports*` file) — each public action is
   one report. Trace each action to its data-service method, the ViewModel it returns, the
   Razor view, the EF entities/`DbContext` it queries, and any matching `Reports/*.rdl`.
   If there is no .NET app, fall back to `Reports/*.rdl` and Crystal `.md` docs. Ignore
   empty placeholder files.
2. For each report, launch a `report-researcher` agent (Agent tool,
   `subagent_type: report-researcher`) — in parallel, one per report. Pass each the
   **full bundle of absolute file paths** (controller action, data service, ViewModel, EF
   models, DbContext, Razor view, `.rdl`) and the `ReportThoughts/` output directory
   (create it if missing).
3. When they finish, summarize each thought file and **explicitly surface any Open
   Questions**. Do not proceed to migration — tell the user to review the thought files
   and run `/report-migrate` once approved.
