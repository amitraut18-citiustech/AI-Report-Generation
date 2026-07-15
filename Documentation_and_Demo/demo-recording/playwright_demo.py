"""Playwright walkthrough for the demo video: 17 steps, numbered screenshots.

Steps 1-3 show the Phase-1 migration artifacts (.rdl → thought file → HTML
template) rendered as styled code viewers; steps 4-17 drive the live app.

Runs headed — the Classic/SSRS report is a PDF in an iframe and headless
Chromium has no PDF viewer. Selector/wait patterns proven in
presentation/evidence/capture_evidence.py.

Returns metadata the orchestrator needs (which narration variant step 9 uses).
"""

import html
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:5282"


def _find_root(start: Path) -> Path:
    """Walk up to the repo root (robust to where this folder lives)."""
    d = start
    for _ in range(6):
        if (d / "HTMLReportsFolder").is_dir() and (d / "DotNetApp").is_dir():
            return d
        d = d.parent
    return start


ROOT = _find_root(Path(__file__).resolve().parent)
SCREENSHOTS = Path(__file__).parent / "screenshots"
VIEWPORT = {"width": 1280, "height": 800}
DEVICE_SCALE = 2  # 2x renders sharp (2560x1600) screenshots — fixes the blur
ASK_TIMEOUT = 120_000

# Candidates in preference order; the local model is non-deterministic, so we
# try each a few times and fall back to alternate narration if it keeps coping.
FALLBACK_QUESTIONS = [
    "which sheet lists the folks who got cells from a donor other than themselves",
    "pull up the sheet for the lady from the dallas clinic",
]

# Step 3 shows the generated HTML template as a code viewer (the actual output
# artifact). Steps 1-2 are graphical intros (plugin structure + artifact lineage).
STEP3_ARTIFACT = (
    ROOT / "HTMLReportsFolder" / "transplant_event.html",
    "Phase 1 — the generated report", "Self-contained HTML template (renders from window.REPORT_DATA)",
)

_VIEWER_CSS = """
body{margin:0;font-family:'Segoe UI',sans-serif;background:#f4f6fa}
header{background:#1f3864;color:#fff;padding:18px 28px}
header h1{margin:0;font-size:1.4rem} header p{margin:4px 0 0;color:#c7d4ee;font-size:.95rem}
.path{background:#dbe5f1;color:#1f3864;padding:6px 28px;font-family:Consolas,monospace;font-size:.85rem}
pre{margin:0;padding:20px 28px;font-family:Consolas,monospace;font-size:.78rem;line-height:1.45;
    color:#1b2330;background:#fff;white-space:pre-wrap;word-break:break-all}
"""


def artifact_viewer(src: Path, title: str, subtitle: str, max_lines: int = 46) -> str:
    """Write a styled, escaped code-viewer page for an artifact; return file:// URL."""
    lines = src.read_text(encoding="utf-8", errors="replace").splitlines()
    body = "\n".join(lines[:max_lines])
    if len(lines) > max_lines:
        body += f"\n… ({len(lines) - max_lines} more lines)"
    page = (f"<!doctype html><html><head><meta charset='utf-8'><style>{_VIEWER_CSS}</style></head>"
            f"<body><header><h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></header>"
            f"<div class='path'>{html.escape(str(src.relative_to(ROOT)))}</div>"
            f"<pre>{html.escape(body)}</pre></body></html>")
    out = Path(tempfile.gettempdir()) / f"artifact-{src.stem}.html"
    out.write_text(page, encoding="utf-8")
    return out.as_uri()


_GRAPHIC_CSS = """
*{box-sizing:border-box}
body{margin:0;font-family:'Segoe UI',system-ui,sans-serif;background:linear-gradient(135deg,#eef2f8,#f7f9fc);
     color:#1b2330;height:100vh;display:flex;flex-direction:column;justify-content:center;padding:40px 56px}
h1{color:#1f3864;margin:0 0 4px;font-size:2rem}
.sub{color:#5b6675;margin:0 0 28px;font-size:1.05rem}
.tree{font-family:Consolas,'Cascadia Code',monospace;font-size:1rem;line-height:1.7;background:#0f1b2d;color:#e7eefb;
      border-radius:14px;padding:22px 26px;white-space:pre;box-shadow:0 12px 30px rgba(31,56,100,.18)}
.tree .c{color:#9fb2d4}.tree .f{color:#8fe3d1;font-weight:600}
.pipe{display:flex;gap:12px;align-items:stretch;margin-top:22px;flex-wrap:wrap}
.pstep{flex:1 1 150px;background:#fff;border:1px solid #d7dce5;border-left:5px solid #2e5496;border-radius:12px;
       padding:14px 16px;box-shadow:0 6px 16px rgba(31,56,100,.08)}
.pstep .n{font-size:.72rem;font-weight:700;letter-spacing:.08em;color:#2e5496}
.pstep b{display:block;margin:.2em 0;font-size:1.05rem}
.pstep span{color:#5b6675;font-size:.9rem}
.pstep.review{border-left-color:#0f766e}.pstep.review .n{color:#0f766e}
.arrow{align-self:center;font-size:1.6rem;color:#2e5496;font-weight:800}
.cards{display:flex;gap:0;align-items:stretch;margin-top:10px;flex-wrap:nowrap}
.card{flex:1;background:#fff;border:1px solid #d7dce5;border-radius:16px;padding:22px;text-align:center;
      box-shadow:0 10px 24px rgba(31,56,100,.10)}
.badge{display:inline-block;font-family:Consolas,monospace;font-weight:700;font-size:1.15rem;color:#fff;
       padding:.3em .8em;border-radius:10px;margin-bottom:12px}
.b-rdl{background:#b02a37}.b-md{background:#0f766e}.b-html{background:#2e5496}
.card h3{margin:.2em 0;color:#1f3864;font-size:1.15rem}
.card p{color:#5b6675;font-size:.92rem;margin:.3em 0 0;line-height:1.4}
.flow{font-size:2rem;color:#2e5496;font-weight:800;align-self:center;padding:0 6px}
.cap{margin-top:22px;color:#5b6675;font-size:.98rem;text-align:center}
"""


