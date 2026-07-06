---
description: Phase 1c — build schema-mapping.json and phi-markers.json for Phase 2
argument-hint: [optional path to DDL/model source]
---

Run Report Forge Phase 1c (Schema Mapping) using source: **$ARGUMENTS**
(If no source is given, build from any SQL DDL in the repo and the field lists in
`ReportThoughts/*.thought.md`. Do NOT connect to a live database unless the user provides
a connection string and explicitly asks for introspection.)

Load the `report-forge` skill, then launch a `schema-mapper` agent (Agent tool,
`subagent_type: schema-mapper`). Pass it the source path(s) and the `DataSchemaMapping/`
output directory (create if missing). Report back the number of tables and PHI columns,
plus any inferences or schema gaps for the user to review.
