# AI Report Forge — Project Context

## What This Is

PoC replacing SSRS/Crystal Reports with AI-driven reporting. Two runtime services:
- **.NET 8 MVC app** (`DotNetApp/PatientReports/`) — serves UI, queries SQLite, renders HTML reports
- **Python FastAPI brain** (`ai-report-forge/`) — decodes NL prompts via Ollama, summarizes results

## Key Directories

- `HTMLReportsFolder/` — generated HTML+JS templates (patient, transplant_event, patient_clinical_summary)
- `ReportThoughts/` — Phase 1a thought files (business logic analysis)
- `DataSchemaMapping/` — schema-mapping.json + phi-markers.json
- `docs/` — runbook, quick start, NLP query reference

## Running

```bash
# Terminal 1: ollama serve
# Terminal 2: cd ai-report-forge && python -m uvicorn ai_report_forge.api:app --host 127.0.0.1 --port 8080
# Terminal 3: cd DotNetApp/PatientReports && dotnet run
# Open: http://localhost:5282/Reports/HtmlReports
```

## Tests

```bash
cd ai-report-forge && python -m pytest tests/ -v
# Expected: 44 passed
```

## Key Conventions

- NLP filters are AND-only (no OR support)
- Filter values are always strings (Pydantic coerces non-strings)
- PHI is anonymized before any LLM call (Ollama and Claude); column matching is
  case-insensitive (the .NET client sends camelCase keys) with a deny-by-default
  net for unconfigured identifier-like columns; the user's question is scrubbed too
- The brain refuses to start if schema-mapping.json or phi-markers.json is missing/empty
- The QuerySpec travels browser-side as a signed+encrypted (Data Protection) `spec` param
- ReportQueryService enforces a per-table filterable-field allowlist (PHI columns blocked)
- The clinical report applies brain filters in memory via `FilterClinicalRows`
  (flat rows; FirstName/LastName match as substrings of PatientName/ProviderName)
- `prompt_decoder._sanitize_filters` deterministically fixes known small-model
  decode errors (inverted gender notEquals, bare city in Facilities.Name)
- HTML report templates use `window.REPORT_DATA` injected by the .NET controller
- Narrative rendered as structured HTML card ("AI Summary" header + paragraphs)
- Chart.js is vendored at `wwwroot/lib/chartjs` (no CDN); LLM chart specs are validated
- Schema-mapping.json drives LLM context for table-qualified filters
- ReportQueryService supports 1-hop and 2-hop navigation for cross-table filters
