---
description: Phase 1a — analyze legacy report(s) into reviewable thought files
argument-hint: [report path or glob, e.g. Reports/*.rdl]
---

Run Report Forge Phase 1a (Research) on: **$ARGUMENTS**
(If no argument is given, target all reports under `Reports/` — `.rdl` files and any
Crystal `.md` companion docs.)

Load the `report-forge` skill for conventions, then:

1. Resolve the target report file(s). Ignore empty placeholder files.
2. For each report, launch a `report-researcher` agent (Agent tool,
   `subagent_type: report-researcher`) — run them in parallel, one per report. Pass each
   the absolute path to its report and to the `ReportThoughts/` output directory (create
   the directory if missing).
3. When they finish, summarize each thought file and **explicitly surface any Open
   Questions**. Do not proceed to migration — tell the user to review the thought files
   and run `/report-migrate` once approved.
