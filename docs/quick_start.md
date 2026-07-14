# Quick Start

Get the AI Report Forge PoC running in under 5 minutes.

## Prerequisites

- .NET 8 SDK
- Python 3.11+
- Ollama installed with the `qwen2.5:3b` model pulled
- Optional: an Anthropic API key (enables the **Ask Claude** button and the
  automatic Claude fallback)

If you don't have the model yet:

```bash
ollama pull qwen2.5:3b
```

## Install (one-time)

```bash
# Python dependencies
cd ai-report-forge
pip install -r requirements.txt
cp .env.example .env        # add ANTHROPIC_API_KEY here if you have one
cd ..

# .NET dependencies
cd DotNetApp/PatientReports
dotnet restore
cd ../..
```

## Start (3 terminals, 4 for the Classic/SSRS path)

**Terminal 1 — Ollama:**
```bash
ollama serve
```

**Terminal 2 — Brain service:**
```bash
cd ai-report-forge
python -m uvicorn ai_report_forge.api:app --host 127.0.0.1 --port 8080
```

Wait for: `Ready -- 3 reports, 7 schema tables, 13 PHI markers`

**Terminal 3 — .NET app:**
```bash
cd DotNetApp/PatientReports
dotnet run
```

Wait for: `Now listening on: http://localhost:5282`

**Terminal 4 (optional) — RDL render service**, only needed for the
**Classic Reports (SSRS)** page and PDF downloads:
```bash
cd DotNetApp/RdlRenderService
dotnet run          # http://localhost:5250
```

## Use

Open **http://localhost:5282** — the app lands on the AI Reports page.

**Ask a question** with either button:

- **Ask Local AI** — decoded by Ollama on your machine; falls back to Claude
  automatically if the local model fails (and a key is configured).
- **Ask Claude** — decoded directly by the Claude API.

A banner under the buttons always shows which model answered
(*Local LLM*, *Claude*, or *Claude (fallback)*).

Try:
- "Give me patient data for Austin General"
- "Show me patients named Ethan"
- "Show transplant events"

**Or select a report from the dropdown:** Patient Report, Transplant Event
Report, Patient Clinical Summary.

Use the navbar to switch to **Classic Reports (SSRS)** — the same reports
rendered from the real `.rdl` files (requires Terminal 4) — or to the
**Prompt Log**, which shows what was actually sent to each LLM for your
recent questions: the original data side-by-side with the anonymized version
the model received (the PHI-protection demo, live).

## Stop

`Ctrl+C` in each terminal.

## Verify services

| Service | Health check |
|---|---|
| Ollama | `curl http://localhost:11434/api/tags` |
| Brain | `curl http://127.0.0.1:8080/health` |
| .NET App | `curl http://localhost:5282` |
| RDL service | `curl http://localhost:5250` |

## Common issues

**Port 8000 blocked:** Use port 8080 (already configured as default).

**Ask Claude shows "Claude is not configured":** Set `ANTHROPIC_API_KEY` in
`ai-report-forge/.env` and **restart the brain** (the key is read at startup).

**Ask Claude shows a Claude API error:** The banner shows the API's own reason —
usually an invalid key or no credit balance on the Anthropic Console account.

**Brain returns no filters:** Restart the brain service after generating
schema-mapping.json. Check `curl http://127.0.0.1:8080/health` shows `schema_tables: 7`.

**Slow responses:** Ollama runs on CPU. Close other apps to free RAM. Expect
5–15 seconds per query on a laptop. Ask Claude is usually faster than the local model.

**Classic report shows "SSRS report could not be rendered":** Start the
RdlRenderService (Terminal 4).

**HTMLReportsFolder not found:** Run the .NET app from `DotNetApp/PatientReports/`
(the relative path in `appsettings.json` resolves from there).

## Run tests

```bash
cd ai-report-forge
python -m pytest tests/ -v
# Expected: 53 passed
```

## More detail

- Full runbook: [docs/runbook-ai-report-forge-poc.md](runbook-ai-report-forge-poc.md)
- NLP query reference: [docs/NLP-Query-Reference.md](NLP-Query-Reference.md)
