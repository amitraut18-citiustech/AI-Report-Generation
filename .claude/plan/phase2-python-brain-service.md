# Phase 2: Python Brain Service — Implementation Plan

## Context

The user's scope is the **Python brain service** only — the background API that sits between the .NET app and the local LLM (Ollama). Phase 1 artifacts (thought files, HTML reports, schema mapping) will be provided separately. The VDI has Python 3.11+, Ollama with `qwen2.5-coder:3b`, PyPI access, and a Claude API key.

The brain has two jobs:
1. **Decode prompts** — classify a natural-language question into a report key + parameters
2. **Summarize results** — turn query result rows into a human-readable narrative

Ollama is primary; Claude API is the fallback (with PHI anonymization before any data leaves the server).

---

## Step 0: Prerequisites & Installation

**Verify environment:**
```bash
python --version          # confirm 3.11+
ollama list               # confirm qwen2.5-coder:3b is pulled
ollama run qwen2.5-coder:3b "hello"   # confirm it responds
```

**Create the Python project inside the repo:**
```
AI-Report-Generation/
└── ai-report-forge/          # new — Python brain service
    ├── ai_report_forge/      # package
    ├── tests/
    ├── requirements.txt
    ├── .env.example
    └── README.md
```

**Install dependencies:**
```
pip install fastapi uvicorn ollama anthropic python-dotenv pydantic
```

`requirements.txt`:
```
fastapi>=0.115.0
uvicorn>=0.30.0
ollama>=0.4.0
anthropic>=0.40.0
python-dotenv>=1.0.0
pydantic>=2.0.0
```

---

## Step 1: Project Scaffold & Configuration (`config.py`)

Create the package structure and a config module that loads settings from `.env`:

```
ai_report_forge/
├── __init__.py
├── config.py               # env vars: Ollama URL/model, Claude key, artifact paths, timeouts
```

`.env.example`:
```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:3b
OLLAMA_TIMEOUT=60

ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-20250514
CLAUDE_MAX_TOKENS=4096

REPORT_THOUGHTS_PATH=../ReportThoughts
HTML_REPORTS_PATH=../HTMLReportsFolder
SCHEMA_MAPPING_PATH=../DataSchemaMapping/schema-mapping.json
PHI_MARKERS_PATH=../DataSchemaMapping/phi-markers.json

BRAIN_HOST=0.0.0.0
BRAIN_PORT=8000
```

---

## Step 2: Context Loader (`context_loader.py`)

Loads Phase 1 artifacts at startup so they're available as LLM context:
- Read all `*.thought.md` files from `REPORT_THOUGHTS_PATH` — extract report keys and summaries
- Read `schema-mapping.json` — the DB schema context
- Read `phi-markers.json` — PHI column markers (used by anonymizer)
- Build a report registry: `{report_key: {thought_summary, template_file, fields}}`

This module runs once at startup, not per-request.

---

## Step 3: Prompt Decoder (`prompt_decoder.py`)

Calls Ollama to classify a user's NL question:
- Builds a system prompt from the loaded thought file summaries + schema mapping
- Sends the user question to Ollama (`qwen2.5-coder:3b`)
- Parses the JSON response: `{report, parameters, template, confidence}`
- Returns `UNKNOWN` if confidence is low or response is malformed

Prompt template follows the plan's "Intent Classification + Parameter Extraction" template.

---

## Step 4: Summarizer (`summarizer.py`)

Calls Ollama to summarize query result rows:
- Builds a prompt from the user question + JSON result rows + row count
- Sends to Ollama
- Validates response quality (length > 20 chars, references data values)
- Returns `{summary, source: "ollama"}`
- If quality check fails → triggers Claude fallback

---

## Step 5: Anonymizer (`anonymizer.py`)

Strips PHI from result rows before sending to Claude:
- Reads `phi-markers.json` for column → strategy mapping
- Applies strategies: `pseudonymize`, `age_range`, `sequential_id`, `redact`, `region_only`
- Builds a reverse-mapping table for re-identification after Claude responds
- Returns anonymized rows + mapping table

---

## Step 6: Claude Fallback (`claude_fallback.py`)

Called when Ollama fails or produces low-quality output:
- Takes anonymized rows (from anonymizer) + user question
- Calls Claude API via `anthropic` SDK
- Gets narrative summary back (using pseudonymized identifiers)
- Re-maps pseudonyms to real values using the mapping table
- Returns `{summary, source: "claude", anonymized: true}`

---

## Step 7: FastAPI App (`api.py`)

Two endpoints:

**POST /decode-prompt**
- Request: `{question: string}`
- Calls `prompt_decoder`
- Response: `{report, parameters, template, confidence}` or `{report: "UNKNOWN", ...}`

**POST /summarize**
- Request: `{question: string, results: [...], row_count: int}`
- Calls `summarizer` (Ollama first)
- If Ollama fails → anonymizer → Claude fallback → re-map
- Response: `{summary, source: "ollama"|"claude", anonymized?: bool}`

**Startup event:**
- Loads context (thought files, schema, PHI markers) via `context_loader`
- Validates Ollama connectivity

**Health endpoint:**
- `GET /health` — returns Ollama status + loaded report count

---

## Step 8: Tests

```
tests/
├── test_prompt_decoder.py    # mock Ollama responses, verify JSON parsing
├── test_anonymizer.py        # verify each PHI strategy + re-mapping
├── test_summarizer.py        # mock Ollama, verify quality check + fallback trigger
└── test_api.py               # FastAPI TestClient integration tests
```

Use `pytest` + `httpx` (FastAPI TestClient).

---

## Build Order

| Order | Module | Depends on | Validates with |
|-------|--------|-----------|----------------|
| 1 | `config.py` | nothing | import and print config |
| 2 | `context_loader.py` | config | load sample artifacts, print registry |
| 3 | `prompt_decoder.py` | config, context_loader | call with sample question, verify JSON |
| 4 | `summarizer.py` | config | call with sample data, check narrative |
| 5 | `anonymizer.py` | config (phi-markers) | unit test each strategy |
| 6 | `claude_fallback.py` | anonymizer, config | call with anonymized sample |
| 7 | `api.py` | all above | `uvicorn ai_report_forge.api:app --reload`, curl both endpoints |
| 8 | tests | all above | `pytest` |

---

## Verification

1. Start the service: `uvicorn ai_report_forge.api:app --host 0.0.0.0 --port 8000 --reload`
2. `GET /health` — confirms Ollama connection + loaded reports
3. `POST /decode-prompt` with `{"question": "Show me patients by blood type"}` — returns a report key
4. `POST /summarize` with sample rows — returns a narrative
5. Stop Ollama, repeat `/summarize` — confirms Claude fallback triggers with anonymized data
6. `pytest tests/` — all pass

---

## Model Consideration

The plan specifies Llama 3.2 (general-purpose). `qwen2.5-coder:3b` is code-optimized and may produce weaker natural-language summaries or struggle with intent classification from conversational questions. The config makes the model name an env var, so swapping to `llama3.2:3b` later is a one-line change. Worth testing both once the endpoints are working.
