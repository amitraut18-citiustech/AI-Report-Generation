# AI Report Forge — Architecture & Design

**Team:** AI Report Forge  
**Status:** Design  
**Created:** 2026-06-25  
**Updated:** 2026-07-02  
**Author:** Pradyumna Kale  

---

## Problem Statement

SSRS and Crystal Reports require developer involvement for every new report — writing RDL definitions, designing layouts, configuring data sources, deploying to report server. This creates IT backlogs and delays business users from getting the data they need. Reports are static snapshots with limited filter-based dynamism.

**Goal:** Replace SSRS/Crystal Reports for on-demand, read-only, tabular/summary reports with an AI-driven platform where business users type natural language questions and receive formatted reports — reducing developer dependency for routine reporting needs.

---

## What This PoC Replaces (and Does NOT Replace) from SSRS

### In Scope (PoC)

| SSRS Capability | AI Report Forge Equivalent |
|----------------|---------------------------|
| Static tabular reports | LLM-populated HTML/JS templates with data tables |
| Filter-based dynamism (date range, facility, etc.) | Natural language questions replace parameter forms |
| PDF/Excel/CSV export | HTML report rendered in browser (export deferred to post-PoC) |
| Developer-written SQL queries | Existing .NET data access code, driven by LLM-decoded parameters |
| Manual report layout design | Claude Code auto-generates HTML templates from analyzed report logic |
| RDL/Crystal Report maintenance | Static HTML + JS templates in version control |

### Out of Scope (Post-PoC / Future)

| SSRS Capability | Status | Notes |
|----------------|--------|-------|
| Scheduled reports (email PDF every Monday) | Deferred | Requires job scheduler + email integration |
| Parameterized drill-down (click facility → see patients) | Deferred | Requires interactive report navigation |
| Subreports / nested reports | Deferred | Current templates are single-level |
| Row-level security (user A sees Facility 1 only) | Deferred | Requires user-scoped data filtering |
| Report subscriptions | Deferred | Requires notification infrastructure |
| PDF/Excel/CSV export | Deferred | Achievable post-PoC with standard libraries |

---

## Old Flow vs New Flow

```
OLD FLOW (SSRS/Crystal Reports):
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ User UI  │────▶│ .NET     │────▶│  SQL     │────▶│  SSRS    │
│ Input    │     │ Code     │     │ (data    │     │ Report   │
│ (filters)│     │          │     │  fetch)  │     │ (.rdl)   │
└──────────┘     └──────────┘     └──────────┘     └──────────┘

NEW FLOW (AI Report Forge):
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ User     │────▶│ .NET App │────▶│ Python   │────▶│ .NET App │────▶│ Static   │
│ Prompt   │     │ (UI +    │     │ Package  │     │ (data    │     │ HTML     │
│ (NL)     │     │  orchestr│     │ (Llama   │     │  fetch + │     │ Report   │
└──────────┘     │  ation)  │     │  decode) │     │  render) │     └──────────┘
                 └──────────┘     └──────────┘     └──────────┘
                      │                                  ▲
                      │         {report, params}         │
                      └──────────────────────────────────┘
```

**Key insight:** The .NET application remains the user-facing service — one UI, one auth system. It calls the Python package (background service) to decode natural language into structured parameters, then uses its existing data access layer to fetch data and render the HTML report. The LLM replaces the SSRS parameter form, not the .NET stack.

---

## Two-Phase Architecture

