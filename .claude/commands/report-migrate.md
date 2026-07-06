---
description: Phase 1b — generate static HTML+JS+md reports from approved thought files
argument-hint: [thought file path or glob; default all in ReportThoughts/]
---

Run Report Forge Phase 1b (Migration) on: **$ARGUMENTS**
(If no argument is given, target all `ReportThoughts/*.thought.md`.)

Load the `report-forge` skill for conventions, then:

1. Resolve the target thought file(s). If a thought file still contains unresolved **Open
   Questions**, flag it and ask the user to confirm before migrating that one.
2. For each thought file, launch a `report-migrator` agent (Agent tool,
   `subagent_type: report-migrator`) — in parallel, one per file. Pass the absolute path
   to the thought file and to the `HTMLReportsFolder/` output directory (create if
   missing).
3. Summarize the generated `{html, js, md}` set per report and note any ambiguities the
   migrators flagged instead of implementing.
