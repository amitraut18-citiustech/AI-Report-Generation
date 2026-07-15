"""Turn the AI-Report-Forge.html slide deck into a narrated MP4.

Screenshots each of the 14 slides (headed not needed — pure HTML), synthesizes
an edge-tts voiceover per slide, and stitches a ~3-4 min 1920x1200 video beside
the deck: Documentation_and_Demo/AI-Report-Forge.mp4.

Run (from demo-recording/, with ffmpeg on PATH):
    .venv\\Scripts\\python -u ppt_video.py
"""

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

import edge_tts
from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
DECK = HERE.parent / "AI-Report-Forge.html"          # the slide deck
FINAL = HERE.parent / "AI-Report-Forge.mp4"          # output beside the deck
SLIDES = HERE / "ppt_slides"
AUDIO = HERE / "ppt_audio"
VOICE = "en-US-AriaNeural"
VIEWPORT = {"width": 1280, "height": 800}
DSF = 2               # 2x = sharp screenshots
PAUSE_AFTER = 0.7     # trailing silence per slide (s)

# One narration per slide, in order (14 slides).
NARRATION = [
    # 1 cover
    "AI Report Forge — the Report Migrator plugin. This walkthrough covers both phases: "
    "phase one, a build-time plugin that migrates legacy SSRS reports into web-native HTML; "
    "and phase two, serving them at runtime with natural-language querying and a local model.",
    # 2 problem
    "The problem. Today, every new or changed report is an IT ticket. SSRS and Crystal reports "
    "are authored as proprietary definitions by developers, deployed to a report server, and "
    "produce static, PDF-centric output that business users cannot self-serve. The goal is to "
    "replace that for on-demand tabular and summary reports, reusing the existing dot-NET data layer.",
    # 3 issues
    "Why SSRS hurts. It needs a report server or the ReportViewer engine, which cannot even run "
    "in-process on modern dot-NET — so a separate dot-NET Framework service is needed just to render it. "
    "The report definitions are verbose XML, hard to diff, review or restyle, and the output is not web-native.",
    # 4 solution
    "The solution: HTML-based reports. Self-contained HTML and JavaScript templates that render from a "
    "single injected data object. They are web-native, responsive, printable, version-controlled in git, "
    "and reuse the same dot-NET data layer. An AI plugin generates them from the existing reports.",
    # 5 plugin structure
    "Phase one is a Claude Code plugin. One skill orchestrates three agents — a researcher that analyzes "
    "the report, a migrator that generates the HTML, and a schema mapper — plus slash commands. Anything "
    "application-specific lives in a shared context file, so the plugin itself stays generic and reusable.",
    # 6 output
    "The plugin produces version-controlled artifacts: a reviewable thought file per report, the "
    "self-contained HTML template set, and a database schema map with PHI markers — all committed to "
    "the repository and consumed at runtime.",
    # 7 migration pipeline
    "The migration pipeline. The researcher reads the legacy report into a thought file; a developer "
    "reviews and approves it; then the migrator generates the HTML. The two sub-phases are separated on "
    "purpose — a misread rule is cheap to fix in the thought file, and expensive to debug in generated code.",
    # 8 impact
    "What changes, and what stays the same. The database, the data-access layer, the business logic and "
    "filtering, controllers and authentication — all unchanged. Only the presentation layer is swapped: "
    "SSRS rendering becomes an HTML template populated with data. SSRS is replaced without disrupting the app.",
    # 9 phase 2 architecture
    "Phase two brings the reports to life at runtime. The dot-NET app calls a Python brain, which uses a "
    "local model, Ollama, to decode questions, with Claude as an anonymized cloud fallback. Data comes from "
    "SQLite through EF Core; reports render as HTML, or, for parity, as the real RDL definition.",
    # 10 NL flow
    "A natural-language query flows like this: the user asks a question; the brain decodes it into a report "
    "plus table-qualified filters; the dot-NET app applies those filters with EF Core; the brain summarizes "
    "the results; and the HTML template renders. Asking for patient data at Austin General filters to just "
    "the patients at that facility.",
    # 11 brain
    "The brain is a FastAPI service with three endpoints — decode-prompt, summarize, and health. At startup "
    "it loads the report catalog, the schema mapping, and the PHI markers. The local Ollama model is primary; "
    "Claude is used only as a fallback, and only on anonymized data.",
    # 12 PHI
    "Privacy is central. PHI never leaves the server in the clear. Rows are anonymized — pseudonyms, age "
    "ranges, redaction — before any model call, and re-mapped locally afterward. The query spec is signed and "
    "encrypted, only allowlisted columns are filterable, and off-topic requests fail closed.",
    # 13 rendering
    "Two render paths share one data layer. The HTML template — the SSRS replacement — with an AI narrative "
    "and interactive filters. And the real RDL rendered to PDF for legacy parity, with a download button. The "
    "same data feeds both, proving the HTML report is a drop-in replacement.",
    # 14 run
    "Running the proof of concept is four processes: Ollama, the Python brain, the RDL render service, and the "
    "dot-NET app. It is local, private, needs no report server, and everything lives in git. That is AI Report Forge.",
]