The system is split into two distinct phases with different execution contexts and tooling:

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  PHASE 1: Build Time (Claude Code Plugin in .NET Project)        │
│  ────────────────────────────────────────────────────────        │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  RESEARCH PHASE                                          │    │
│  │                                                          │    │
│  │  Existing Reports (.rdl, .rpt docs, .md)                 │    │
│  │       │                                                  │    │
│  │       ▼                                                  │    │
│  │  Claude Code Plugin                                      │    │
│  │       │  Reads each report definition                    │    │
│  │       │  Extracts: tables, joins, formulas,              │    │
│  │       │    grouping, conditional logic,                   │    │
│  │       │    parameters, business rules                     │    │
│  │       ▼                                                  │    │
│  │  ReportThoughts/                                         │    │
│  │       ├── patient_demographics.thought.md                │    │
│  │       ├── blood_type_distribution.thought.md             │    │
│  │       ├── encounter_summary.thought.md                   │    │
│  │       └── ...                                            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                       │                                          │
│                       ▼                                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  MIGRATION PHASE                                         │    │
│  │                                                          │    │
│  │  ReportThoughts/ (all .thought.md files)                 │    │
│  │       │                                                  │    │
│  │       ▼                                                  │    │
│  │  Claude Code Plugin                                      │    │
│  │       │  Reads thought files                             │    │
│  │       │  Generates HTML + JavaScript equivalents         │    │
│  │       │  Creates documentation (.md) per report          │    │
│  │       ▼                                                  │    │
│  │  HTMLReportsFolder/                                      │    │
│  │       ├── patient_demographics.html                      │    │
│  │       ├── patient_demographics.md                        │    │
│  │       ├── blood_type_distribution.html                   │    │
│  │       ├── blood_type_distribution.md                     │    │
│  │       └── ...                                            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                       │                                          │
│                       │  Artifacts committed to .NET project     │
│                       ▼                                          │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PHASE 2: Runtime (.NET Frontend + Python Brain Service)         │
│  ───────────────────────────────────────────────────────         │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  .NET Application (User-Facing — existing app)            │   │
│  │                                                           │   │
│  │  1. User types NL prompt in report UI                     │   │
│  │  2. .NET calls Python API: POST /decode-prompt            │   │
│  │  3. Receives: { report, parameters, template }            │   │
│  │  4. Existing data access layer → SQL Server → data        │   │
│  │  5. Calls Python API: POST /summarize (data + question)   │   │
│  │  6. Receives: narrative summary                           │   │
│  │  7. Populates static HTML template with data + narrative  │   │
│  │  8. Serves rendered report to user                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│              │                            ▲                      │
│              │ POST /decode-prompt        │ {report, params}     │
│              │ POST /summarize            │ narrative             │
│              ▼                            │                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Python Package (Background Brain Service — port 8000)    │   │
│  │                                                           │   │
│  │  Inputs loaded at startup:                                │   │
│  │    ├── ReportThoughts/      (report logic context)        │   │
│  │    ├── HTMLReportsFolder/   (template registry)           │   │
│  │    └── DataSchemaMapping    (DB schema context)           │   │
│  │                                                           │   │
│  │  Endpoints:                                               │   │
│  │  POST /decode-prompt → Llama classifies intent + params   │   │
│  │  POST /summarize     → Llama summarizes query results     │   │
│  │                                                           │   │
│  │  If Llama fails on /summarize:                            │   │
│  │    Anonymize (phi-markers.json)                           │   │
│  │    → Claude API (anonymized data only)                    │   │
│  │    → Re-map pseudonyms                                    │   │
│  │    → Return narrative                                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────┐                                               │
│  │   Ollama      │  (Llama, CPU or GPU)                         │
│  │   :11434      │                                               │
│  └──────────────┘                                               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Build-Time Report Migration (Claude Code Plugin)

### Purpose

Phase 1 is a **Claude Code plugin** used within the .NET code project during the development lifecycle. It replaces the SSRS/Crystal Reports development workflow by:
1. Analyzing existing report definitions to extract business logic
2. Generating static HTML + JavaScript replacements

This is NOT a runtime component — it runs during development and produces static artifacts that are committed to the codebase.

### Sub-Phase 1a: Research Phase

Claude Code reads existing SSRS report definitions (`.rdl` XML) and Crystal Report documentation (`.md` files describing `.rpt` reports) and produces a structured **thought file** for each report.

```
Existing Report
    │
    ▼
Claude Code Plugin (Research)
    │
    │  For each report:
    │    1. Parse report definition / documentation
    │    2. Extract database connections and tables used
    │    3. Identify SQL queries, joins, and filters
    │    4. Document business logic (formulas, calculated fields)
    │    5. Capture grouping and sorting rules
    │    6. Map conditional logic (show/hide, formatting rules)
    │    7. List parameters and their types
    │    8. Note report layout structure
    │
    ▼
ReportThoughts/{report_name}.thought.md
```

#### Thought File Structure (Example)

```markdown
# Report Thought: Patient Demographics Summary

## Source
- **Type:** SSRS (.rdl)
- **File:** Reports/PatientDemographics.rdl
- **Last Modified:** 2024-11-15

## Database Context
- **Data Source:** HealthcareDB
- **Tables Used:**
  - Patients (alias: p) — primary entity
  - Facilities (alias: f) — joined via p.FacilityId = f.Id
- **Relationships:**
  - Patients.FacilityId → Facilities.Id (many-to-one)

## Queries
- **Main Query:**
  ```sql
  SELECT p.Gender,
    CASE
      WHEN DATEDIFF(YEAR, p.DateOfBirth, GETDATE()) < 18 THEN 'Pediatric'
      WHEN DATEDIFF(YEAR, p.DateOfBirth, GETDATE()) BETWEEN 18 AND 64 THEN 'Adult'
      ELSE 'Senior'
    END AS AgeGroup,
    COUNT(*) AS PatientCount
  FROM Patients p
  WHERE p.Status = 'Active'
  GROUP BY p.Gender, [AgeGroup CASE expression]
  ```

## Business Logic
- **Age Grouping Formula:**
  - < 18 years → "Pediatric"
  - 18-64 years → "Adult"
  - 65+ years → "Senior"
- **Filter:** Active patients only (Status = 'Active')
- **Grouping:** By Gender, then by AgeGroup

## Conditional Logic
- If PatientCount = 0 for any group → suppress row
- Header shows total active patient count

## Parameters
- **FacilityId** (optional, INT) — filter by facility
- **DateRange** (optional, date pair) — filter by registration date

## Layout
- Summary card: total active patients
- Table: Gender × AgeGroup with counts
- Footer: report generation timestamp
```

