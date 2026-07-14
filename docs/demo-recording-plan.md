# Automated Demo Recording Pipeline — Plan

## Context

The AI Report Forge PoC has 6 documented demo scenarios in the runbook but no automated way to produce a demo video. Stakeholder demos require someone to manually walk through the app while screen-recording. This pipeline automates that: a Playwright script walks the demo flow, captures screenshots at each step, generates narration audio via a free TTS engine, and stitches everything into an MP4 with voiceover.

No TTS API keys are available, so we use `edge-tts` (Microsoft Edge neural voices, free, no key required). All four services (Ollama, Python brain, .NET app, RdlRenderService) are auto-started and health-checked by the orchestrator.

## Architecture

```
demo-recording/
├── orchestrator.py          # Main entry point: start services, run Playwright, generate TTS, stitch video
├── playwright_demo.py       # Playwright script: walks all 4 pages, captures numbered screenshots
├── narration.json           # Step → narration text manifest
├── requirements.txt         # playwright, edge-tts, Pillow
├── screenshots/             # Output: step-01.png, step-02.png, ...
├── audio/                   # Output: step-01.mp3, step-02.mp3, ...
└── output/                  # Output: demo.mp4
```

FFmpeg is required on PATH (pre-installed or user installs separately).

---

## Demo Flow (Full, ~14 steps)

| Step | Page | Action | Screenshot Captures | Narration |
|------|------|--------|-------------------|-----------|
| 1 | AI Reports | Land on homepage | Empty state with question input | "This is AI Report Forge — a natural language reporting tool that replaces legacy SSRS and Crystal Reports with AI-powered querying." |
| 2 | AI Reports | Type "Show me patients at Austin General" | Filled question input | "We type a natural language question — no SQL, no report parameters, just plain English." |
| 3 | AI Reports | Click "Ask Local AI", wait for the provenance banner | Report with Local LLM banner + filter badges + data table + AI Summary | "The local model decoded the question into structured filters. Notice the grey banner — all processing happened on-premise. No data left this machine." |
| 4 | AI Reports | Scroll to show AI Summary narrative | AI Summary card visible | "An AI-generated narrative summarizes the filtered results, highlighting key patterns in the data." |
| 5 | AI Reports | Clear question, type "Show female patients at Austin General Hospital", click "Ask Claude" | Report with amber Claude banner | "Now we ask using Claude. The amber banner shows this was decoded by the cloud API. The application supports both local and cloud models with full transparency." |
| 6 | AI Reports | Type "which sheet lists the folks who got cells from a donor other than themselves", click "Ask Local AI" (retry up to 3× until the fallback banner appears — see Fallback staging below) | Report with amber "Claude (fallback)" banner | "This phrasing is too colloquial for the small local model — it failed, and the system automatically fell back to Claude. The banner says so explicitly: cloud usage is never silent." |
| 7 | AI Reports | Type "show patient with MRN-00003", click "Ask Local AI" | Zero-row report + struck-through filter badge + explanation narrative | "Here's the security model at work. MRN is a protected field — the filter is blocked, and rather than showing more data than was asked for, the report fails closed with zero rows and an explanation." |
| 8 | Prompt Log | Click "Prompt Log" nav link | Prompt Log page; newest accordion group expanded, older asks collapsed | "The Prompt Log shows exactly what was sent to each model. Each question is a collapsible group; the routing chain shows what happened — including the local-model failure and Claude fallback we just saw." |
| 9 | Prompt Log | Expand the group for the step-3 ask; scroll to its Summarize card | Side-by-side PHI comparison (before/after) | "This is the key privacy feature. Real patient data on the left was never sent to any model. The LLM only saw the anonymized version on the right — pseudonyms, age ranges, and redacted identifiers." |
| 10 | AI Reports | Navigate back, select "Transplant Event Report" from dropdown | Dropdown selected | "Reports can also be accessed directly from the dropdown without a natural language question." |
| 11 | AI Reports | Click "Generate Report" | Transplant event report in iframe | "The transplant event report shows donor types, visit dates, and inpatient status across all patients." |
| 12 | AI Reports | Select "Patient Clinical Summary", generate | Clinical summary report | "The clinical summary is the most complex report — it groups data by facility, computes BMI and risk scores, and flags abnormal lab results." |
| 13 | Classic Reports | Click "Classic Reports (SSRS)" nav link | SSRS page with dropdown | "For comparison, the original SSRS reports are still available side-by-side." |
| 14 | Classic Reports | Select "Patient Report", click Generate | RDL-rendered report in iframe | "The classic view renders the original RDL definition — same data, legacy format. This lets stakeholders compare the AI-generated reports against the originals." |

**Verified prompts** (against the live app, 2026-07-14): step 5's question decodes on Claude to `Gender = Female AND Facilities.Name = Austin General Hospital` (1 row); step 6's question failed on qwen2.5:3b and was rescued by Claude (`DonorType = Allogeneic`, 8 rows) in repeated runs; step 7's MRN probe reliably produces the fail-closed zero-row page.