def _write_graphic(name: str, inner: str) -> str:
    page = (f"<!doctype html><html><head><meta charset='utf-8'>"
            f"<style>{_GRAPHIC_CSS}</style></head><body>{inner}</body></html>")
    out = Path(tempfile.gettempdir()) / f"graphic-{name}.html"
    out.write_text(page, encoding="utf-8")
    return out.as_uri()


def plugin_structure_viewer() -> str:
    """Step 1 graphic: the Phase-1 Claude Code plugin structure + pipeline."""
    tree = (
        ".claude/\n"
        "├── skills/report-forge/\n"
        "│   ├── <span class='f'>SKILL.md</span>          <span class='c'># orchestrates research → migrate</span>\n"
        "│   └── references/          <span class='c'># thought-file / html / schema templates</span>\n"
        "├── agents/\n"
        "│   ├── <span class='f'>report-researcher.md</span>   <span class='c'># .rdl → thought file</span>\n"
        "│   ├── <span class='f'>report-migrator.md</span>     <span class='c'># thought file → HTML+JS+md</span>\n"
        "│   └── <span class='f'>schema-mapper.md</span>       <span class='c'># DB → schema + PHI markers</span>\n"
        "└── commands/                <span class='c'># /report-research, /report-migrate</span>"
    )
    inner = (
        "<h1>Phase 1 — the migration plugin</h1>"
        "<p class='sub'>A Claude Code plugin: one skill orchestrating three agents.</p>"
        f"<div class='tree'>{tree}</div>"
        "<div class='pipe'>"
        "<div class='pstep'><span class='n'>1a · RESEARCH</span><b>report-researcher</b><span>legacy report → thought file</span></div>"
        "<div class='arrow'>→</div>"
        "<div class='pstep review'><span class='n'>CHECKPOINT</span><b>Human review</b><span>approve the logic</span></div>"
        "<div class='arrow'>→</div>"
        "<div class='pstep'><span class='n'>1b · MIGRATE</span><b>report-migrator</b><span>thought file → HTML report</span></div>"
        "</div>"
    )
    return _write_graphic("plugin-structure", inner)


def artifact_lineage_viewer() -> str:
    """Step 2 graphic: one report as three versioned artifacts (.rdl → .md → .html)."""
    inner = (
        "<h1>Phase 1 — one report, three artifacts</h1>"
        "<p class='sub'>The plugin turns a legacy report definition into version-controlled files.</p>"
        "<div class='cards'>"
        "<div class='card'><span class='badge b-rdl'>.rdl</span><h3>SSRS definition</h3>"
        "<p>The legacy report — verbose XML, developer-authored, needs a report server.</p></div>"
        "<div class='flow'>→</div>"
        "<div class='card'><span class='badge b-md'>.md</span><h3>Thought file</h3>"
        "<p>Human-reviewed analysis of data, business logic, parameters &amp; layout.</p></div>"
        "<div class='flow'>→</div>"
        "<div class='card'><span class='badge b-html'>.html</span><h3>HTML template</h3>"
        "<p>Self-contained report that renders from an injected data object — a file in git.</p></div>"
        "</div>"
        "<p class='cap'>Reviewable diffs · no report server · generated by the Claude Code plugin</p>"
    )
    return _write_graphic("artifact-lineage", inner)


def ask(page, question: str, button_id: str) -> None:
    page.goto(f"{BASE}/Reports/HtmlReports")
    page.fill("#question", question)
    page.click(f"#{button_id}")
    # Ask navigates back to the hub at the ROOT url (default route) — wait for
    # the provenance/error banner, not a URL.
    page.wait_for_selector("div.alert", timeout=ASK_TIMEOUT)


def banner_text(page) -> str:
    return page.locator("div.alert").first.inner_text()


def wait_report_iframe(page) -> None:
    # The report page runs an inline LLM /summarize before returning, which is slow
    # on CPU; and a fallback query can yield an empty-state (no table). Wait
    # generously, but don't abort the whole capture if the table never appears —
    # screenshot whatever rendered (banner + report frame).
    frame = page.frame_locator('iframe[title="HTML report"]')
    try:
        frame.locator("table").first.wait_for(timeout=150_000)
    except Exception:
        print("  (report table not visible in time — capturing current state)")
    page.wait_for_timeout(2_000)  # let /summarize land in the prompt log