### Sub-Phase 1b: Migration Phase

Claude Code reads all thought files and generates static HTML + JavaScript reports with accompanying documentation.

```
ReportThoughts/*.thought.md
    │
    ▼
Claude Code Plugin (Migration)
    │
    │  For each thought file:
    │    1. Read the extracted business logic
    │    2. Generate HTML template with data binding placeholders
    │    3. Generate JavaScript for rendering logic
    │       (sorting, conditional display, formatting)
    │    4. Create documentation (.md) describing the new report
    │    5. Map parameters to input controls
    │
    ▼
HTMLReportsFolder/
    ├── patient_demographics.html    # Static HTML template
    ├── patient_demographics.js      # Rendering logic (sorting, formatting)
    ├── patient_demographics.md      # Report documentation
    ├── blood_type_distribution.html
    ├── blood_type_distribution.js
    ├── blood_type_distribution.md
    └── ...
```

**Why the two-sub-phase approach?**
- **Thought files are reviewable:** A developer can verify Claude's understanding of the report BEFORE any code is generated. Catching a misunderstood formula at the thought file stage is much cheaper than debugging incorrect HTML output.
- **Thought files are reusable:** If the HTML template needs regeneration (styling change, new framework), the thought files don't need to be recreated — the analysis is preserved.
- **Separation of concerns:** Understanding a report (research) and generating a replacement (migration) are distinct skills. Separating them produces better results from the LLM.

### Data Dictionary / Schema Mapping

The Claude Code plugin also generates a **data schema mapping** artifact that Phase 2 uses for prompt decoding. Three approaches:

#### Option A: Fully Automated

Script connects to SQL Server, extracts all tables/columns/types/relationships/constraints automatically.

| Pros | Cons |
|------|------|
| Zero manual effort | Includes internal/system tables the LLM doesn't need |
| Always complete — no missing tables | Column names like `Col1`, `FK_PatTbl_3` are meaningless to the LLM |
| Easy to re-run on schema changes | No business context ("Patients" table could mean anything) |
| | PHI columns not marked — anonymizer doesn't know what to strip |

#### Option B: Fully Curated

Developer manually selects reportable tables, writes business-friendly descriptions, marks PHI columns.

| Pros | Cons |
|------|------|
| LLM gets business context — better prompt decoding | Manual effort for every table/column |
| PHI columns explicitly marked — anonymizer is accurate | Risk of missing tables/columns |
| Excludes irrelevant system tables | Must be manually updated on schema changes |

#### Option C: Hybrid (Recommended)

Auto-generate the skeleton from SQL Server, then developer annotates business descriptions and PHI markers.

| Pros | Cons |
|------|------|
| Completeness of auto-generation | Requires developer review step |
| Business context of manual curation | Initial review takes 1-2 hours for medium schema |
| PHI markers for accurate anonymization | |
| Easy to re-run: regenerate skeleton, diff against existing annotations | |

### Schema Mapping Example

```json
{
  "database": "HealthcareDB",
  "generated": "2026-07-02T10:00:00Z",
  "tables": [
    {
      "name": "Patients",
      "description": "Active and inactive recipients of care",
      "reportable": true,
      "columns": [
        { "name": "Id", "type": "INT", "description": "Primary key", "phi": false },
        { "name": "FirstName", "type": "NVARCHAR(100)", "description": "Patient first name", "phi": true },
        { "name": "LastName", "type": "NVARCHAR(100)", "description": "Patient last name", "phi": true },
        { "name": "DateOfBirth", "type": "DATE", "description": "Patient date of birth", "phi": true },
        { "name": "MRN", "type": "NVARCHAR(20)", "description": "Medical Record Number", "phi": true },
        { "name": "BloodType", "type": "NVARCHAR(10)", "description": "ABO/Rh blood type", "phi": false },
        { "name": "Gender", "type": "NVARCHAR(20)", "description": "Patient gender", "phi": false },
        { "name": "Status", "type": "NVARCHAR(20)", "description": "Active or Inactive", "phi": false },
        { "name": "FacilityId", "type": "INT", "description": "Foreign key to Facilities", "phi": false }
      ],
      "relationships": [
        { "column": "FacilityId", "references": "Facilities.Id", "type": "many-to-one" }
      ]
    }
  ]
}
```

