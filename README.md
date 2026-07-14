# AI Report Forge

A proof-of-concept platform that replaces SSRS/Crystal Reports with AI-driven reporting.
Business users type natural-language questions (e.g. *"Show me patients named Ethan"*) or
pick a report from a dropdown, and receive a formatted report — with an AI-generated
narrative summary — that reads from the live database.

The same reports render **two ways** from one .NET data layer:

- **AI Reports** (the SSRS-replacement path) — static, self-contained HTML+JS templates
  generated from the legacy reports and populated at runtime with live data.
- **Classic Reports** — the real SSRS `.rdl` files rendered via a ReportViewer
  side-service, for parity with the legacy output. Every report also has a
  **Download PDF** button.

## Architecture

| Layer | Technology |
|---|---|
| Web app (user-facing) | ASP.NET Core MVC (.NET 8), SQLite via EF Core |
| SSRS/RDL renderer | `RdlRenderService` — .NET Framework 4.8 + Microsoft ReportViewer (`LocalReport`), called over HTTP |
| PDF export | PDFsharp / MigraDoc (MIT) |
| AI brain service | Python 3.11+, FastAPI, Uvicorn |
| Local LLM | Ollama with `qwen2.5:3b` (or larger) |
| Cloud LLM | Anthropic Claude API — explicit "Ask Claude" button, plus automatic fallback when the local model fails |
| Report templates | Static HTML + vanilla JS (generated from legacy SSRS `.rdl` files) |
| Phase-1 tooling | Claude Code plugin (`.claude/` — skills, agents, commands) |

## How It Works

**Phase 1 — Build-time (Claude Code plugin).** The `report-forge` plugin analyzes legacy
`.rdl` reports, produces reviewable **thought files** (business-logic analysis), then
generates static **HTML+JS templates**, plus a database **schema mapping** and **PHI
markers**. A developer reviews the thought file before any code is generated.

**Phase 2 — Runtime.** The .NET app serves the UI and owns all data access. A user asks a
question using one of two buttons:

- **Ask Local AI** — the Python **brain** decodes the question via Ollama (using the
  schema mapping) into a structured query spec: the report key plus table-qualified
  filters. If Ollama fails or is too uncertain, the brain **automatically falls back to
  the Claude API** (when a key is configured).
- **Ask Claude** — the question is decoded directly by the Claude API.

The .NET app applies the decoded filters with EF Core against SQLite, injects the rows
into the HTML template (`window.REPORT_DATA`), and the brain adds an anonymized narrative
summary. A **provenance banner** always shows which model answered: Local LLM, Claude, or
Claude (fallback), and the **Prompt Log** page shows exactly what was sent to each LLM —
original data side-by-side with the anonymized version the model received. The real
`.rdl` can also be rendered via `RdlRenderService`.

> Charts are disabled by default (`ENABLE_CHARTS=false` in the brain's `.env`) — they
> added LLM latency without serving the core SSRS-replacement story. The rendering
> pipeline is intact; flip the flag to bring them back.

```
Browser ──▶ .NET MVC (:5282) ──▶ Python brain (:8080) ──▶ Ollama (:11434)
                │                     └─ Claude API (direct "Ask Claude",
                │                        or automatic fallback)
                ├──▶ SQLite (EF Core)         data
                ├──▶ HTMLReportsFolder/       HTML templates + REPORT_DATA
                └──▶ RdlRenderService (:5250) real .rdl rendering + PDF
```

## Repository Layout

```
DotNetApp/
  PatientReports/       .NET 8 MVC app (UI, data access, brain client, report serving)
  RdlRenderService/     .NET Framework 4.8 service that renders real .rdl
ai-report-forge/        Python brain service (FastAPI): decode-prompt, summarize, prompt-log
HTMLReportsFolder/       Generated HTML+JS report templates (+ .md docs)
ReportThoughts/          Phase-1 analysis per report + _CONTEXT.md (app migration context)
DataSchemaMapping/       schema-mapping.json + phi-markers.json
Reports/                 Legacy SSRS .rdl source files
.claude/                 Phase-1 Claude Code plugin (skills / agents / commands) + plans
docs/                    Quick start, runbook, NLP query reference
```

## Prerequisites

| Component | Version | Notes |
|---|---|---|
| .NET SDK | 8.0 | Main app + RDL service build |
| Python | 3.11+ | Brain service |
| Ollama | latest | `ollama pull qwen2.5:3b` (~2 GB) |
| Database | SQLite | Auto-created and seeded on app startup |
| Anthropic API key | optional | Enables Ask Claude + automatic fallback |

## Running (4 processes)

See **[docs/quick_start.md](docs/quick_start.md)** for the full walkthrough. In short:

```bash
# 1. Ollama (local LLM)
ollama serve                                   # http://localhost:11434

# 2. Python brain  (port 8000 is firewall-blocked on the VDI — use 8080)
cd ai-report-forge
pip install -r requirements.txt && cp .env.example .env
python -m uvicorn ai_report_forge.api:app --host 127.0.0.1 --port 8080

# 3. RDL render service (only needed for the Classic/SSRS path)
cd DotNetApp/RdlRenderService && dotnet run    # http://localhost:5250

# 4. .NET web app
cd DotNetApp/PatientReports && dotnet run       # http://localhost:5282
```

Open **http://localhost:5282** — the app lands on the AI Reports page. Ask a question or
pick a report; the navbar switches between **AI Reports** and **Classic Reports (SSRS)**.

The app runs without the brain (dropdown reports still work); the ask buttons just show a
message until the brain is up. Set `ANTHROPIC_API_KEY` in `ai-report-forge/.env` to enable
the **Ask Claude** button and the automatic fallback (restart the brain after editing).

## Tests

```bash
cd ai-report-forge && python -m pytest tests/ -v   # brain unit tests (no services needed)
# Expected: 53 passed
```

## Safety & Robustness

- **Data rows never leave the server in the clear** — before any LLM summarization call
  (local or cloud), rows are anonymized (pseudonyms / redaction / age ranges) and the
  question is scrubbed of known PHI values; real names are re-mapped locally afterwards.
  The brain refuses to start without its PHI markers.
- **Ask Claude sends the question to the cloud** — decoding inherently transmits the
  question text (filter values like patient names must be extracted from it), but never
  any database rows. The provenance banner makes every cloud interaction visible.
- **Filters can't be forged** — the query spec travels as a signed+encrypted parameter,
  and only allowlisted columns per table are filterable (PHI contact fields are blocked).
- **Small-model guardrails** — deterministic post-decode corrections fix known local-LLM
  mistakes (inverted gender filters, city-vs-facility confusion, hallucinated filters);
  they are not applied to Claude's output. Off-topic questions fail closed as UNKNOWN.
- **Honest failures** — if both LLMs fail, the API returns an error instead of a
  fabricated summary; Claude API errors (billing, auth) surface with their real reason.

## Documentation

| Document | Description |
|---|---|
| [Architecture](docs/architecture.md) | How the system works — components, request flow, PHI protection, trust boundaries, with diagrams |
| [Quick Start](docs/quick_start.md) | Setup and run guide |
| [Runbook](docs/runbook-ai-report-forge-poc.md) | Full PoC runbook: architecture, demo scenarios, troubleshooting |
| [NLP Query Reference](docs/NLP-Query-Reference.md) | Supported natural-language queries with expected results |
| [Architecture & design](.claude/plan/ai-driven-reporting-poc.md) | Original two-phase design doc |
