# AI Report Forge

A proof-of-concept platform that replaces SSRS/Crystal Reports with AI-driven reporting.
Business users type natural-language questions (e.g. *"Show me patients named Ethan"*) or
pick a report from a dropdown, and receive a formatted report — with an AI-generated
narrative summary and optional chart — that reads from the live database.

The same reports render **two ways** from one .NET data layer:
- **HTML templates** (the SSRS-replacement path) — static, self-contained HTML+JS
  generated from the legacy reports and populated at runtime with live data.
- **Real SSRS `.rdl`** — rendered to PDF via a ReportViewer side-service, for parity with
  the legacy output. Every report also has a **Download PDF** button.

## Architecture

| Layer | Technology |
|---|---|
| Web app (user-facing) | ASP.NET Core MVC (.NET 8), SQLite via EF Core |
| SSRS/RDL renderer | `RdlRenderService` — .NET Framework 4.8 + Microsoft ReportViewer (`LocalReport`), called over HTTP |
| PDF export | PDFsharp / MigraDoc (MIT) |
| AI brain service | Python 3.11+, FastAPI, Uvicorn |
| Local LLM | Ollama with `qwen2.5:3b` |
| Cloud LLM fallback | Anthropic Claude API (anonymized PHI only) |
| Report templates | Static HTML + vanilla JS (generated from legacy SSRS `.rdl` files) |
| Phase-1 tooling | Claude Code plugin (`.claude/` — skills, agents, commands) |

## How It Works

**Phase 1 — Build-time (Claude Code plugin).** The `report-forge` plugin analyzes legacy
`.rdl` reports, produces reviewable **thought files** (business-logic analysis), then
generates static **HTML+JS templates**, plus a database **schema mapping** and **PHI
markers**. A developer reviews the thought file before any code is generated.

**Phase 2 — Runtime.** The .NET app serves the UI and owns all data access. A user asks a
question; the Python **brain** decodes it (via the local LLM, using the schema mapping)
into a structured query spec — the report key plus table-qualified filters. The .NET app
applies those filters with EF Core against SQLite, injects the rows into the HTML template
(`window.REPORT_DATA`), and the brain adds an anonymized narrative summary (and optional
chart). The real `.rdl` can also be rendered to PDF via `RdlRenderService`.

```
Browser ──▶ .NET MVC (:5282) ──▶ Python brain (:8080) ──▶ Ollama (:11434)
                │                     └─ Claude API (anonymized fallback)
                ├──▶ SQLite (EF Core)         data
                ├──▶ HTMLReportsFolder/       HTML templates + REPORT_DATA
                └──▶ RdlRenderService (:5250) real .rdl → PDF
```

## Repository Layout

```
DotNetApp/
  PatientReports/       .NET 8 MVC app (UI, data access, brain client, report serving)
  RdlRenderService/     .NET Framework 4.8 service that renders real .rdl → PDF
ai-report-forge/        Python brain service (FastAPI): decode-prompt + summarize
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

## Running (4 processes)

See **[docs/quick_start.md](docs/quick_start.md)** for the full walkthrough. In short:

```bash
# 1. Ollama (local LLM)
ollama serve                                   # http://localhost:11434

# 2. Python brain  (port 8000 is firewall-blocked on the VDI — use 8080)
cd ai-report-forge
pip install -r requirements.txt && cp .env.example .env
python -m uvicorn ai_report_forge.api:app --host 127.0.0.1 --port 8080

# 3. RDL render service (only needed for the SSRS/PDF path)
cd DotNetApp/RdlRenderService && dotnet run    # http://localhost:5250

# 4. .NET web app
cd DotNetApp/PatientReports && dotnet run       # http://localhost:5282
```

Open **http://localhost:5282/Reports/HtmlReports** and ask a question, or pick a report.
The app runs without the brain (dropdown reports still work); the "Ask" box just shows a
message until the brain is up. Set `ANTHROPIC_API_KEY` in `ai-report-forge/.env` to enable
the Claude fallback demo.

## Tests

```bash
cd ai-report-forge && python -m pytest tests/ -v   # brain unit tests (no services needed)
```

## Safety & Robustness

- **PHI never leaves the server in the clear** — rows and the question itself are anonymized
  (pseudonyms / redaction / age ranges) before any LLM call; real names are re-mapped
  locally afterwards. The brain refuses to start without its PHI markers.
- **Filters can't be forged** — the query spec travels as a signed+encrypted parameter, and
  only allowlisted columns per table are filterable (PHI contact fields are blocked).
- **Small-model guardrails** — deterministic post-decode corrections fix known LLM mistakes
  (inverted gender filters, city-vs-facility confusion); off-topic or destructive questions
  fail closed.
- **Honest failures** — if both LLMs fail, the API returns an error instead of a fabricated
  summary; LLM chart output is validated before rendering.

## Documentation

| Document | Description |
|---|---|
| [Quick Start](docs/quick_start.md) | Setup and run guide |
| [Runbook](docs/runbook-ai-report-forge-poc.md) | Full PoC runbook: architecture, demo scenarios, troubleshooting |
| [NLP Query Reference](docs/NLP-Query-Reference.md) | Supported natural-language queries with expected results |
| [Architecture & design](.claude/plan/ai-driven-reporting-poc.md) | Original two-phase design doc |
```