### Phase 1 Artifacts Summary

| Artifact | Location | Purpose | Consumer |
|----------|----------|---------|----------|
| Thought files | `ReportThoughts/*.thought.md` | Business logic analysis of each existing report | Phase 1b (migration), Phase 2 (LLM context), developers (review) |
| HTML templates | `HTMLReportsFolder/*.html` | Static report templates with data binding placeholders | Phase 2 (report rendering) |
| JavaScript | `HTMLReportsFolder/*.js` | Rendering logic (sorting, formatting, conditional display) | Phase 2 (browser-side rendering) |
| Report docs | `HTMLReportsFolder/*.md` | Human-readable documentation per report | Developers, QA |
| Schema mapping | `DataSchemaMapping/schema-mapping.json` | DB schema context for LLM prompt decoding | Phase 2 (Llama context) |
| PHI markers | `DataSchemaMapping/phi-markers.json` | Which columns contain PHI (for anonymizer) | Phase 2 (Claude fallback anonymization) |

---

## Phase 2: Runtime Reporting Engine (.NET Frontend + Python Brain)

### Purpose

Phase 2 uses the **existing .NET application** as the user-facing service. A Python package runs as a **background "brain" service** with two endpoints — one to decode natural language prompts, one to summarize query results. The .NET app orchestrates the full flow: receive user prompt → call Python to decode → fetch data via existing data access layer → call Python to summarize → populate HTML template → serve report.

### Architecture Pattern (Option B: .NET is Frontend)

```
              .NET Application (existing)            Python Brain Service
              ┌────────────────────────┐          ┌──────────────────────┐
              │                        │          │                      │
User ────────▶│  1. Receive NL prompt  │  POST    │                      │
  "Show me    │  2. Call Python ───────│─────────▶│  /decode-prompt      │
   patients   │     /decode-prompt     │          │  Llama classifies    │
   over 65    │  3. Get back:          │◀─────────│  intent + extracts   │
   at Austin  │     {report, params,   │  JSON    │  parameters          │
   General"   │      template}         │          │                      │
              │  4. SQL Server query   │          │                      │
              │     (existing DAL)     │  POST    │                      │
              │  5. Call Python ───────│─────────▶│  /summarize          │
              │     /summarize         │          │  Llama summarizes    │
              │  6. Get back:          │◀─────────│  (or Claude fallback │
              │     narrative text     │  JSON    │   with anonymized)   │
              │  7. Populate template  │          │                      │
              │  8. Serve HTML report  │          │                      │
              └────────────────────────┘          └──────────────────────┘
```

**Why .NET as frontend (Option B)?**
- **.NET already has the user-facing surface.** Users interact with an existing .NET application — adding a "report" section avoids a second web server, second auth system, second entry point.
- **Data stays in .NET.** Existing parameterized queries, connection pooling, and security model are reused. Python never touches SQL Server.
- **Simpler Python service.** The Python package is a stateless background API with two endpoints. No HTML serving, no session management, no static files. Smaller attack surface.

### What Each Service Does

| .NET Application (orchestrator) | Python Package (brain) |
|---------------------------------|----------------------|
| Serve report UI to user | Decode NL prompt → report key + params |
| Authenticate users | Summarize query results into narrative |
| Call Python API for LLM operations | Handle Claude fallback with anonymization |
| Execute SQL via existing data access layer | Load ReportThoughts + Schema as LLM context |
| Populate HTML templates with data + narrative | — |
| Serve rendered report to user | — |

### Request Flow (Detailed)

```
User: "How many patients do we have by blood type?"
                    │
                    ▼
          ┌──────────────────┐
          │ .NET App         │  Receives user prompt
          │ (Report UI)      │
          └────────┬─────────┘
                   │
          ┌────────▼─────────────────────────────────┐
          │ POST /decode-prompt to Python             │
          │                                           │
          │ Python injects context:                   │
          │  - ReportThoughts/*.thought.md            │
          │  - DataSchemaMapping/schema-mapping.json   │
          │                                           │
          │ Llama output:                             │
          │ {                                         │
          │   "report": "blood_type_distribution",    │
          │   "parameters": {},                       │
          │   "template": "blood_type_dist.html"      │
          │ }                                         │
          └────────┬─────────────────────────────────┘
                   │
          ┌────────▼─────────┐
          │ .NET Data Access │  Existing code, existing queries
          │ → SQL Server     │  → [{BloodType: "O+", Count: 142},
          │   (read-only)    │     {BloodType: "A+", Count: 98}, ...]
          └────────┬─────────┘
                   │
          ┌────────▼─────────────────────────────────┐
          │ POST /summarize to Python                 │
          │                                           │
          │ Llama summarizes raw data locally          │
          │ Produces narrative summary                 │
          │                                           │
          │ If Llama fails:                           │
          │   Python anonymizes (phi-markers.json)    │
          │   → Claude API (anonymized data only)     │
          │   → Re-maps pseudonyms locally            │
          │   → Returns narrative                     │
          └────────┬─────────────────────────────────┘
                   │
          ┌────────▼─────────┐
          │ .NET populates   │  Static HTML template from
          │ HTML template    │  HTMLReportsFolder/
          │ with data +      │
          │ narrative         │  → Rendered report to user
          └──────────────────┘
```

