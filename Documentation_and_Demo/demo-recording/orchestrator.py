"""Demo video orchestrator: services → Playwright capture → TTS → MP4.

Usage:
    cd demo-recording
    python orchestrator.py [--skip-capture] [--skip-claude-check]

--skip-capture reuses existing screenshots/ (re-stitch after narration edits).
Requires: ffmpeg on PATH, `pip install -r requirements.txt`,
`python -m playwright install chromium`.
"""

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import edge_tts

def _find_root(start: Path) -> Path:
    """Walk up to the repo root (robust to where this folder lives)."""
    d = start
    for _ in range(6):
        if (d / "HTMLReportsFolder").is_dir() and (d / "DotNetApp").is_dir():
            return d
        d = d.parent
    return start


HERE = Path(__file__).parent
ROOT = _find_root(HERE)
SCREENSHOTS = HERE / "screenshots"
AUDIO = HERE / "audio"
OUTPUT = HERE / "output"
VOICE = "en-US-AriaNeural"

SERVICES = [
    ("Ollama", "http://localhost:11434/api/tags", ["ollama", "serve"], None, 30),
    ("Python brain", "http://127.0.0.1:8080/health",
     [sys.executable, "-m", "uvicorn", "ai_report_forge.api:app", "--host", "127.0.0.1", "--port", "8080"],
     ROOT / "ai-report-forge", 30),
    (".NET app", "http://localhost:5282/",
     ["dotnet", "run", "--no-launch-profile", "--urls", "http://localhost:5282"],
     ROOT / "DotNetApp" / "PatientReports", 90),
    ("RdlRenderService", "http://localhost:5250/RdlView?report=patient",
     ["dotnet", "run"], ROOT / "DotNetApp" / "RdlRenderService", 90),
]


def url_ok(url: str, timeout: float = 3) -> bool:
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except Exception as exc:  # noqa: BLE001 — any HTTP status means the port answers
        return getattr(exc, "code", None) is not None


def ffmpeg_or_die() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        sys.exit("ffmpeg not found on PATH. Install: winget install Gyan.FFmpeg "
                 "(or choco install ffmpeg / scoop install ffmpeg), then reopen the terminal.")
    return exe


def start_services() -> list[subprocess.Popen]:
    started = []
    for name, health, cmd, cwd, timeout in SERVICES:
        if url_ok(health):
            print(f"[services] {name}: already running")
            continue
        print(f"[services] starting {name}...")
        try:
            proc = subprocess.Popen(
                cmd, cwd=cwd,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            if name == "RdlRenderService":
                print(f"[services] WARNING: could not start {name} — Classic step will show the error page")
                continue
            raise
        started.append(proc)
        deadline = time.time() + timeout
        while time.time() < deadline:
            if url_ok(health):
                print(f"[services] {name}: up")
                break
            time.sleep(2)
        else:
            if name == "RdlRenderService":
                print(f"[services] WARNING: {name} not healthy — continuing (Classic step shows error page)")
            else:
                sys.exit(f"[services] {name} failed to become healthy within {timeout}s")
    return started


def claude_preflight() -> None:
    """Steps 5–6 depend on a valid ANTHROPIC_API_KEY in ai-report-forge/.env."""
    req = urllib.request.Request(
        "http://127.0.0.1:8080/decode-prompt",
        data=json.dumps({"question": "show all patients", "provider": "claude"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.load(resp)
    msg = body.get("message") or ""
    if body.get("report") == "UNKNOWN" and ("Claude" in msg):
        sys.exit(f"[preflight] Claude is not usable: {msg}\n"
                 "Fix ANTHROPIC_API_KEY in ai-report-forge/.env and restart the brain, "
                 "or rerun with --skip-claude-check (steps 5-6 will show errors).")
    print("[preflight] Claude decode OK")


def generate_tts(steps: list[dict]) -> None:
    AUDIO.mkdir(exist_ok=True)

    async def synth() -> None:
        for s in steps:
            out = AUDIO / f"{s['filename']}.mp3"
            print(f"[tts] {s['filename']}: {s['narration'][:50]}...")
            await edge_tts.Communicate(s["narration"], VOICE).save(str(out))

    asyncio.run(synth())


def clip_duration(ffprobe: str, path: Path) -> float:
    out = subprocess.check_output(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        text=True,
    )
    return float(out.strip())


def stitch(ffmpeg: str, steps: list[dict], name: str = "demo") -> Path:
    OUTPUT.mkdir(exist_ok=True)
    ffprobe = shutil.which("ffprobe") or str(Path(ffmpeg).parent / "ffprobe")

    # Per step: pad the audio clip with trailing silence, pair it with the
    # screenshot as one segment, then concat all segments.
    segments = []
    for i, s in enumerate(steps):
        img = SCREENSHOTS / f"{s['filename'].replace('-alt', '')}.png"
        aud = AUDIO / f"{s['filename']}.mp3"
        dur = clip_duration(ffprobe, aud) + float(s.get("pause_after", 0.5))
        seg = OUTPUT / f"seg-{i:02d}.mp4"
        subprocess.run(
            [ffmpeg, "-y", "-loglevel", "error",
             "-loop", "1", "-i", str(img), "-i", str(aud),
             "-t", f"{dur:.2f}",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
             "-crf", "18", "-preset", "medium",       # crisp text (2x screenshots downscaled with lanczos)
             "-vf", "scale=1920:1200:flags=lanczos",
             "-c:a", "aac", "-af", "apad",            # pad audio to segment length (bounded by -t)
             seg],
            check=True,
        )
        segments.append(seg)
        print(f"[stitch] segment {i + 1}/{len(steps)} ({dur:.1f}s)")

    concat_file = OUTPUT / "concat.txt"
    concat_file.write_text("".join(f"file '{s.name}'\n" for s in segments), encoding="ascii")
    final = OUTPUT / f"{name}.mp4"
    subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(concat_file), "-c", "copy", str(final)],
        check=True, cwd=OUTPUT,
    )
    for s in segments:
        s.unlink()
    concat_file.unlink()
    return final


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-capture", action="store_true")
    parser.add_argument("--skip-claude-check", action="store_true")
    parser.add_argument("--name", default="demo", help="output file name (without .mp4)")
    args = parser.parse_args()

    ffmpeg = ffmpeg_or_die()
    manifest = json.loads((HERE / "narration.json").read_text(encoding="utf-8"))

    started: list[subprocess.Popen] = []
    try:
        started = start_services()
        if not args.skip_claude_check:
            claude_preflight()

        if args.skip_capture:
            meta = {"fallback_variant": "step-09"}
            print("[capture] skipped (reusing screenshots/)")
        else:
            sys.path.insert(0, str(HERE))
            from playwright_demo import run as run_capture
            meta = run_capture()

        # Pick the right fallback-step narration variant; drop the other.
        steps = [s for s in manifest
                 if not s["filename"].startswith("step-09") or s["filename"] == meta["fallback_variant"]]
        steps.sort(key=lambda s: s["step"])

        generate_tts(steps)
        final = stitch(ffmpeg, steps, args.name)

        ffprobe = shutil.which("ffprobe") or str(Path(ffmpeg).parent / "ffprobe")
        size_mb = final.stat().st_size / 1e6
        total = sum(clip_duration(ffprobe, AUDIO / f"{s['filename']}.mp3")
                    + s.get("pause_after", 0.5) for s in steps)
        print(f"\n[done] {final}  ({total:.0f}s, {size_mb:.1f} MB)")
    finally:
        for proc in started:
            proc.terminate()


if __name__ == "__main__":
    main()
