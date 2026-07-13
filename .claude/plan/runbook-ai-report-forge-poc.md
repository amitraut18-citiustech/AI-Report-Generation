# Runbook: AI Report Forge — Full PoC / Demo

**Updated:** 2026-07-13

---

## What This PoC Demonstrates

1. **Phase 1 (Build-Time):** Claude Code analyzes legacy SSRS `.rdl` reports → produces reviewable thought files → generates static HTML+JS report replacements
2. **Phase 2 (Runtime):** A .NET MVC app serves reports populated with live data. A Python brain service decodes natural language questions into report keys via a local LLM (Ollama). Claude API is the anonymized-PHI fallback.
3. **End-to-End Flow:** User types a question → Python brain routes it → .NET fetches data → HTML report renders with an LLM-generated narrative summary

---

## System Requirements

| Component | Version | VDI-Verified |
|---|---|---|
| .NET SDK | 8.0 | Yes |
| Python | 3.11+ (3.14 on VDI) | Yes |
| Ollama | latest | Yes |
| LLM Model | qwen2.5:3b (~2 GB RAM) | Yes |
| Node.js | Not required | — |
| Database | SQLite (bundled, no setup) | Yes |

**Hardware note:** VDI is a ThinkPad L14 — i5-1135G7, 16 GB RAM, no GPU. CPU-only inference works but is slow (~5-10 tok/s). Close unnecessary apps to free RAM before running Ollama.

---

## Repository Layout

```
AI-Report-Generation/
├── DotNetApp/PatientReports/      # .NET 8 MVC app (user-facing)
│   ├── Controllers/
│   │   └── ReportsController.cs   # Report hub + HTML report serving
│   ├── DataServices/              # Data access (SQLite), PDF generation
│   ├── Models/                    # Patient, Facility, Encounter, etc.
│   ├── Views/Reports/             # Razor views + HTML report iframe
│   ├── db/PatientDB.db            # SQLite database (seeded with sample data)
│   └── appsettings.json           # Config (DB path, HTMLReportsFolder path)
│
├── Reports/                       # Legacy SSRS source .rdl files
│   ├── GenericTransplantListReport.rdl
│   ├── GenericRetransplantationReport.rdl
│   └── AI-report.rdlc
│
├── ReportThoughts/                # Phase 1a output: analyzed business logic
│   ├── blood_type_distribution.thought.md
│   ├── patient.thought.md
│   ├── patient_clinical_summary.thought.md
│   ├── patient_demographics.thought.md
│   └── transplant_event.thought.md
│
├── HTMLReportsFolder/             # Phase 1b output: static HTML+JS reports
│   ├── patient.html / .js / .md
│   ├── patient_clinical_summary.html / .js / .md
│   └── transplant_event.html / .js / .md
│
├── DataSchemaMapping/             # Phase 1c output: schema + PHI markers
│   ├── schema-mapping.json
│   └── phi-markers.json
│
├── ai-report-forge/               # Phase 2: Python brain service
│   ├── ai_report_forge/           # FastAPI app (7 modules)
│   ├── tests/                     # 24 unit/integration tests
│   ├── requirements.txt
│   └── .env.example
│
└── .claude/                       # Claude Code plugin (Phase 1 tooling)
    ├── agents/                    # report-researcher, report-migrator, schema-mapper
    ├── commands/                  # /report-research, /report-migrate, /report-schema
    ├── skills/report-forge/       # Orchestration skill + reference templates
    └── plan/                      # Architecture doc, plans, this runbook
```

---

## One-Time Setup

### 1. Ollama + LLM

```bash
# Install Ollama (if not done): https://ollama.com/download
ollama pull qwen2.5:3b
ollama list                  # verify model appears
```

### 2. Python Brain Service

```bash
cd ai-report-forge
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY if Claude fallback demo is needed
```

### 3. .NET App

```bash
cd DotNetApp/PatientReports
dotnet restore
dotnet build
```

No database setup needed — SQLite DB (`db/PatientDB.db`) is bundled with seeded sample data.

---

## Starting the PoC (3 Services)

Start these in order, each in its own terminal:

### Terminal 1: Ollama

```bash
ollama serve
```

Runs on `http://localhost:11434`. Verify: `curl http://localhost:11434/api/tags`

### Terminal 2: Python Brain Service

```bash
cd ai-report-forge
python -m uvicorn ai_report_forge.api:app --host 127.0.0.1 --port 8080 --reload
```

**Expected output:**
```
Loaded report thought: blood_type_distribution
Loaded report thought: patient_demographics
...
Ready — 5 reports, 4 schema tables, 8 PHI markers
Uvicorn running on http://127.0.0.1:8080
```

Verify: `curl http://127.0.0.1:8080/health`

**Note:** Port 8000 is blocked by VDI corporate firewall. Use 8080 or 8081.

### Terminal 3: .NET App

```bash
cd DotNetApp/PatientReports
dotnet run
```

**Expected output:**
```
Now listening on: http://localhost:5282
```

Open browser: **http://localhost:5282**

---

## Stopping the PoC