### Python API Endpoints

#### POST /decode-prompt

Decodes a natural language question into a structured report request.

**Request:**
```json
{
  "question": "How many patients do we have by blood type?"
}
```

**Response:**
```json
{
  "report": "blood_type_distribution",
  "parameters": {},
  "template": "blood_type_distribution.html",
  "confidence": 0.92
}
```

**Response (no match):**
```json
{
  "report": "UNKNOWN",
  "parameters": {},
  "template": null,
  "confidence": 0.0,
  "message": "No matching report found for this question"
}
```

#### POST /summarize

Summarizes query results into a human-readable narrative.

**Request:**
```json
{
  "question": "How many patients do we have by blood type?",
  "results": [
    {"BloodType": "O+", "Count": 142},
    {"BloodType": "A+", "Count": 98}
  ],
  "row_count": 8
}
```

**Response:**
```json
{
  "summary": "The majority of active patients have blood type O+ (142 patients, 29%), followed by A+ (98 patients, 20%). The least common blood type is AB- with only 12 patients (2%).",
  "source": "llama"
}
```

**Response (Claude fallback):**
```json
{
  "summary": "The majority of active patients have blood type O+ ...",
  "source": "claude",
  "anonymized": true
}
```

### LLM Prompt Templates

#### Intent Classification + Parameter Extraction

```
You are a report routing system for a healthcare application.

AVAILABLE REPORTS:
{report_thoughts_summaries}

DATABASE SCHEMA:
{schema_mapping_context}

Given the user's question, determine:
1. Which report best matches (return the report key)
2. What parameters to extract (dates, facilities, filters)
3. Which HTML template to use

If no report matches, return "UNKNOWN".

User question: "{user_question}"

Response (JSON):
{
  "report": "<report_key>",
  "parameters": { ... },
  "template": "<template_file>"
}
```

#### Result Summarization

```
You are a healthcare data analyst. Summarize the following query results
in a way that is useful for a non-technical healthcare professional.

USER QUESTION: "{user_question}"
QUERY RESULTS (JSON): {json_results}
TOTAL ROWS: {row_count}

Provide:
1. A 2-3 sentence executive summary highlighting key findings
2. Notable patterns or outliers
3. Any data quality observations (e.g., NULL values, unexpected distributions)

Keep the tone professional and factual. Do not speculate beyond what the
data shows.
```

---

## PHI Safety Boundary

**Core principle:** Raw patient data (PHI) never leaves the server. The cloud LLM fallback only receives anonymized, aggregated data.

```
         ON-PREM (PHI allowed)              CLOUD (anonymized only)
        ─────────────────────              ─────────────────────────
Data:   John Smith, DOB 03/15/1985   →     Patient_001, Age: 30-39
        MRN: MRN-84729               →     ID: P_001
        SSN: 123-45-6789             →     [REDACTED]
        123 Main St, Austin TX       →     State: TX

LLM:    Llama (sees raw data)              Claude (sees pseudonymized)
        Never leaves server                Safe to transmit
```

### Anonymization Rules (Driven by phi-markers.json)

| Data Type | On-Prem (Llama) | Cloud (Claude) |
|-----------|-----------------|----------------|
| Patient names | Raw | Pseudonymized: Patient_001 |
| Dates of birth | Raw | Age range: 30-39 |
| MRNs | Raw | Sequential: P_001 |
| SSNs | Raw (if queried) | Always `[REDACTED]` — never sent |
| Addresses | Raw | State/region only |
| Aggregate counts | Raw | Passed through unchanged (not PHI) |
| Percentages | Raw | Passed through unchanged (not PHI) |

### Re-mapping

When Claude returns a narrative using pseudonymized identifiers, the Python package re-maps pseudonyms to real values locally before rendering the final report. The user sees real names; Claude never does.

---

## Claude Fallback Trigger Conditions

| Condition | Detection Method |
|-----------|-----------------|
| Llama produces empty/gibberish output | Response length < 20 chars or fails structure check |
| Llama times out | No response within 60 seconds |
| Llama summary quality is low | Response doesn't reference data values from result set |
| Result set is very large | > 5,000 rows (Llama context window may struggle) |
| Llama is unavailable | Ollama connection refused / model not loaded |

### Fallback Pipeline