def shot(page, name: str) -> None:
    SCREENSHOTS.mkdir(exist_ok=True)
    page.screenshot(path=str(SCREENSHOTS / f"{name}.png"))
    print(f"  captured {name}.png")


def run() -> dict:
    """Returns {'fallback_variant': 'step-09' | 'step-09-alt'}."""
    meta = {"fallback_variant": "step-09"}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=DEVICE_SCALE)
        # Ask buttons trigger a slow local-LLM decode; the click auto-waits for the
        # resulting navigation, so the nav timeout must cover cold-start inference.
        page.set_default_navigation_timeout(ASK_TIMEOUT)
        page.set_default_timeout(60_000)

        print("step 1: plugin structure (graphic)")
        page.goto(plugin_structure_viewer())
        shot(page, "step-01")

        print("step 2: artifact lineage (graphic)")
        page.goto(artifact_lineage_viewer())
        shot(page, "step-02")

        print("step 3: generated HTML template (code viewer)")
        src, title, subtitle = STEP3_ARTIFACT
        page.goto(artifact_viewer(src, title, subtitle))
        shot(page, "step-03")

        print("step 4: landing page")
        page.goto(f"{BASE}/Reports/HtmlReports")
        page.wait_for_selector("#question")
        shot(page, "step-04")

        print("step 5: question typed")
        page.fill("#question", "Show me patients at Austin General")
        shot(page, "step-05")

        print("step 6: ask local AI")
        page.click("#askBtn")
        page.wait_for_selector("div.alert", timeout=ASK_TIMEOUT)
        wait_report_iframe(page)
        shot(page, "step-06")

        print("step 7: AI summary in view")
        page.frame_locator('iframe[title="HTML report"]').locator("table").first.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        shot(page, "step-07")

        print("step 8: ask Claude")
        ask(page, "Show female patients at Austin General Hospital", "askClaudeBtn")
        wait_report_iframe(page)
        shot(page, "step-08")

        print("step 9: automatic fallback (up to 3 attempts per candidate prompt)")
        got_fallback = False
        for question in FALLBACK_QUESTIONS:
            for attempt in range(3):
                ask(page, question, "askBtn")
                if "fallback" in banner_text(page).lower():
                    got_fallback = True
                    break
                print(f"  local model decoded it (attempt {attempt + 1}) — retrying")
            if got_fallback:
                break
        if not got_fallback:
            meta["fallback_variant"] = "step-09-alt"
            print("  fallback did not trigger — using alternate narration")
        wait_report_iframe(page)
        shot(page, "step-09")

        print("step 10: MRN fail-closed")
        ask(page, "show patient with MRN-00003", "askBtn")
        wait_report_iframe(page)
        shot(page, "step-10")

        print("step 11: prompt log routing")
        page.goto(f"{BASE}/Reports/PromptLog")
        page.wait_for_selector("#promptLogAccordion .accordion-item", timeout=15_000)
        shot(page, "step-11")

        print("step 12: PHI before/after")
        groups = page.locator("#promptLogAccordion .accordion-item")
        for i in range(groups.count()):
            g = groups.nth(i)
            if "Austin General" in g.locator(".accordion-button").inner_text():
                g.locator(".accordion-button").click()
                break
        page.wait_for_timeout(800)
        before = page.locator(".accordion-collapse.show div.border-danger-subtle").first
        before.wait_for(timeout=10_000)
        before.scroll_into_view_if_needed()
        shot(page, "step-12")

        print("step 13: dropdown selection")
        page.goto(f"{BASE}/Reports/HtmlReports")
        page.select_option("#report", "transplant")
        shot(page, "step-13")

        print("step 14: transplant report via dropdown")
        # NB: the dropdown form's action renders as the ROOT url (default
        # route), so don't select by form action.
        page.click('button:has-text("Generate Report")')
        page.wait_for_selector('iframe[title="HTML report"]', timeout=30_000)
        page.frame_locator('iframe[title="HTML report"]').locator("table").first.wait_for(timeout=30_000)
        shot(page, "step-14")

        print("step 15: clinical summary")
        page.select_option("#report", "clinical")
        page.click('button:has-text("Generate Report")')
        page.wait_for_selector('iframe[title="HTML report"]', timeout=30_000)
        page.frame_locator('iframe[title="HTML report"]').locator("table").first.wait_for(timeout=60_000)
        shot(page, "step-15")

        print("step 16: classic SSRS page")
        page.click('a.nav-link:has-text("Classic Reports")')
        page.wait_for_selector("#report")
        shot(page, "step-16")

        print("step 17: SSRS report rendered")
        page.select_option("#report", "patient")
        page.click("button.btn-primary")
        page.wait_for_selector("#rdlFrame", timeout=30_000)
        page.wait_for_timeout(8_000)  # PDF render inside the iframe
        shot(page, "step-17")

        browser.close()
    return meta


if __name__ == "__main__":
    print(run())