1. `Ctrl+C` in each terminal (Ollama, Python, .NET)
2. If a port is stuck:
   ```bash
   netstat -ano | grep <port>
   taskkill /PID <pid> /F
   ```

---

## Demo Scenarios

### Demo 1: Phase 1 — Report Migration Pipeline (Claude Code)

**Story:** Show how an SSRS report gets replaced by a static HTML report without manual coding.

**Steps:**
1. Show a legacy `.rdl` file: `Reports/GenericTransplantListReport.rdl`
2. Show the thought file Claude Code produced: `ReportThoughts/transplant_event.thought.md`
   - Point out: data fields, business logic, parameters, layout — all extracted automatically
3. Show the generated HTML report: `HTMLReportsFolder/transplant_event.html`
   - Open it directly in a browser — it renders with an empty-data placeholder
4. Show the .NET app serving it with live data: http://localhost:5282/Reports/HtmlReports?report=transplant

**Key message:** Developer reviews the thought file (catches errors early), then HTML is auto-generated. No SSRS, no report server, no RDL authoring.

### Demo 2: .NET App — Report Hub (Existing Reports)

**Story:** The existing .NET app already serves reports — both Razor-rendered and HTML-template-based.

**Steps:**
1. Open http://localhost:5282/Reports
2. Select "Patient Report" → Generate Report → see Razor-rendered table
3. Click "Download PDF" → PDF generated via PDFsharp/MigraDoc
4. Navigate to http://localhost:5282/Reports/HtmlReports
5. Select "Patient Report" → Generate HTML Report → see the Phase 1-generated HTML template populated with live data from SQLite
6. Click "Open in new tab" → standalone self-contained HTML report

**Available reports:**

| Dropdown value | Razor report | HTML report |
|---|---|---|
| Patient Report | Yes | Yes (`patient.html`) |
| Transplant Event | Yes | Yes (`transplant_event.html`) |
| Clinical Summary | Yes | Yes (`patient_clinical_summary.html`) |

### Demo 3: Python Brain — Prompt Decoding (Ollama)

**Story:** A natural language question gets classified into the correct report + parameters by the local LLM.

**Steps:**
```bash
# Blood type question → routes to blood_type_distribution
curl -X POST http://127.0.0.1:8080/decode-prompt \
  -H "Content-Type: application/json" \
  -d '{"question": "Show me patients by blood type"}'

# Demographics question → routes to patient_demographics
curl -X POST http://127.0.0.1:8080/decode-prompt \
  -H "Content-Type: application/json" \
  -d '{"question": "Show me patient demographics by age and gender"}'

# Transplant question → routes to transplant_event
curl -X POST http://127.0.0.1:8080/decode-prompt \
  -H "Content-Type: application/json" \
  -d '{"question": "What transplant events happened this year?"}'

# Unknown question → returns UNKNOWN
curl -X POST http://127.0.0.1:8080/decode-prompt \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the weather today?"}'
```

**Key message:** The LLM replaces the SSRS parameter form. Users type questions instead of selecting dropdowns.

### Demo 4: Python Brain — Result Summarization (Ollama)

**Story:** Raw query results get summarized into a human-readable narrative.

**Steps:**
```bash
curl -X POST http://127.0.0.1:8080/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How many patients do we have by blood type?",
    "results": [
      {"BloodType": "O+", "Count": 142, "Percentage": 29.1},
      {"BloodType": "A+", "Count": 98, "Percentage": 20.1},
      {"BloodType": "B+", "Count": 76, "Percentage": 15.6},
      {"BloodType": "AB-", "Count": 12, "Percentage": 2.5}
    ],
    "row_count": 4
  }'
```

**Key message:** The narrative summary is injected into the HTML report alongside the data table — the user gets both the raw numbers and an executive summary.

### Demo 5: Claude Fallback with PHI Anonymization

**Story:** When the local LLM fails, Claude API is called — but only with anonymized data. PHI never leaves the server.

**Prerequisites:** `ANTHROPIC_API_KEY` configured in `.env`

**Steps:**
1. Stop Ollama: close Terminal 1 (or `taskkill`)
2. Send a summarize request — Ollama fails, Claude fallback triggers:
   ```bash
   curl -X POST http://127.0.0.1:8080/summarize \
     -H "Content-Type: application/json" \
     -d '{
       "question": "Show me patient details",
       "results": [
         {"FirstName": "John", "LastName": "Smith", "MRN": "MRN-001", "BloodType": "O+", "Gender": "Male"},
         {"FirstName": "Jane", "LastName": "Doe", "MRN": "MRN-002", "BloodType": "A+", "Gender": "Female"}
       ],
       "row_count": 2,
       "table": "Patients"
     }'
   ```
3. Response shows `"source": "claude"`, `"anonymized": true`
4. The narrative uses real names (re-mapped locally) — Claude only saw pseudonyms
5. Restart Ollama: `ollama serve`

**Key message:** HIPAA compliance — PHI is anonymized before any cloud API call. The anonymizer uses `phi-markers.json` to know which columns are sensitive.

