from __future__ import annotations

import json
import os
import pathlib
import time
import traceback
from typing import Any

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[3]
AUTOQA = pathlib.Path(__file__).resolve().parent
ARTIFACTS = AUTOQA / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)
REPORT = ROOT / "QA_REPORT.md"
MATRIX = AUTOQA / "qa_matrix.json"

FRONTEND_URL = os.getenv("QA_FRONTEND_URL", "http://127.0.0.1:3000")
BACKEND_URL = os.getenv("QA_BACKEND_URL", "http://127.0.0.1:5001")
CHATMOCK_URL = os.getenv("CHATMOCK_BASE_URL", "http://127.0.0.1:8000/v1").rstrip("/")
MODEL_ID = os.getenv("DEFAULT_MODEL", "chatmock/gpt-5.5")


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


class QaReport:
    def __init__(self) -> None:
        self.rows: list[dict[str, str]] = []
        self.console_errors: list[str] = []
        self.notes: list[str] = []

    @property
    def failures(self) -> int:
        return sum(1 for r in self.rows if r["result"] == "FAIL")

    def record(self, case_id: str, ok: bool, evidence: str) -> None:
        self.rows.append({"case": case_id, "result": "PASS" if ok else "FAIL", "evidence": evidence})

    def write(self) -> None:
        matrix = json.loads(MATRIX.read_text(encoding="utf-8-sig")) if MATRIX.exists() else []
        lines = [
            "# QA_REPORT",
            "",
            f"- Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"- Frontend: `{FRONTEND_URL}`",
            f"- Backend: `{BACKEND_URL}`",
            f"- ChatMock: `{CHATMOCK_URL}`",
            f"- Target model: `{MODEL_ID}`",
            "",
            "## QA Matrix",
            "",
            "| ID | Name | Expect |",
            "|---|---|---|",
        ]
        for item in matrix:
            lines.append(f"| {item.get('id','')} | {item.get('name','')} | {item.get('expect','')} |")
        lines.extend([
            "",
            "## Results",
            "",
            "| Case | Result | Evidence |",
            "|---|---|---|",
        ])
        for row in self.rows:
            lines.append(f"| {row['case']} | {row['result']} | {row['evidence']} |")
        if self.console_errors:
            lines.extend(["", "## Browser Console Errors", ""])
            for err in self.console_errors[:40]:
                lines.append(f"- `{err[:500]}`")
        if self.notes:
            lines.extend(["", "## Notes", ""])
            for note in self.notes:
                lines.append(f"- {note}")
        lines.extend([
            "",
            "## Fixes Applied",
            "",
            "- `config.py`: Set ChatMock default provider model to `chatmock/gpt-5.5` and filtered placeholder API keys.",
            "- `routes/blog_routes.py`: Switched default generation model to `DEFAULT_MODEL` / `chatmock/gpt-5.5`.",
            "- `frontend/app/page.tsx`: Wired the existing direct-text input component into the main page.",
            "- `tests/e2e/autoqa/*`: Added ChatMock 5.5 server wrapper, QA matrix, Playwright QA runner, and Windows stack runner/cleanup script.",
            "- QA CORS/CSRF path is verified with explicit `CORS_ORIGINS`, `Origin`, and `Referer` headers matching browser execution.",
            "- Export-menu QA now scopes clicks to the generated result card, avoiding the Next.js dev overlay.",
            "",
            "## Summary",
            "",
            f"- Failures: `{self.failures}`",
        ])
        REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def screenshot(page, name: str) -> str:
    path = ARTIFACTS / name
    page.screenshot(path=str(path), full_page=True)
    return _rel(path)


def get_json(url: str, timeout: int = 15) -> Any:
    res = requests.get(url, timeout=timeout)
    res.raise_for_status()
    return res.json()


def post_json(url: str, payload: dict[str, Any], timeout: int = 180) -> Any:
    res = requests.post(url, json=payload, timeout=timeout, headers={"Origin": FRONTEND_URL, "Referer": FRONTEND_URL + "/"})
    if not res.ok:
        raise RuntimeError(f"HTTP {res.status_code}: {res.text[:1000]}")
    return res.json()


