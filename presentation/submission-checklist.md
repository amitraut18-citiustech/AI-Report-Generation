# Submission Pack — AI Report Forge

**Use case #1 — AI-Driven Reporting** · One repo + demo + evidence.
This file maps every mandatory submission component to its location.

## Mandatory components

| Component | Location | Status |
|---|---|---|
| **Repository access / ZIP** — source, prompts, agent config, tools, sample inputs, generated outputs | This repo. Agent config: `.claude/` (3 agents, 1 skill, 3 commands). Runtime LLM prompts: `ai-report-forge/ai_report_forge/{prompt_decoder,summarizer,claude_fallback}.py`. Generated outputs: `ReportThoughts/`, `HTMLReportsFolder/`, `DataSchemaMapping/`. Sample inputs: `docs/NLP-Query-Reference.md` | ✅ |
| **README run document** — setup, prerequisites, commands, inputs, limitations, troubleshooting | `README.md` (overview) → `docs/quick_start.md` (5-minute setup) → `docs/runbook-ai-report-forge-poc.md` (full runbook + troubleshooting). Limitations: `docs/NLP-Query-Reference.md` → Current Limitations | ✅ |
| **Definition-of-Done evidence** — checklist mapped to the assigned use-case DoD | [`presentation/dod-evidence.md`](dod-evidence.md) — per-item status with measured timings and honest deviations | ✅ |
| **Sample data pack** — synthetic only, no real PHI | Synthetic SQLite dataset auto-seeded on startup; data dictionary in `docs/NLP-Query-Reference.md` → Seed Data Reference. **No real PHI/PII anywhere** | ✅ |
| **Demo script / video** | [`presentation/demo-script.md`](demo-script.md) (~3-min walkthrough, verified prompts). Video: `demo-recording/output/demo.mp4` (3:34, narrated, 17 steps incl. Phase-1 artifacts) — regenerate with `python demo-recording/orchestrator.py` | ✅ |
| **Output artifacts** — final deliverables + proof of run | Phase-1 deliverables in `HTMLReportsFolder/` + `ReportThoughts/` + `DataSchemaMapping/`; run proof: [`presentation/evidence/`](evidence/README.md) — 7 screenshots (banners, fallback, fail-closed MRN, PHI before/after, SSRS parity) + pytest output (53 passed) + the capture script to regenerate | ✅ |
| **Compliance note** — responsible-AI safeguards, human-in-the-loop, PHI safety, risks | [`presentation/compliance-note.md`](compliance-note.md) | ✅ |

## Judge quick-start (reproduce in ~5 minutes)

```bash
ollama pull qwen2.5:3b && ollama serve                # terminal 1
cd ai-report-forge && pip install -r requirements.txt
cp .env.example .env                                  # optional: add ANTHROPIC_API_KEY
python -m uvicorn ai_report_forge.api:app --host 127.0.0.1 --port 8080   # terminal 2
cd DotNetApp/PatientReports && dotnet run             # terminal 3
# open http://localhost:5282 → ask: "Show me patients at Austin General"
cd ai-report-forge && python -m pytest tests/ -v      # expect: 53 passed
```

Claude features (Ask Claude button, automatic fallback) need an Anthropic API key in
`ai-report-forge/.env`; everything else runs fully offline.

## Scoring-criteria pointers

| Criterion | Where to look |
|---|---|
| Functional completeness | `presentation/dod-evidence.md` |
| Agent design quality | `.claude/` plugin (modular agents/skill/commands), `docs/architecture.md` (trust boundaries, brain design) |
| Business value | `presentation/requirements.html` (SRS §2–3: Provider reporting, SSRS replacement, PHI compliance) |
| Innovation | Two-phase design: build-time agentic migration with human-reviewed thought files + runtime local/cloud LLM routing with provenance disclosure and a live PHI-anonymization transparency page (Prompt Log) |
| Demo & output quality | `presentation/demo-script.md`, presentation deck `presentation/AI-Report-Forge.html` |
| Reproducibility | Quick-start above; synthetic data auto-seeds; no external state |
| Safety & compliance | `presentation/compliance-note.md` + live Prompt Log |

## Other presentation assets

- `AI-Report-Forge.html` — slide deck (open in browser, arrow keys)
- `requirements.html` — Requirements Specification (SRS v1.1)

## Pre-submit checklist (final pass)

- [ ] Run once from a clean clone following the judge quick-start
- [ ] `pytest` → 53 passed
- [ ] Verify no secrets committed (`.env` is gitignored; only `.env.example` in repo)
- [x] Capture run-evidence screenshots (report + banner, Prompt Log before/after, MRN fail-closed, test output) — see `evidence/`
- [x] Record the demo video — `demo-recording/output/demo.mp4`
