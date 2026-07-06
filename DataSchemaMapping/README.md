# DataSchemaMapping (Phase 1c output)

Database context for the Phase 2 Python brain, produced by the `schema-mapper` agent
(`/report-schema`):

- `schema-mapping.json` — tables/columns/types/relationships with business descriptions
  and `reportable` flags; used to decode NL prompts into report keys + parameters.
- `phi-markers.json` — PHI columns and anonymization strategies; used to strip PHI before
  any cloud (Claude) LLM call.

Format: [`.claude/skills/report-forge/references/schema-mapping-example.md`](../.claude/skills/report-forge/references/schema-mapping-example.md)