**Fallback staging (step 6)**: the local model is not deterministic — occasionally it decodes even the colloquial phrasing. The script must check the banner after the ask: if it shows "Local LLM" instead of "Claude (fallback)", re-ask (up to 3 attempts). If still no fallback, capture the Local LLM result and swap in alternate narration ("The local model handled even this colloquial phrasing...") so the video never narrates something that didn't happen.

---

## Implementation Details

### 1. `demo-recording/requirements.txt`

```
playwright
edge-tts
Pillow
```

FFmpeg is a system dependency — the orchestrator checks for it and prints install instructions if missing.

### 2. `demo-recording/narration.json`

JSON array, each entry:
```json
{
  "step": 1,
  "filename": "step-01",
  "narration": "This is AI Report Forge...",
  "pause_after": 0.5
}
```
`pause_after` adds silence (seconds) after the audio clip for pacing between steps.

### 3. `demo-recording/playwright_demo.py`

Playwright script using the sync API. Key details:

**Browser config**: Chromium, viewport 1280×800, **headed** (`headless=False`) — the Classic/SSRS report renders as a PDF inside the iframe, and headless Chromium has no PDF viewer (blank frame). Verified during evidence capture; see `presentation/evidence/capture_evidence.py` for a working reference implementation of the waits/selectors.

**Selectors** (derived from the actual Razor views):

| Selector | Element | Page |
|----------|---------|------|
| `#question` | NL question text input | AI Reports |
| `#askBtn` | "Ask Local AI" button | AI Reports |
| `#askClaudeBtn` | "Ask Claude" button | AI Reports |
| `#askSpinner` | Full-screen spinner overlay | AI Reports |
| `#report` | Report dropdown | AI Reports + Classic |
| `button.btn-primary` | "Generate Report" button | AI Reports + Classic |
| `iframe[title="HTML report"]` | AI report iframe | AI Reports |
| `#rdlFrame` / `iframe[title="Report"]` | SSRS report iframe | Classic Reports |
| `a.nav-link:has-text("Prompt Log")` | Prompt Log nav link | Layout |
| `a.nav-link:has-text("Classic Reports")` | Classic Reports nav link | Layout |
| `a.nav-link:has-text("AI Reports")` | AI Reports nav link | Layout |
| `#promptLogAccordion .accordion-item` | Log entry groups | Prompt Log |
| `.badge:has-text("Summarize")` | Summarize card badge | Prompt Log |
| `div.border-danger-subtle` | "Before" PHI panel | Prompt Log |
| `div.border-success-subtle` | "After" PHI panel | Prompt Log |

**Ask-button handling**: Clicking an Ask button is a full form navigation (GET `/Reports/AskReport` → 302 back to the hub), not an in-page update. Wait for the navigation and the provenance banner rather than the spinner (the spinner element also exists hidden on the destination page, so a `state='hidden'` wait would pass vacuously):
```python
page.click('#askBtn')
# NB: the hub is the app's default route, so the redirect lands on the ROOT
# URL (/?report=...), not /Reports/HtmlReports — wait for the banner, not a URL.
page.wait_for_selector('div.alert .badge', timeout=90000)   # provenance banner
```
90s matches the .NET HttpClient timeout for brain calls. The banner badge text ("Local LLM" / "Claude" / "Claude (fallback)") is also the signal for the step-6 fallback retry logic.

**Iframe handling**: After an NL query loads, the report renders inside `iframe[title="HTML report"]`. Use `page.frame_locator(...)` to wait for table content to appear, then screenshot the full page. **This wait is a precondition for the Prompt Log steps**: the Summarize entry (with the before/after PHI panels) is only recorded when the iframe actually loads and triggers `/summarize` — navigate to the Prompt Log too early and the newest group contains only a Decode entry.

**Pre-warm**: Send a throwaway query to Ollama before the demo starts to avoid cold model load latency during screenshot capture.

### 4. `demo-recording/orchestrator.py`

Main entry point. Invoked as:
```bash
cd demo-recording
python orchestrator.py
```

**Phase 1 — Service Startup**

1. **FFmpeg check**: Run `ffmpeg -version`, fail fast with install instructions if missing
2. **Ollama**: Start `ollama serve` (subprocess). Poll `http://localhost:11434/api/tags` every 2s, timeout 30s. Run `ollama pull qwen2.5:3b` if model not present
3. **Python brain**: Start `python -m uvicorn ai_report_forge.api:app --host 127.0.0.1 --port 8080` from `ai-report-forge/`. Poll `/health` every 2s, timeout 30s
4. **.NET app**: Start `dotnet run` from `DotNetApp/PatientReports/`. Poll `http://localhost:5282/` every 2s, timeout 60s (first run compiles)
5. **RdlRenderService**: Start `dotnet run` from `DotNetApp/RdlRenderService/`. Poll `http://localhost:5250/` every 2s, timeout 60s. **If this fails, warn and continue** — Classic Reports step will show the styled "service unavailable" page

