---
description: Phase 1a — analyze legacy report(s) into reviewable thought files
argument-hint: [report name or path; default: discover from the project]
---

Run Report Forge Phase 1a (Research) on: **$ARGUMENTS**
(If no argument is given, discover reports automatically — see step 1.)

Load the `report-forge` skill for conventions, and read the application migration context
(`ReportThoughts/_CONTEXT.md`, if present) for this project's stack and file map. Then:

1. **Discover report bundles.** A report is a *bundle* (its `.rdl` plus whatever host code
   defines/renders/filters it), not just an `.rdl`. Use the context's report registry/file
   map if present; otherwise discover from the report sources — the `.rdl` files and/or the
   host app's report registry (e.g. its report controller/routes). Ignore empty placeholder
   files.
2. For each report, launch a `report-researcher` agent (Agent tool,
   `subagent_type: report-researcher`) — in parallel, one per report. Pass each the
   **full bundle of absolute file paths** for that report and the `ReportThoughts/` output
   directory (create it if missing).
3. When they finish, summarize each thought file and **explicitly surface any Open
   Questions**. Do not proceed to migration — tell the user to review the thought files
   and run `/report-migrate` once approved.
