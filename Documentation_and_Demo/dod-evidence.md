# Definition-of-Done Evidence — AI Report Forge

**Use case:** #1 — AI-Driven Reporting (assigned use-case DoD from the project plan,
`.claude/plan/ai-driven-reporting-poc.md` → Use Case Summary)
**Evidence gathered:** 2026-07-14, on the development machine (all four services running)

Status legend: ✅ met · ⚠️ partially met (honest deviation stated) · each row lists where a judge can verify it.

## Phase 1 — Report migration pipeline

| # | DoD item | Status | Evidence |
|---|---|---|---|
| 1.1 | Existing report → thought file → HTML report pipeline demonstrated | ✅ | Pipeline artifacts per report: `Reports/*.rdl` (source) → `ReportThoughts/*.thought.md` (reviewable analysis) → `HTMLReportsFolder/*.html + .js + .md` (generated output). Plugin implementation in `.claude/` (agents `report-researcher`, `report-migrator`, `schema-mapper`; skill `report-forge`; commands `/report-research`, `/report-migrate`, `/report-schema`) |
| 1.2 | …for **5 reports** | ⚠️ | **3 reports migrated**: patient, transplant_event, patient_clinical_summary — the third being a deliberately complex multi-table report (facility grouping, BMI/risk computation, lab flags) chosen to prove depth over count. The pipeline is report-agnostic; adding reports 4–5 is a re-run of `/report-research` + `/report-migrate`, no new engineering |
| 1.3 | Developer review checkpoint before code generation | ✅ | Thought files are the human-in-the-loop gate — see `ReportThoughts/README.md` ("Review these before migrating") and any `*.thought.md` |

## Phase 2 — Runtime natural-language reporting

| # | DoD item | Status | Evidence |
|---|---|---|---|
| 2.1 | User submits plain-English question, receives formatted HTML report | ✅ | Live: http://localhost:5282 → type "Show me patients at Austin General" → **Ask Local AI**. Filter badges + filtered table + AI Summary render. Query reference with expected row counts per question: `docs/NLP-Query-Reference.md` |
| 2.2 | Local LLM decodes prompt **within 10s** | ✅ | Measured 2026-07-14: **3.4s** ("show patients named Ethan"), **3.8s** ("show male patients from Dallas") via `POST /decode-prompt`, qwen2.5:3b on CPU. Direct Claude decode: **2.2s**. Note: CPU-bound — first query after model load is slower; the demo pipeline pre-warms |
| 2.3 | .NET API returns data **within 5s** | ✅ | Measured 2026-07-14: full data-fetch + template render round trip **<1s** (`GET /Reports/HtmlReport?report=patient`). SQLite is local and seeded with the synthetic dataset |
| 2.4 | Claude fallback triggers automatically on failure, with anonymized data | ✅ | Verified 2026-07-14: colloquial prompt ("which sheet lists the folks who got cells from a donor other than themselves") failed on the local model and was rescued by Claude — UI shows the amber **Claude (fallback)** banner; Prompt Log records `Local LLM ✗ → Claude — fallback ✓`. Summarization fallback sends **anonymized rows only** (see `presentation/compliance-note.md` and the live **Prompt Log** page). Also verified: Ollama stopped entirely → fallback fires on any question |
| 2.5 | New reports deployable by adding thought files + HTML templates without app rebuild | ⚠️ | **Templates are hot-swappable** — the .NET app reads `HTMLReportsFolder/` from disk per request (no compile-time embedding), and the brain loads thought files at startup; editing an existing report's template requires no rebuild. **Registering a brand-new report key** currently requires a small .NET change (dropdown registry + report-key mapping) — a known limitation; making the registry data-driven is listed as future work |

## Standard deliverables (submission-pack checklist)

| Deliverable | Location |
|---|---|
| Source code, prompts, agent config, tools | This repo — `.claude/` (agent/skill/command definitions), `ai-report-forge/` (runtime LLM prompts in `prompt_decoder.py`, `summarizer.py`, `claude_fallback.py`), `DotNetApp/` |
| README run document | `README.md`, `docs/quick_start.md`, `docs/runbook-ai-report-forge-poc.md` (troubleshooting included) |
| Sample data pack | Synthetic SQLite dataset, auto-seeded on app startup — **no real PHI anywhere in the repo**. Data dictionary: `docs/NLP-Query-Reference.md` → Seed Data Reference |
| Sample inputs | Verified natural-language questions with expected results: `docs/NLP-Query-Reference.md` |
| Generated outputs | `ReportThoughts/`, `HTMLReportsFolder/`, `DataSchemaMapping/` (Phase 1); live reports at runtime (Phase 2) |
| Demo script / video | `presentation/demo-script.md` (narrative); automated recording pipeline plan: `docs/demo-recording-plan.md` |
| Compliance note | `presentation/compliance-note.md` |
| Tests | `cd ai-report-forge && python -m pytest tests/ -v` → **53 passed** (anonymizer, PHI pipeline, decoder guardrails, API, stats) |

## Known deviations, summarized for judging

1. **3 of 5 reports migrated** — depth over count; the pipeline itself is the deliverable and is report-agnostic.
2. **New-report registration touches .NET code** — templates/thought files are data, the report registry is not (yet).
3. Timing figures are from the machine above; CPU-only local inference is hardware-sensitive (the runbook documents lighter-model options).