```
Raw query results (with PHI)
    │
    ▼
Anonymizer (using phi-markers.json)
    ├─ Replace names → Patient_001, Patient_002
    ├─ Replace DOBs → age ranges
    ├─ Replace MRNs → P_001, P_002
    ├─ Redact SSNs → [REDACTED]
    ├─ Replace addresses → state only
    └─ Build pseudonym mapping table
    │
    ▼
Anonymized results → Claude API
    │
    ▼
Claude narrative (uses pseudonyms)
    │
    ▼
Re-mapper: pseudonyms → real values (using mapping table, locally)
    │
    ▼
Final narrative → Report renderer
```

---

## Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Phase 1 Plugin** | Claude Code (skills/agents) | Codebase-aware AI — reads report files, understands context, generates artifacts |
| **Host Project** | .NET (existing application) | Reports plugin operates within the .NET project that already has DB access |
| **Phase 2 Frontend** | .NET (existing application) | User-facing service — serves UI, handles auth, fetches data, renders reports |
| **Phase 2 Brain** | Python 3.11+ (background API service) | LLM orchestration — prompt decoding + summarization via Ollama/Claude |
| **Database** | SQL Server (accessed via .NET only) | Existing data access layer reused — Python never touches SQL Server |
| **Local LLM** | Ollama → Llama | Runs on same box as app, called by Python for prompt decoding + summarization |
| **Cloud Fallback** | Claude API (anthropic SDK) | Only receives anonymized data, called by Python when Llama fails |
| **Report Templates** | Static HTML + JavaScript | Generated in Phase 1, populated by .NET at runtime with data + narrative |
| **API Communication** | REST API (.NET → Python) | .NET calls Python for LLM operations; Python never calls .NET |

### Python Package Dependencies

```
ollama>=0.4.0
anthropic>=0.40.0
python-dotenv>=1.0.0
fastapi>=0.115.0        # API layer for the Python package
uvicorn>=0.30.0         # ASGI server
```

---

## Project Structure

### .NET Project (Phase 1 Plugin + Artifacts)

```
DotNetProject/
├── Reports/                          # Existing SSRS/Crystal report source files
│   ├── PatientDemographics.rdl       # SSRS report definition
│   ├── BloodTypeDistribution.rdl
│   └── ...
├── ReportThoughts/                   # Phase 1a output: analyzed report logic
│   ├── patient_demographics.thought.md
│   ├── blood_type_distribution.thought.md
│   ├── encounter_summary.thought.md
│   └── ...
├── HTMLReportsFolder/                # Phase 1b output: static HTML replacements
│   ├── patient_demographics.html
│   ├── patient_demographics.js
│   ├── patient_demographics.md
│   ├── blood_type_distribution.html
│   ├── blood_type_distribution.js
│   ├── blood_type_distribution.md
│   └── ...
├── DataSchemaMapping/                # Schema context for Phase 2
│   ├── schema-mapping.json           # DB schema with business descriptions
│   └── phi-markers.json              # PHI column markers for anonymizer
└── .claude/                          # Claude Code plugin configuration
    ├── skills/
    │   └── report-forge/
    │       └── SKILL.md              # Plugin skill definition
    └── agents/
        ├── report-researcher.md      # Research phase agent
        └── report-migrator.md        # Migration phase agent
```

### Python Package (Phase 2 Brain Service)

```
ai-report-forge/
├── ai_report_forge/                  # Python package
│   ├── __init__.py
│   ├── api.py                        # FastAPI: POST /decode-prompt, POST /summarize
│   ├── config.py                     # Ollama URL, Claude key, artifact paths
│   ├── prompt_decoder.py             # Llama decodes NL → report key + params
│   ├── summarizer.py                 # Llama summarizes query results
│   ├── anonymizer.py                 # Strip PHI using phi-markers.json
│   ├── claude_fallback.py            # Claude API (anonymized data only)
│   └── context_loader.py            # Load ReportThoughts + Schema at startup
├── tests/
│   ├── test_prompt_decoder.py        # Intent classification tests
│   ├── test_anonymizer.py            # PHI stripping tests
│   └── test_summarizer.py            # Summarization + Claude fallback tests
├── requirements.txt
├── .env.example
└── README.md
```

**Note:** `template_renderer.py` is removed from the Python package. Template population now happens in .NET — Python only returns data (decoded params + narrative text), and .NET populates the HTML templates.

---

## Database Setup

### Read-Only User (Defense in Depth)

Even though the existing .NET code handles SQL execution, a dedicated read-only user ensures defense in depth:

