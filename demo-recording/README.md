# Demo Recording Pipeline

Produces a narrated demo video (`output/demo.mp4`, ~3:35, 1280×800) of the full
AI Report Forge walkthrough: 17 steps × (screenshot + edge-tts voiceover), stitched
with FFmpeg. Design/plan: [`../docs/demo-recording-plan.md`](../docs/demo-recording-plan.md).

## Run

```bash
pip install -r requirements.txt
python -m playwright install chromium
# ffmpeg on PATH (winget install Gyan.FFmpeg) and ANTHROPIC_API_KEY in ai-report-forge/.env

python orchestrator.py
```

The orchestrator health-checks and auto-starts any of the four services that aren't
already running, pre-flights the Claude key (steps 5–6 depend on it; `--skip-claude-check`
to override), runs the headed Playwright walkthrough, generates narration, and stitches
`output/demo.mp4`. Re-stitch without re-capturing (e.g. after narration edits):
`python orchestrator.py --skip-capture`.

## Notes

- **Headed browser required** — the Classic/SSRS report is a PDF in an iframe; headless
  Chromium renders it blank. Don't minimize the browser window during capture.
- **Restart the brain first** for a clean Prompt Log (the log page appears in the video).
- Step 9 (Claude fallback) retries candidate prompts up to 3× each; if the local model
  keeps decoding them, the video automatically uses alternate narration that matches
  what was actually captured (`step-09-alt` in `narration.json`).
- Voice: `en-US-AriaNeural` (change `VOICE` in `orchestrator.py`; edge-tts needs network).