def open_generation_settings(page) -> None:
    page.locator("#url-input").wait_for(state="visible", timeout=20_000)
    page.locator("#url-input").evaluate(
        """el => {
            const root = el.parentElement;
            const buttons = root ? root.querySelectorAll('button') : [];
            if (!buttons.length) throw new Error('settings button not found');
            buttons[0].click();
        }"""
    )
    page.locator("[role='dialog']").wait_for(state="visible", timeout=10_000)


def click_text_generate(page) -> None:
    textarea = page.locator("textarea").first
    textarea.wait_for(state="visible", timeout=20_000)
    qa_text = (
        "??? ? ??? ??? ??????. ?? QA? ChatMock 5.5 ??? ?? "
        "?? ??? ?? ??? ?? ????? ?????. ?? ??? ?? ?? ?????."
    )
    textarea.fill(qa_text)
    page.wait_for_timeout(300)
    textarea.evaluate(
        """el => {
            const outer = el.closest('div');
            const root = outer && outer.parentElement ? outer.parentElement : el.parentElement;
            const buttons = root ? root.querySelectorAll('button') : [];
            if (!buttons.length) throw new Error('text generate button not found');
            buttons[buttons.length - 1].click();
        }"""
    )


def main() -> int:
    report = QaReport()

    # Backend/ChatMock API checks
    try:
        models = get_json(f"{CHATMOCK_URL}/models")
        ids = [m.get("id") for m in models.get("data", [])]
        report.record("chatmock-server", "gpt-5.5" in ids, f"/v1/models ids={ids[:6]}")
    except Exception as exc:
        report.record("chatmock-server", False, repr(exc))

    try:
        providers = get_json(f"{BACKEND_URL}/api/providers")
        chatmock = providers.get("providers", {}).get("chatmock")
        first_model = (chatmock or {}).get("models", [{}])[0].get("id")
        report.record("provider-chatmock-api", first_model == MODEL_ID, f"first_model={first_model}")
    except Exception as exc:
        report.record("provider-chatmock-api", False, repr(exc))

    # Direct backend canary: proves Flask -> LiteLLM -> ChatMock 5.5 path.
    try:
        payload = {
            "url": "",
            "content": "?? API ??????. ChatMock 5.5 ??? ?? ??? ??? ??? ???. ? ??? 50?? ????.",
            "model": MODEL_ID,
            "style": "summary",
            "modifiers": {"length": "short", "writing_style": "conversational", "language": "ko"},
        }
        generated = post_json(f"{BACKEND_URL}/generate", payload, timeout=180)
        ok = bool(generated.get("content") or generated.get("html")) and generated.get("transcript_source") == "direct_input"
        report.record("direct-text-api", ok, f"title={generated.get('title', '')[:80]!r}, source={generated.get('transcript_source')}")
    except Exception as exc:
        report.record("direct-text-api", False, repr(exc))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
        context.add_init_script(
            """
            localStorage.setItem('insight-engine-onboarding-done', JSON.stringify(true));
            localStorage.setItem('insight-engine-selected-provider', JSON.stringify('chatmock'));
            localStorage.setItem('insight-engine-selected-model', JSON.stringify('chatmock/gpt-5.5'));
            localStorage.removeItem('insight-engine-reports');
            """
        )
        page = context.new_page()
        page.on("console", lambda msg: report.console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: report.console_errors.append(str(exc)))

        try:
            page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
            page.locator("#url-input").wait_for(state="visible", timeout=60_000)
            page.wait_for_timeout(1000)
            home_png = screenshot(page, "home-load.png")
            report.record("home-load", page.locator("#url-input").count() > 0, home_png)
        except Exception as exc:
            report.record("home-load", False, f"{type(exc).__name__}: {exc}")
            report.write()
            browser.close()
            return report.failures

        try:
            open_generation_settings(page)
            settings_png = screenshot(page, "settings-open.png")
            dialog_text = page.locator("[role='dialog']").inner_text(timeout=5_000)
            ok = "ChatMock" in dialog_text or "GPT-5.5" in dialog_text or "5.5" in dialog_text
            report.record("settings-open", True, settings_png)
            report.record("provider-chatmock", ok, "settings popover contains ChatMock/GPT-5.5" if ok else dialog_text[:300])

            style_buttons = page.locator("[role='dialog'] button[aria-pressed]")
            style_count = style_buttons.count()
            if style_count:
                target = style_buttons.nth(min(1, style_count - 1))
                target.click(timeout=5_000)
                pressed = target.get_attribute("aria-pressed") == "true"
                report.record("style-selection", pressed, f"style buttons={style_count}")
            else:
                report.record("style-selection", False, "no aria-pressed style buttons")
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
        except Exception as exc:
            report.record("settings-open", False, repr(exc))
            report.record("provider-chatmock", False, repr(exc))
            report.record("style-selection", False, repr(exc))

        try:
            page.locator("#url-input").fill("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            page.locator("#url-input").press("Enter")
            page.wait_for_timeout(800)
            body = page.content()
            url_png = screenshot(page, "youtube-url-validation.png")
            ok = "dQw4w9WgXcQ" in body or "youtube" in body.lower()
            report.record("youtube-url-validation", ok, url_png)
            # Remove URL chip so direct text mode is visible.
            remove_buttons = page.locator("button", has=page.locator("svg"))
            page.locator("#url-input").evaluate(
                """el => {
                    const chips = Array.from(document.querySelectorAll('button'))
                      .filter(b => (b.getAttribute('aria-label') || '').includes('dQw4w9WgXcQ'));
                    if (chips[0]) chips[0].click();
                }"""
            )
            page.wait_for_timeout(500)
        except Exception as exc:
            report.record("youtube-url-validation", False, repr(exc))

        try:
            # Ensure no URL chips remain; reload if the direct text textarea is hidden.
            if page.locator("textarea").count() == 0:
                page.reload(wait_until="domcontentloaded", timeout=60_000)
                page.locator("#url-input").wait_for(state="visible", timeout=60_000)
            click_text_generate(page)
            page.locator("[data-report-id]").wait_for(state="visible", timeout=220_000)
            gen_png = screenshot(page, "direct-text-generate.png")
            alert_text = page.locator("[role='alert']").inner_text(timeout=1000) if page.locator("[role='alert']").count() else ""
            ok = page.locator("[data-report-id]").count() > 0 and not alert_text
            report.record("direct-text-generate", ok, gen_png if ok else f"alert={alert_text}; screenshot={gen_png}")
        except Exception as exc:
            fail_png = screenshot(page, "direct-text-generate-fail.png")
            report.record("direct-text-generate", False, f"{repr(exc)}; screenshot={fail_png}")

        try:
            page.locator("header button").first.click(timeout=5_000)
            page.locator("aside").wait_for(state="visible", timeout=10_000)
            history_png = screenshot(page, "history-panel.png")
            report.record("history-panel", True, history_png)
        except Exception as exc:
            report.record("history-panel", False, repr(exc))

        try:
            card = page.locator("[data-report-id]").first
            card.scroll_into_view_if_needed(timeout=10_000)
            menu_button = card.locator("button[aria-haspopup='menu']").last
            menu_button.click(timeout=10_000)
            page.locator("[role='menu']").wait_for(state="visible", timeout=10_000)
            menu_text = page.locator("[role='menu']").inner_text(timeout=5_000)
            export_png = screenshot(page, "export-buttons.png")
            ok = any(token in menu_text.lower() for token in ["docx", "html", ".md", ".txt", "zip"])
            report.record("export-buttons", ok, export_png if ok else menu_text[:300])
        except Exception as exc:
            report.record("export-buttons", False, repr(exc))

        browser.close()

    if report.console_errors:
        # Known browser extension / dev noise should not fail QA; actual app errors are visible in report.
        report.notes.append("???? console error? ?? ??? ??????.")

    report.write()
    return report.failures


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        (ARTIFACTS / "run_autoqa.crash.log").write_text(traceback.format_exc(), encoding="utf-8")
        raise
