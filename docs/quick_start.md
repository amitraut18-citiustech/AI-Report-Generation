# Quick Start

Get the AI Report Forge PoC running in under 5 minutes.

## Prerequisites

- .NET 8 SDK
- Python 3.11+
- Ollama installed with `qwen2.5:3b` model pulled

If you don't have the model yet:

```bash
ollama pull qwen2.5:3b
```

## Install (one-time)

```bash
# Python dependencies
cd ai-report-forge
pip install -r requirements.txt
cd ..

# .NET dependencies
cd DotNetApp/PatientReports
dotnet restore
cd ../..
```

## Start (3 terminals)

**Terminal 1 -- Ollama:**
```bash
ollama serve
```

**Terminal 2 -- Brain service:**
```bash
cd ai-report-forge
python -m uvicorn ai_report_forge.api:app --host 127.0.0.1 --port 8080
```

Wait for: `Ready -- 3 reports, 7 schema tables, 13 PHI markers`

**Terminal 3 -- .NET app:**
```bash
cd DotNetApp/PatientReports
dotnet run
```

Wait for: `Now listening on: http://localhost:5282`

## Use

Open http://localhost:5282/Reports/HtmlReports

**Ask a question:**
- "Give me patient data for Austin General"
- "Show me patients named Ethan"
- "Show transplant events"

**Or select a report from the dropdown:**
- Patient Report
- Transplant Event Report
- Patient Clinical Summary

## Stop

`Ctrl+C` in each terminal.

## Verify services

| Service | Health check |
|---|---|
| Ollama | `curl http://localhost:11434/api/tags` |
| Brain | `curl http://127.0.0.1:8080/health` |
| .NET App | `curl http://localhost:5282` |

## Common issues

**Port 8000 blocked:** Use port 8080 (already configured as default).

**Brain returns no filters:** Restart the brain service after generating schema-mapping.json. Check `curl http://127.0.0.1:8080/health` shows `schema_tables: 7`.

**Slow responses:** Ollama runs on CPU. Close other apps to free RAM. Expect 5-15 seconds per query on a laptop.

**HTMLReportsFolder not found:** Run the .NET app from `DotNetApp/PatientReports/` (the relative path in `appsettings.json` resolves from there).

## Run tests

```bash
cd ai-report-forge
python -m pytest tests/ -v
# Expected: 44 passed
```

## More detail

- Full runbook: [docs/runbook-ai-report-forge-poc.md](runbook-ai-report-forge-poc.md)
- NLP query reference: [docs/NLP-Query-Reference.md](NLP-Query-Reference.md)