```sql
-- scripts/setup_db_user.sql

CREATE LOGIN [ai_report_reader] WITH PASSWORD = '<strong-password>';

USE [HealthcareDB];
CREATE USER [ai_report_reader] FOR LOGIN [ai_report_reader];

-- Grant SELECT only
ALTER ROLE [db_datareader] ADD MEMBER [ai_report_reader];

-- Explicitly deny dangerous permissions
DENY INSERT, UPDATE, DELETE, EXECUTE, ALTER, CREATE TABLE,
     DROP TABLE, CREATE VIEW, CREATE PROCEDURE
TO [ai_report_reader];
```

### Synthetic Schema (for PoC without production data)

```sql
CREATE TABLE Patients (
    Id INT PRIMARY KEY IDENTITY,
    FirstName NVARCHAR(100),
    LastName NVARCHAR(100),
    DateOfBirth DATE,
    Gender NVARCHAR(20),
    BloodType NVARCHAR(10),
    MRN NVARCHAR(20) UNIQUE,
    Status NVARCHAR(20) DEFAULT 'Active',
    FacilityId INT,
    CreatedDate DATETIME DEFAULT GETDATE()
);

CREATE TABLE Facilities (
    Id INT PRIMARY KEY IDENTITY,
    FacilityName NVARCHAR(200),
    City NVARCHAR(100),
    State NVARCHAR(2),
    Status NVARCHAR(20) DEFAULT 'Active'
);

CREATE TABLE Encounters (
    Id INT PRIMARY KEY IDENTITY,
    PatientId INT FOREIGN KEY REFERENCES Patients(Id),
    EncounterType NVARCHAR(50),
    EncounterDate DATE,
    ProviderId INT,
    Status NVARCHAR(20),
    Notes NVARCHAR(MAX)
);

CREATE TABLE Providers (
    Id INT PRIMARY KEY IDENTITY,
    FirstName NVARCHAR(100),
    LastName NVARCHAR(100),
    Specialty NVARCHAR(100),
    FacilityId INT FOREIGN KEY REFERENCES Facilities(Id)
);
```

---

## Security Considerations

### Defense in Depth

| Layer | Control | Protects Against |
|-------|---------|-----------------|
| 1. .NET Data Access | Parameterized queries in existing code | SQL injection |
| 2. DB User Permissions | SELECT-only role | Data modification |
| 3. Query Timeout | 30-second hard limit in .NET | Runaway queries, DoS |
| 4. Row Limit | Results capped at 10,000 rows | Memory exhaustion |
| 5. PHI Anonymizer | Strip PHI before cloud API (phi-markers.json) | HIPAA violation |
| 6. No SSN Transmission | SSNs always `[REDACTED]` | Identity theft risk |
| 7. Prompt Injection Guard | Separate system/user message roles | LLM prompt manipulation |
| 8. Internal API Auth | .NET → Python call secured (API key or localhost-only) | Unauthorized brain service access |
| 9. Python has no DB access | Python only receives data via .NET, never queries directly | Data exfiltration via brain service |

---

## Environment Configuration

### Python Brain Service (.env)

```bash
# .env.example (Python brain service)

# Ollama (local LLM)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_TIMEOUT=60

# Claude API (fallback only — anonymized data)
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-20250514
CLAUDE_MAX_TOKENS=4096

# Artifact Paths (Phase 1 outputs consumed by Phase 2)
REPORT_THOUGHTS_PATH=../DotNetProject/ReportThoughts
HTML_REPORTS_PATH=../DotNetProject/HTMLReportsFolder
SCHEMA_MAPPING_PATH=../DotNetProject/DataSchemaMapping/schema-mapping.json
PHI_MARKERS_PATH=../DotNetProject/DataSchemaMapping/phi-markers.json

# Brain Service
BRAIN_HOST=0.0.0.0
BRAIN_PORT=8000
```

### .NET Application (appsettings.json addition)

```json
{
  "ReportForge": {
    "BrainServiceUrl": "http://localhost:8000",
    "BrainServiceTimeout": 30,
    "HtmlReportsPath": "./HTMLReportsFolder",
    "MaxQueryRows": 10000
  }
}
```

---

## PoC Build Phases

| Phase | Deliverable | Components | Est. Effort |
|-------|-------------|------------|-------------|
| **1a: Research Plugin** | Claude Code plugin for report analysis | `report-researcher` agent, thought file format, SSRS .rdl parser prompt | Day 1 |
| **1b: Migration Plugin** | Claude Code plugin for HTML generation | `report-migrator` agent, HTML+JS template generation from thought files | Day 1-2 |
| **1c: Schema Mapping** | Data schema artifacts | Schema introspection script, `schema-mapping.json`, `phi-markers.json` | Day 2 |
| **2a: Python Brain** | Brain service scaffold | `api.py` (two endpoints), `prompt_decoder.py`, `context_loader.py`, Ollama integration | Day 2-3 |
| **2b: .NET Integration** | Report UI + Python client | .NET controller with report prompt UI, HTTP client to call Python brain, template population | Day 3 |
| **3: Prompt Decoding** | Llama intent classification + param extraction | Prompt templates, ReportThoughts context injection, parameter parsing | Day 3-4 |
| **4: Report Rendering** | .NET template population + Python summarization | .NET populates HTML with data, `summarizer.py` generates narrative via Llama | Day 4 |
| **5: Claude Fallback** | PHI anonymizer + Claude API integration | `anonymizer.py`, `claude_fallback.py`, quality detection | Day 5 |
| **6: Polish** | Error handling, demo prep, README | Tests, UX polish, demo scenarios | Day 5-6 |

