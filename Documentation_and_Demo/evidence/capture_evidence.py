"""Capture run-evidence screenshots for the hackathon submission pack.

Prereqs: all four services running (see docs/quick_start.md), a valid
ANTHROPIC_API_KEY in ai-report-forge/.env, and `pip install playwright`
+ `python -m playwright install chromium`.

Usage:  python capture_evidence.py
Output: PNGs in this folder (presentation/evidence/).
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:5282"
OUT = Path(__file__).parent
VIEWPORT = {"width": 1280, "height": 800}
ASK_TIMEOUT = 120_000  # brain decode can take a while on CPU


def ask(page, question: str, button_id: str) -> None:
    """Type a question, click an Ask button, wait for the answer banner."""
    page.goto(f"{BASE}/Reports/HtmlReports")
    page.fill("#question", question)
    page.click(f"#{button_id}")
    # Ask is a full navigation back to the hub (served at the root URL — it is
    # the default route). The provenance banner (or an error banner) marks the
    # answer's arrival; don't match on URL.
    page.wait_for_selector("div.alert", timeout=ASK_TIMEOUT)


def banner_text(page) -> str:
    return page.locator("div.alert").first.inner_text()


def wait_report_iframe(page) -> None:
    """Wait for the report iframe to finish rendering (also triggers /summarize)."""
    frame = page.frame_locator('iframe[title="HTML report"]')
    frame.locator("table").first.wait_for(timeout=60_000)
    # Give the summarize round-trip a moment to land in the prompt log.
    page.wait_for_timeout(2_000)


def shot(page, name: str) -> None:
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=False)
    print(f"  captured {name}.png")


def main() -> None:
    with sync_playwright() as p:
        # Headed: the Classic (SSRS) report renders as a PDF inside an iframe,
        # and headless Chromium has no PDF viewer (blank frame).
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport=VIEWPORT)

        print("1/7 local ask (banner + filters + table + AI summary)")
        ask(page, "Show me patients at Austin General", "askBtn")
        wait_report_iframe(page)
        shot(page, "01-local-ask-report")

        print("2/7 direct Ask Claude")
        ask(page, "Show female patients at Austin General Hospital", "askClaudeBtn")
        wait_report_iframe(page)
        shot(page, "02-ask-claude-report")

        print("3/7 automatic Claude fallback (retrying until it triggers)")
        for attempt in range(3):
            ask(page, "which sheet lists the folks who got cells from a donor other than themselves", "askBtn")
            if "fallback" in banner_text(page).lower():
                break
            print(f"  local model decoded it (attempt {attempt + 1}) — retrying")
        wait_report_iframe(page)
        shot(page, "03-claude-fallback-banner")

        print("4/7 fail-closed PHI probe (MRN)")
        ask(page, "show patient with MRN-00003", "askBtn")
        wait_report_iframe(page)
        shot(page, "04-mrn-fail-closed")

        print("5/7 prompt log — routing chains (newest group expanded)")
        page.goto(f"{BASE}/Reports/PromptLog")
        page.wait_for_selector("#promptLogAccordion .accordion-item", timeout=15_000)
        shot(page, "05-prompt-log-routing")

        print("6/7 prompt log — PHI before/after panels")
        # Open the group for the step-1 local ask (it has a Summarize card) and
        # scroll its before-panel into view.
        groups = page.locator("#promptLogAccordion .accordion-item")
        for i in range(groups.count()):
            group = groups.nth(i)
            if "Austin General" in group.locator(".accordion-button").inner_text():
                group.locator(".accordion-button").click()
                break
        page.wait_for_timeout(800)  # accordion animation
        # Scope to the currently-expanded group — a page-wide .first can match
        # a hidden panel inside a collapsed group.
        before = page.locator(".accordion-collapse.show div.border-danger-subtle").first
        before.wait_for(timeout=10_000)
        before.scroll_into_view_if_needed()
        shot(page, "06-phi-before-after")

        print("7/7 classic SSRS report")
        page.goto(f"{BASE}/Reports/Index?report=patient")
        page.wait_for_selector("#rdlFrame", timeout=30_000)
        # The RDL service can take several seconds (first render compiles the
        # report); wait generously so the PDF is fully painted, not half-loaded.
        page.wait_for_timeout(8_000)
        shot(page, "07-classic-ssrs-report")

        browser.close()
    print(f"\nDone — screenshots in {OUT}")


if __name__ == "__main__":
    main()
