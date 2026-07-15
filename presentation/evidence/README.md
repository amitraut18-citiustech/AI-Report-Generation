# Run Evidence — AI Report Forge

Screenshots and logs proving a completed end-to-end run (captured 2026-07-15 against the
live app, all four services running, valid Claude API key configured).

| File | Proves |
|---|---|
| `01-local-ask-report.png` | Natural-language ask via **Ask Local AI**: grey on-device banner, AI-derived filter (`Facilities.Name = Austin General Hospital`), filtered table (3 of 8 patients), AI Summary narrative |
| `02-ask-claude-report.png` | Direct **Ask Claude**: amber banner, Claude-decoded filters, correct single-row result |
| `03-claude-fallback-banner.png` | **Automatic fallback**: colloquial question failed on the local model; amber "Claude (fallback)" banner; Claude's correct decode (`DonorType = Allogeneic`, 8 events) with AI Summary |
| `04-mrn-fail-closed.png` | **Fail-closed security**: probing protected field MRN returns zero rows + explanation instead of dumping the table |
| `05-prompt-log-routing.png` | Prompt Log with per-ask accordion groups and triggering-button badges |
| `06-phi-before-after.png` | **PHI anonymization evidence**: real data (Ava Patel, real DOB, contact info) side-by-side with what the LLM received (`Patient_001`, `30-39`, `[REDACTED]`) |
| `07-classic-ssrs-report.png` | Legacy parity: the original SSRS `.rdl` rendered via RdlRenderService, same data |
| `08-test-run.txt` | Full pytest output — **53 passed** (anonymizer, PHI pipeline, decoder guardrails, API validation, stats) |

## Regenerating

```bash
# all four services running (docs/quick_start.md), ANTHROPIC_API_KEY set, then:
pip install playwright && python -m playwright install chromium
cd presentation/evidence
python capture_evidence.py        # runs headed — the SSRS iframe is a PDF (no headless viewer)
cd ../../ai-report-forge && python -m pytest tests/ -v > ../presentation/evidence/08-test-run.txt
```

Restart the brain before capturing for a clean Prompt Log. Step 3 retries the fallback
prompt up to 3× (the local model occasionally decodes it — non-deterministic).
