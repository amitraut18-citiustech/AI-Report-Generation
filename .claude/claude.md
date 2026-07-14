# AI Report Forge — Project Context

## What This Is

PoC replacing SSRS/Crystal Reports with AI-driven reporting. Runtime services:
- **.NET 8 MVC app** (`DotNetApp/PatientReports/`) — serves UI, queries SQLite, renders HTML reports
- **Python FastAPI brain** (`ai-report-forge/`) — decodes NL prompts (Ollama or Claude API), summarizes results
- **RdlRenderService** (`DotNetApp/RdlRenderService/`, .NET Framework 4.8, :5250) — renders the real `.rdl` files for the Classic (SSRS) page and PDF download

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
# Terminal 4 (Classic/SSRS path only): cd DotNetApp/RdlRenderService && dotnet run
# Open: http://localhost:5282  (lands on AI Reports; navbar: AI Reports | Classic Reports (SSRS))
```

## Tests

```bash
cd ai-report-forge && python -m pytest tests/ -v
# Expected: 53 passed
```

## Key Conventions

- Two ask buttons: **Ask Local LLM** (Ollama, auto-falls back to Claude on failure/low
  confidence when a key is configured) and **Ask Claude** (direct Claude API decode).
  `/decode-prompt` takes `provider` ("local"|"claude") and returns `source`
  ("ollama"|"claude"|"claude_fallback"); the UI shows a provenance banner per source
- The Claude API key lives in `ai-report-forge/.env` (`ANTHROPIC_API_KEY`), read at
  brain startup — restart the brain after changing it. The .NET app never holds the key
- `FORCE_DECODE_FALLBACK=true` in the brain's `.env` makes every local decode fail so
  the Claude fallback fires deterministically — demo/testing only
- NLP filters are AND-only (no OR support)
- Filter values are always strings (Pydantic coerces non-strings)
- Data rows are anonymized before any summarization LLM call (Ollama and Claude);
  column matching is case-insensitive (the .NET client sends camelCase keys) with a
  deny-by-default net for unconfigured identifier-like columns; the question is scrubbed
  too. Exception: the *decode* step inherently sends the raw question (filter values
  must be extracted from it) — never any rows
- The brain refuses to start if schema-mapping.json or phi-markers.json is missing/empty
- The QuerySpec travels browser-side as a signed+encrypted (Data Protection) `spec` param
- ReportQueryService enforces a per-table filterable-field allowlist (PHI columns blocked)
- The clinical report applies brain filters in memory via `FilterClinicalRows`
  (flat rows; FirstName/LastName match as substrings of PatientName/ProviderName)
- `prompt_decoder._sanitize_filters` deterministically fixes known small-model decode
  errors (inverted gender notEquals, bare city in Facilities.Name) — local model only
- HTML report templates use `window.REPORT_DATA` injected by the .NET controller
- Narrative rendered as structured HTML card ("AI Summary" header + paragraphs)
- Charts are disabled by default (`enable_charts=false` in brain config); the rendering
  pipeline (ChartSpec validation, vendored Chart.js at `wwwroot/lib/chartjs`) is intact —
  set `ENABLE_CHARTS=true` to re-enable
- Schema-mapping.json drives LLM context for table-qualified filters
- ReportQueryService supports 1-hop and 2-hop navigation for cross-table filters
- Classic (SSRS) page has no loading spinner (removed deliberately); the AI page keeps
  its full-screen ask spinner
- **Prompt Log** page (`/Reports/PromptLog`, third navbar entry) shows what was actually
  sent to each LLM — backed by the brain's in-memory `prompt_log.py` (bounded, clears on
  restart) via `GET /prompt-log`; decode/summarize calls record entries at the point of
  scrubbing. Button label in the UI is "Ask Local AI"