def capture() -> int:
    SLIDES.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=DSF)
        page.goto(DECK.as_uri())
        page.wait_for_selector(".slide.active")
        page.wait_for_load_state("networkidle")
        # Kill the fade/transition so every slide is fully painted at screenshot
        # time (the first slide was catching a mid-fade / pre-paint frame).
        page.add_style_tag(content="*{animation:none !important; transition:none !important}")
        page.evaluate("() => (document.fonts ? document.fonts.ready.then(() => true) : true)")
        page.wait_for_timeout(700)  # initial paint settle (cover gradient + hero text)
        n = page.evaluate("document.querySelectorAll('.slide').length")
        for i in range(n):
            page.wait_for_timeout(450)
            page.screenshot(path=str(SLIDES / f"slide-{i:02d}.png"))
            print(f"  captured slide {i + 1}/{n}")
            if i < n - 1:
                page.click("#next")
        browser.close()
    return n


def generate_tts(count: int) -> None:
    AUDIO.mkdir(exist_ok=True)

    async def synth() -> None:
        for i in range(count):
            out = AUDIO / f"aud-{i:02d}.mp3"
            if out.exists() and out.stat().st_size > 0:
                print(f"  tts slide {i + 1}: reusing existing audio")
                continue
            print(f"  tts slide {i + 1}: {NARRATION[i][:48]}...")
            await edge_tts.Communicate(NARRATION[i], VOICE).save(str(out))

    asyncio.run(synth())


def clip_duration(ffprobe: str, path: Path) -> float:
    out = subprocess.check_output(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)], text=True)
    return float(out.strip())


def stitch(ffmpeg: str, ffprobe: str, n: int) -> None:
    FINAL.parent.mkdir(exist_ok=True)
    segs = []
    for i in range(n):
        img = SLIDES / f"slide-{i:02d}.png"
        aud = AUDIO / f"aud-{i:02d}.mp3"
        dur = clip_duration(ffprobe, aud) + PAUSE_AFTER
        seg = HERE / f"ppt-seg-{i:02d}.mp4"
        subprocess.run(
            [ffmpeg, "-y", "-loglevel", "error",
             "-loop", "1", "-i", str(img), "-i", str(aud), "-t", f"{dur:.2f}",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
             "-crf", "18", "-preset", "medium",
             "-vf", "scale=1920:1200:flags=lanczos",
             "-c:a", "aac", "-af", "apad", str(seg)],
            check=True)
        segs.append(seg)
        print(f"  segment {i + 1}/{n} ({dur:.1f}s)")

    concat = HERE / "ppt-concat.txt"
    concat.write_text("".join(f"file '{s.name}'\n" for s in segs), encoding="ascii")
    subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(concat), "-c", "copy", str(FINAL)], check=True, cwd=HERE)
    for s in segs:
        s.unlink()
    concat.unlink()


def main() -> None:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        sys.exit("ffmpeg/ffprobe not on PATH")
    if not DECK.exists():
        sys.exit(f"deck not found: {DECK}")

    print("[capture] screenshotting slides...")
    n = capture()
    if n != len(NARRATION):
        print(f"[warn] {n} slides but {len(NARRATION)} narrations — using min")
        n = min(n, len(NARRATION))
    print("[tts] synthesizing voiceover...")
    generate_tts(n)
    print("[stitch] building video...")
    stitch(ffmpeg, ffprobe, n)

    total = sum(clip_duration(ffprobe, AUDIO / f"aud-{i:02d}.mp3") + PAUSE_AFTER for i in range(n))
    print(f"\n[done] {FINAL}  ({total:.0f}s, {FINAL.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