---

## Demo Scenarios

### Report Matches (LLM routes to existing report)
1. "How many patients do we have by blood type?"
2. "Show me patient demographics"
3. "Which facilities have the most active patients?"
4. "What types of encounters happened in the last 6 months?"
5. "Show me provider workload for the past month"

### Parameterized Queries (LLM extracts filters)
6. "Show me patients over 65 at Austin General"
7. "Provider workload for cardiology last quarter"
8. "New patient registrations by month this year"

### Fallback Demo (Claude)
9. Temporarily stop Ollama during a query to demonstrate graceful fallback with anonymized data

### Phase 1 Demo (Report Migration)
10. Show a before/after: SSRS .rdl → thought file → HTML report, demonstrating the research → migration pipeline

---

## Use Case Summary

| S.No | Use Case | Description | Business Impact | Definition of Done | Agent Type |
|------|----------|-------------|-----------------|-------------------|------------|
| 1 | AI-Driven Reporting | Phase 1: Claude Code plugin analyzes existing SSRS/Crystal reports, produces thought files capturing business logic, then generates static HTML+JS replacements. Phase 2: Python package uses Llama (local LLM) to decode user natural language prompts into structured input for existing .NET code, which fetches data from SQL Server and populates the static HTML templates. Claude API fallback with anonymized PHI for resilience. | Eliminates developer dependency for report creation and migration; business users self-serve insights via natural language; HIPAA-compliant with PHI never leaving the server boundary; existing .NET data access layer reused (no rewrite) | Phase 1: Existing report → thought file → HTML report pipeline demonstrated for 5 reports. Phase 2: User submits plain-English question and receives formatted HTML report; Llama decodes prompt within 10s; .NET API returns data within 5s; Claude fallback triggers automatically on failure with anonymized data; new reports deployable by adding thought files + HTML templates without app rebuild | Phase 1: Claude Code (codebase-aware AI plugin) / Phase 2: Local LLM (Llama via Ollama) + Cloud LLM fallback (Claude API) + Existing .NET Data Access Layer |

---

## Future Enhancements (Post-PoC)

| Enhancement | Description |
|-------------|-------------|
| **Scheduled reports** | Job scheduler + email integration for recurring reports |
| **Drill-down navigation** | Click a value in a report to see detailed breakdown |
| **PDF/Excel/CSV export** | Standard library integration for report download |
| **Row-level security** | User-scoped data filtering based on role/facility |
| **Chart generation** | Chart.js visualizations embedded in report templates |
| **Report subscriptions** | Users subscribe to reports and receive updates |
| **Audit logging** | Log all queries, LLM calls, and data access for compliance |
| **Multi-database support** | Extend beyond SQL Server to PostgreSQL, etc. |
| **Feedback loop** | Users rate report quality; improve prompts accordingly |
| **GPU acceleration** | Larger Llama model for better prompt decoding quality |
| **Bulk migration** | Batch-process all SSRS reports through Phase 1 pipeline |
| **Thought file versioning** | Track changes between report analysis runs |

---

## Open Questions

1. **Data Dictionary approach** — Which option (Auto / Curated / Hybrid) for the initial PoC? Hybrid recommended.
2. **VDI GPU availability** — Determines Llama model size (smaller for CPU-only, larger for GPU).
3. **Production database access** — Will PoC connect to real database or use synthetic data?
4. **Authentication** — Localhost-only sufficient for demo, or need user auth?
5. **Concurrent users** — Single-user PoC or multi-user support?
6. **Existing report format** — SSRS `.rdl` XML confirmed readable by Claude. Do Crystal Reports need pre-conversion to `.md` documentation? (`.rpt` files are binary — Claude cannot parse directly.)
7. ~~**Python ↔ .NET API contract**~~ — Resolved: .NET calls Python (Option B). Python exposes `POST /decode-prompt` and `POST /summarize`. API contracts documented above.
8. **Llama model selection** — Which Llama variant? (3.2 3B for CPU, 3.2 11B for GPU, etc.)
9. **Claude Code plugin packaging** — Will this be a Claude Code skill, a custom agent, or both?
10. **.NET report controller** — Does the existing .NET app already have a report-serving controller, or does a new one need to be added for the Report Forge UI?