### Demo 6: Phase 1 Live (Run in Claude Code)

**Story:** Demonstrate the research → migration pipeline live on a new report.

**Steps (in Claude Code):**
1. Run `/report-research Reports/GenericRetransplantationReport.rdl`
2. Review the generated thought file
3. Run `/report-migrate ReportThoughts/generic_retransplantation.thought.md`
4. Open the generated HTML report in a browser

**Key message:** Adding a new report = run two commands + review. No developer coding required.

---

## Verified Endpoints (Tested 2026-07-13)

| Endpoint | URL | Status |
|---|---|---|
| .NET App home | http://localhost:5282 | Working |
| .NET Reports hub | http://localhost:5282/Reports | Working |
| .NET HTML Reports hub | http://localhost:5282/Reports/HtmlReports | Working |
| Brain health | http://127.0.0.1:8080/health | Working |
| Brain decode-prompt | http://127.0.0.1:8080/decode-prompt | Working |
| Brain summarize | http://127.0.0.1:8080/summarize | Working |
| Ollama API | http://localhost:11434/api/tags | Working |

---

## What's Connected vs. Not Yet Connected

| Integration | Status | Notes |
|---|---|---|
| .NET → SQLite (data) | Connected | Seeded sample data, EF Core |
| .NET → HTMLReportsFolder (templates) | Connected | `ReportsController.HtmlReport()` reads and populates templates |
| .NET → PDF generation | Connected | PDFsharp/MigraDoc, download button works |
| Python brain → Ollama (LLM) | Connected | Prompt decoding + summarization verified |
| Python brain → Claude (fallback) | Built, not tested | Needs `ANTHROPIC_API_KEY` in `.env` |
| **.NET → Python brain** | **Not connected** | .NET does not yet call `/decode-prompt` or `/summarize`. Reports are selected via dropdown, not NL prompt. This is the Phase 2b integration step. |

**The gap:** The .NET app currently has a dropdown report selector. The "user types a question" flow requires a new UI + `HttpClient` calls to the Python brain. The brain is ready; the .NET integration is not built yet.

---

## Running Tests

### Python brain tests (no services needed)

```bash
cd ai-report-forge
python -m pytest tests/ -v
# Expected: 24 passed
```

### .NET app

```bash
cd DotNetApp/PatientReports
dotnet build
# No automated tests exist yet
```

---

## Troubleshooting

### Port blocked (8000)

VDI corporate firewall blocks port 8000. Use `127.0.0.1:8080` or `127.0.0.1:8081`.

### Ollama model name mismatch

`/decode-prompt` returns `"Ollama unavailable"` even though `/health` says connected.

**Cause:** `OLLAMA_MODEL` in config doesn't match what's pulled. Config default is `qwen2.5:3b` — verify with `ollama list`.

### .NET can't find HTMLReportsFolder

**Error:** `DirectoryNotFoundException: Could not locate HTMLReportsFolder`

**Cause:** `ReportForge:HtmlReportsPath` in `appsettings.json` is `../../HTMLReportsFolder` (relative to `DotNetApp/PatientReports/`). If you run `dotnet run` from a different directory, the relative path breaks.

**Fix:** Run from `DotNetApp/PatientReports/`, or set an absolute path in `appsettings.json`.

### Slow LLM responses (>30s)

CPU-only inference on 4-core i5 with limited free RAM. Close apps to free memory. If the model is paging to disk, responses will be 10-20x slower.

Consider `gemma2:2b` (~1.7 GB) as a lighter alternative: `ollama pull gemma2:2b`, update `OLLAMA_MODEL` in `.env`.

---

## Architecture Diagram

```
                    ┌────────────────────────────────────────────────┐
                    │              .NET MVC App (:5282)              │
                    │                                                │
   User ──────────▶│  /Reports          → Razor report (dropdown)   │
   (browser)       │  /Reports/HtmlReports → HTML report (iframe)   │
                    │  /Reports/Download → PDF download              │
                    │                                                │
                    │  Future: NL prompt UI ─┐                       │
                    └───────────────────────│───────────────────────┘
                         │                  │               │
                    SQLite DB          POST /decode      POST /summarize
                    (PatientDB.db)     POST /summarize
                                            │
                    ┌───────────────────────▼───────────────────────┐
                    │         Python Brain Service (:8080)           │
                    │                                                │
                    │  Loads at startup:                              │
                    │    ReportThoughts/*.thought.md                  │
                    │    DataSchemaMapping/schema-mapping.json        │
                    │    DataSchemaMapping/phi-markers.json           │
                    │                                                │
                    │  /decode-prompt  → Ollama (qwen2.5:3b)         │
                    │  /summarize     → Ollama → quality check       │
                    │                    fail? → anonymize → Claude  │
                    └───────────────────────────────────────────────┘
                                            │
                    ┌───────────────────────▼───────────────────────┐
                    │           Ollama (:11434)                      │
                    │           qwen2.5:3b (CPU, ~2 GB)             │
                    └───────────────────────────────────────────────┘

PHI boundary: Ollama sees raw data (local). Claude only sees anonymized data.
```