6. **Claude pre-flight check**: POST `/decode-prompt` with `{"question": "show all patients", "provider": "claude"}`. If the response is UNKNOWN with a "Claude is not configured" / "Claude API error" message, **abort with a clear message** (steps 5–6 depend on a valid `ANTHROPIC_API_KEY` in `ai-report-forge/.env`). A `--skip-claude` flag downgrades instead: step 5 becomes a second local ask (adjusted narration) and step 6 is dropped.
7. **Ollama pre-warm**: send a throwaway `/decode-prompt` (provider local) so the cold model load doesn't land inside a timed demo step.

Port conflict handling: if a port already responds, skip starting that service.

All subprocesses tracked for cleanup in a `finally` block (only processes the orchestrator itself started are killed).

**Phase 2 — Playwright Capture**

1. Ensure Playwright browsers installed: `playwright install chromium`
2. Import and run `playwright_demo.py`
3. Output: `screenshots/step-01.png` through `step-14.png`

**Phase 3 — TTS Generation (edge-tts)**

1. Read `narration.json`
2. For each step: `edge_tts.Communicate(text, voice="en-US-AriaNeural")` → save to `audio/step-NN.mp3`. Note: `Communicate.save()` is a **coroutine** — wrap the loop in `asyncio.run(...)`.
3. Measure each clip's duration via `ffprobe -show_entries format=duration`

edge-tts is free and keyless but **not offline** — it calls Microsoft's TTS endpoint over the network. On locked-down networks (the same VDI that blocks port 8000), fall back to the offline `pyttsx3` (Windows SAPI voices — lower quality, zero network).

Voice choice: `en-US-AriaNeural` is a clear, professional female voice. Alternatives: `en-US-GuyNeural` (male), `en-US-JennyNeural` (conversational).

**Phase 4 — Video Stitching (FFmpeg)**

1. Build FFmpeg concat input file: each screenshot held for (audio_duration + pause_after) seconds
2. Concatenate audio clips with silence gaps into one track
3. Mux image slideshow + audio → `output/demo.mp4`
   - Codec: libx264, pixel format yuv420p (max compatibility)
   - Resolution: 1280×800 (matches Playwright viewport)

**Phase 5 — Cleanup**

- Kill all started subprocesses (Ollama, brain, .NET app, RdlRenderService)
- Print: output file path, duration, file size

---

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Claude key missing/invalid/out of credits (steps 5–6 depend on it) | Pre-flight probe in Phase 1: abort with a clear message, or `--skip-claude` downgrades those steps. **This failure mode is silent otherwise** — the video would narrate success over an error banner |
| Local model non-determinism (step 6 fallback may not trigger) | Check the banner text after the ask; retry up to 3×; if still no fallback, swap in alternate narration for the captured result |
| Ollama slow on first query (cold model load) | Pre-warm with a throwaway decode before demo starts |
| Brain call slow (>90s) | `wait_for_url` timeout matches the .NET HttpClient config |
| Port conflicts (services already running) | Health-check first — skip starting any service whose port already responds |
| FFmpeg not installed | Fail fast with platform-specific install instructions (winget/choco/scoop) |
| edge-tts blocked (needs network) or rate-limited | Retry with backoff; offline fallback via pyttsx3 (Windows SAPI) |
| RdlRenderService won't start (.NET Framework 4.8 required) | Warn and continue — step 14 shows the styled error page, still demo-worthy |
| UI selector breakage after view changes | Selectors use stable IDs (`#question`, `#askBtn`, etc.) from the actual Razor views |

**Deliberate trade-off — screenshots vs. motion**: this plan produces a narrated slideshow (deterministic, easy to retime). Playwright's native video recording (`browser.new_context(record_video_dir=...)`) would capture real motion (typing, spinner, scrolling) at the cost of harder audio alignment. Slideshow chosen for v1; revisit if stakeholders want motion.

---

## Files to Create

All new files in `demo-recording/` at the repo root:

| File | Purpose |
|------|---------|
| `demo-recording/requirements.txt` | pip dependencies (playwright, edge-tts, Pillow) |
| `demo-recording/narration.json` | Step → narration text manifest (14 entries) |
| `demo-recording/playwright_demo.py` | Playwright browser automation script |
| `demo-recording/orchestrator.py` | Main orchestrator (services + capture + TTS + stitch) |

No existing files are modified.

---

## How to Run (Once Built)

```bash
# One-time setup
cd demo-recording
pip install -r requirements.txt
playwright install chromium

# Record the demo (starts all services, captures, generates voiceover, produces MP4)
python orchestrator.py

# Output
# → demo-recording/output/demo.mp4  (~2-3 minutes, 1280×800, with voiceover)
```

---

## Estimated Effort

| Component | Time |
|-----------|------|
| Playwright script (12 steps with waits) | ~2 hours |
| Narration text (14 entries) | ~30 min |
| Orchestrator (service management + TTS + FFmpeg) | ~3 hours |
| Testing and timing adjustments | ~1 hour |
| **Total** | **~1 day** |
