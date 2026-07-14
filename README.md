# AI Report Forge

A proof-of-concept platform that replaces SSRS/Crystal Reports with AI-driven reporting. Business users type natural language questions (e.g., "Show me patients named Ethan") and receive formatted HTML reports with AI-generated summaries and charts.

## Architecture

| Layer | Technology |
|---|---|
| Web app | ASP.NET Core MVC (.NET 8), SQLite via EF Core |
| AI brain service | Python 3.11+, FastAPI, Uvicorn |
| Local LLM | Ollama with `qwen2.5:3b` |
| Cloud LLM fallback | Anthropic Claude API (anonymized PHI only) |
| Report templates | Static HTML + vanilla JS (generated from legacy SSRS .rdl files) |

## Quick Start

See [docs/quick_start.md](docs/quick_start.md) for setup and run instructions.

## Documentation

| Document | Description |
|---|---|
| [Quick Start](docs/quick_start.md) | 5-minute setup guide |
| [Runbook](docs/runbook-ai-report-forge-poc.md) | Full PoC runbook with architecture diagrams, demo scenarios, and troubleshooting |
| [NLP Query Reference](docs/NLP-Query-Reference.md) | Complete list of supported natural language queries with expected results |

## Safety & Robustness

- **PHI never leaves the server in the clear** — rows and the question itself are anonymized (pseudonyms / redaction / age ranges) before any LLM call; real names are re-mapped locally afterwards. The brain refuses to start without its PHI markers.
- **Filters can't be forged** — the query spec travels as a signed+encrypted parameter, and only allowlisted columns per table are filterable (PHI contact fields are blocked).
- **Small-model guardrails** — deterministic post-decode corrections fix known LLM mistakes (inverted gender filters, city-vs-facility confusion); off-topic or destructive questions fail closed.
- **Honest failures** — if both LLMs fail, the API returns an error instead of a fabricated summary; LLM chart output is validated before rendering.

## How It Works

1. **Phase 1 (Build-time):** Claude Code analyzes legacy `.rdl` reports, produces reviewable thought files, and generates static HTML+JS report templates and database schema mappings.
2. **Phase 2 (Runtime):** The .NET app serves the UI. The Python brain service decodes natural language prompts into structured queries via a local LLM. Data is fetched from SQLite, rendered in the HTML template, and accompanied by an AI summary with an optional chart.

## Repository Layout

```
DotNetApp/PatientReports/    .NET 8 MVC app (user-facing)
ai-report-forge/             Python brain service (FastAPI)
HTMLReportsFolder/            Generated HTML+JS report templates
ReportThoughts/              Analyzed business logic per report
DataSchemaMapping/            Schema map + PHI markers
docs/                        Documentation
```
