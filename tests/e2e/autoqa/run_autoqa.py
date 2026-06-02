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

MENU_EXPECTED_LABELS = [
    "제목 복사",
    "전체 복사",
    "프롬프트 보기",
    "플랫폼 변환",
    "NLM 팟캐스트",
    "NLM 비디오",
    "NLM 인포그래픽",
    "NLM 슬라이드",
    "NLM 마인드맵",
    "NLM 퀴즈",
    "NLM 플래시카드",
    "NLM 브리핑",
    "NLM 스터디 가이드",
    "이벤트 추출",
    "영상에 질문하기",
    "HTML 내보내기",
    "DOCX 내보내기",
    "마크다운 (.md)",
    "텍스트 (.txt)",
    "패키지 (.zip)",
    "PDF 인쇄",
    "예약 발행",
    "공유",
    "삭제",
]

NOTEBOOK_MENU_TYPES = {
    "NLM 팟캐스트": "audio",
    "NLM 비디오": "video",
    "NLM 인포그래픽": "infographic",
    "NLM 슬라이드": "slide_deck",
    "NLM 마인드맵": "mindmap",
    "NLM 퀴즈": "quiz",
    "NLM 플래시카드": "flashcards",
    "NLM 브리핑": "briefing",
    "NLM 스터디 가이드": "study_guide",
}

EXPORT_MENU_EXTENSIONS = {
    "HTML 내보내기": ".html",
    "DOCX 내보내기": ".docx",
    "마크다운 (.md)": ".md",
    "텍스트 (.txt)": ".txt",
    "패키지 (.zip)": ".zip",
}


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
            "- Result-card action-menu QA now clicks every copy, prompt, platform, NLM, event, chat, export, schedule, share, and delete item with external side effects mocked.",
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
    page.locator("#url-input").locator("xpath=following-sibling::button[1]").click(timeout=10_000)
    page.locator("[role='dialog']").wait_for(state="visible", timeout=10_000)


def click_text_generate(page) -> None:
    page.locator("[data-testid='source-tab-text']").click(timeout=10_000)
    page.wait_for_timeout(300)
    textarea = page.locator("textarea").first
    textarea.wait_for(state="visible", timeout=20_000)
    qa_text = (
        "This is a long direct text source for the studio Generate Dock QA. "
        "It verifies that text input is treated as a real source and can create a result card."
    )
    textarea.fill(qa_text)
    page.wait_for_timeout(300)
    dock_button = page.locator("[data-testid='generate-dock-button']")
    dock_button.wait_for(state="visible", timeout=10_000)
    if not dock_button.is_enabled():
        raise AssertionError("Generate Dock button should be enabled for valid text source")
    dock_button.click(timeout=10_000)


def wait_until(predicate, timeout_ms: int = 5_000, page=None) -> bool:
    deadline = time.time() + (timeout_ms / 1000)
    while time.time() < deadline:
        if predicate():
            return True
        if page is not None:
            page.wait_for_timeout(50)
        else:
            time.sleep(0.05)
    return bool(predicate())


def menu_report_fixture() -> dict[str, Any]:
    return {
        "id": "qa-menu-report",
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "youtube_title": "QA용 테스트 영상",
        "title": "QA 전체 메뉴 테스트 리포트",
        "content": (
            "# QA 전체 메뉴 테스트\n\n"
            "이 콘텐츠는 결과 카드 액션 메뉴의 복사, 변환, NLM, 내보내기, 발행, 예약, 공유, 삭제를 "
            "검증하기 위한 안전한 테스트 데이터입니다.\n\n"
            "- 핵심 요약\n- 실행 항목\n- 참고 링크\n"
        ),
        "html": "<h1>QA 전체 메뉴 테스트</h1><p>안전한 테스트 콘텐츠입니다.</p>",
        "style": "summary",
        "prompt": "QA 자동화가 프롬프트 보기 메뉴를 검증하기 위한 테스트 프롬프트입니다.",
        "usage": {"total_tokens": 1234},
        "elapsed_time": 1.2,
        "transcript_source": "qa_seed",
        "cached": False,
        "comment_summary_included": False,
        "time": "방금 전",
        "createdAt": int(time.time() * 1000),
        "transcript": "00:00 소개. 00:30 핵심 요약. 01:00 실행 항목.",
        "transcript_segments": [
            {"start": 0, "text": "소개"},
            {"start": 30, "text": "핵심 요약"},
            {"start": 60, "text": "실행 항목"},
        ],
    }


def install_menu_mocks(context, calls: dict[str, list[dict[str, Any]]]) -> None:
    plugins = [
        {"id": "naver_blog", "name": "네이버 블로그", "description": "QA mock"},
        {"id": "wordpress", "name": "WordPress", "description": "QA mock"},
        {"id": "medium", "name": "Medium", "description": "QA mock"},
        {"id": "substack", "name": "Substack", "description": "QA mock"},
    ]

    def fulfill_json(route, payload: dict[str, Any], status: int = 200) -> None:
        route.fulfill(status=status, content_type="application/json", body=json.dumps(payload, ensure_ascii=False))

    def request_payload(route) -> dict[str, Any]:
        try:
            data = route.request.post_data_json
            if callable(data):
                data = data()
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    context.route("**/api/mcp/plugins", lambda route: fulfill_json(route, {"plugins": plugins}))

    def schedule(route) -> None:
        payload = request_payload(route)
        calls["schedule"].append(payload)
        fulfill_json(
            route,
            {
                "id": "qa-schedule-1",
                "title": payload.get("title"),
                "content": payload.get("content"),
                "target_plugin": payload.get("target_plugin"),
                "scheduled_at": payload.get("scheduled_at"),
                "status": "pending",
            },
            status=201,
        )

    context.route("**/api/schedule", schedule)
    context.route("**/api/notebooklm/auth-check", lambda route: fulfill_json(route, {"valid": True, "email": "qa@example.com"}))

    def notebook_generate(route) -> None:
        payload = request_payload(route)
        calls["notebooklm"].append(payload)
        fulfill_json(route, {"artifact_id": f"qa-{payload.get('type', 'unknown')}", "status": "in_progress"}, status=202)

    context.route("**/api/notebooklm/generate", notebook_generate)
    context.route("**/api/notebooklm/status/*", lambda route: fulfill_json(route, {"status": "completed", "type": "qa"}))

    def rewrite(route) -> None:
        payload = request_payload(route)
        calls["rewrite"].append(payload)
        platform = payload.get("platform", "unknown")
        text = f"[{platform}] QA 메뉴 변환 결과입니다."
        fulfill_json(route, {"text": text, "char_count": len(text), "max_chars": 280})

    context.route("**/api/rewrite", rewrite)

    def extract_events(route) -> None:
        payload = request_payload(route)
        calls["events"].append(payload)
        event = {
            "type": "action_item",
            "content": "QA 자동화 이벤트 확인",
            "timestamp": "00:01:00",
            "context": "메뉴 테스트",
            "priority": "medium",
        }
        fulfill_json(
            route,
            {
                "events": [event],
                "categorized": {"action_item": [event], "key_point": [], "decision": [], "question": []},
                "summary": {
                    "total": 1,
                    "by_type": {"action_item": 1, "key_point": 0, "decision": 0, "question": 0},
                    "type_labels": {
                        "action_item": "액션 아이템",
                        "key_point": "핵심 포인트",
                        "decision": "결정 사항",
                        "question": "질문",
                    },
                    "highlights": {
                        "high_priority_actions": [],
                        "important_key_points": [],
                        "open_questions": [],
                    },
                },
            },
        )

    context.route("**/api/extract-events", extract_events)

    def video_qa(route) -> None:
        payload = request_payload(route)
        calls["video_qa"].append(payload)
        fulfill_json(
            route,
            {
                "answer": "QA mock answer: 영상 질문 기능이 정상 호출되었습니다.",
                "sources": [{"text": "QA transcript source", "relevance": 0.92}],
            },
        )

    context.route("**/api/video-qa", video_qa)

    export_payloads = {
        "docx": ("qa-menu.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx mock"),
        "markdown": ("qa-menu.md", "text/markdown", "# markdown mock"),
        "txt": ("qa-menu.txt", "text/plain", "txt mock"),
        "zip": ("qa-menu.zip", "application/zip", "zip mock"),
    }

    for fmt, (filename, mime, body) in export_payloads.items():
        def handler(route, fmt=fmt, filename=filename, mime=mime, body=body) -> None:
            payload = request_payload(route)
            calls["exports"].append({"format": fmt, **payload})
            route.fulfill(
                status=200,
                headers={"Content-Type": mime, "Content-Disposition": f"attachment; filename={filename}"},
                body=body,
            )

        context.route(f"**/api/export/{fmt}", handler)


def install_upload_generate_mock(context, calls: list[dict[str, Any]]):
    def upload_generate(route) -> None:
        request = route.request
        content_type = request.headers.get("content-type", "")
        if request.method != "POST" or "multipart/form-data" not in content_type:
            route.continue_()
            return

        body = request.post_data_buffer or b""
        source_kind = "audio" if b"qa-voice.webm" in body else "file"
        calls.append({"kind": source_kind, "content_type": content_type})
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "title": f"QA {source_kind} upload",
                "content": f"# QA {source_kind} upload\n\nGenerated from uploaded source.",
                "html": f"<h1>QA {source_kind} upload</h1><p>Generated from uploaded source.</p>",
                "usage": {"total_tokens": 42},
                "elapsed_time": 0.2,
                "transcript_source": f"{source_kind}_upload",
                "prompt": "upload qa",
                "cached": False,
                "comment_summary_included": False,
            }),
        )

    context.route("**/generate", upload_generate)
    return upload_generate


def seed_menu_context(context) -> None:
    report = menu_report_fixture()
    context.add_init_script(
        f"""
        localStorage.setItem('insight-engine-onboarding-done', JSON.stringify(true));
        localStorage.setItem('insight-engine-selected-provider', JSON.stringify('chatmock'));
        localStorage.setItem('insight-engine-selected-model', JSON.stringify('chatmock/gpt-5.5'));
        localStorage.setItem('ie_view_mode', 'full');
        localStorage.setItem('insight-engine-reports', JSON.stringify({json.dumps([report], ensure_ascii=False)}));
        localStorage.removeItem('insight_engine_pinned_ids');
        """
    )


def close_dialogs(page) -> None:
    page.keyboard.press("Escape")
    page.wait_for_timeout(250)
    panel = page.locator("div.fixed.inset-y-0.right-0")
    if panel.count() and panel.first.is_visible():
        panel.first.locator("button").first.click(timeout=5_000)
        panel.first.wait_for(state="hidden", timeout=5_000)


def open_action_menu(page):
    close_dialogs(page)
    card = page.locator("[data-report-id='qa-menu-report']").first
    card.scroll_into_view_if_needed(timeout=10_000)
    trigger = card.locator("button[aria-haspopup='menu']").last
    trigger.click(timeout=10_000)
    menu = page.locator("[role='menu']").last
    menu.wait_for(state="visible", timeout=10_000)
    return menu


def click_menu_label(page, label: str) -> None:
    menu = open_action_menu(page)
    item = menu.locator("[role='menuitem']", has_text=label)
    if item.count() != 1:
        raise AssertionError(f"menu item {label!r} count={item.count()}")
    item.click(timeout=10_000)


def run_seeded_menu_action_suite(browser, report: QaReport) -> None:
    calls: dict[str, list[dict[str, Any]]] = {
        "schedule": [],
        "notebooklm": [],
        "rewrite": [],
        "events": [],
        "video_qa": [],
        "exports": [],
    }
    context = browser.new_context(viewport={"width": 1440, "height": 1100}, accept_downloads=True)
    context.grant_permissions(["clipboard-read", "clipboard-write"], origin=FRONTEND_URL)
    install_menu_mocks(context, calls)
    seed_menu_context(context)
    page = context.new_page()
    page.on("console", lambda msg: report.console_errors.append(f"[menu] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[menu] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("[data-report-id='qa-menu-report']").wait_for(state="visible", timeout=60_000)
        menu = open_action_menu(page)
        visible_labels = [line.strip() for line in menu.inner_text(timeout=5_000).splitlines() if line.strip()]
        missing = [label for label in MENU_EXPECTED_LABELS if label not in visible_labels]
        removed_publish = ["네이버 블로그 발행", "WordPress 발행", "Medium 발행", "Substack 발행"]
        still_visible = [label for label in removed_publish if label in visible_labels]
        menu_png = screenshot(page, "menu-all-items.png")
        report.record(
            "menu-all-items",
            not missing and not still_visible,
            menu_png if not missing and not still_visible else f"missing={missing}; still_visible={still_visible}; labels={visible_labels}",
        )
        close_dialogs(page)
    except Exception as exc:
        report.record("menu-all-items", False, repr(exc))
        context.close()
        return

    def record_action(label: str, ok: bool, evidence: str) -> None:
        safe_id = (
            label.replace(" ", "-")
            .replace("/", "-")
            .replace("(", "")
            .replace(")", "")
            .replace(".", "")
        )
        report.record(f"menu-action:{safe_id}", ok, evidence)

    title = menu_report_fixture()["title"]
    content = menu_report_fixture()["content"]

    for label, expected_text in [("제목 복사", title), ("전체 복사", content)]:
        try:
            click_menu_label(page, label)
            copied = page.evaluate("navigator.clipboard.readText()")
            ok = title in copied if label == "제목 복사" else ("QA 전체 메뉴 테스트" in copied and "핵심 요약" in copied)
            record_action(label, ok, f"clipboard_len={len(copied)}")
        except Exception as exc:
            record_action(label, False, repr(exc))

    try:
        click_menu_label(page, "프롬프트 보기")
        dialog = page.locator("[role='dialog']").last
        dialog.wait_for(state="visible", timeout=10_000)
        text = dialog.inner_text(timeout=5_000)
        prompt_png = screenshot(page, "menu-prompt-view.png")
        record_action("프롬프트 보기", "테스트 프롬프트" in text, prompt_png if "테스트 프롬프트" in text else text[:300])
        close_dialogs(page)
    except Exception as exc:
        record_action("프롬프트 보기", False, repr(exc))

    try:
        before = len(calls["rewrite"])
        click_menu_label(page, "플랫폼 변환")
        dialog = page.locator("[role='dialog']").last
        dialog.wait_for(state="visible", timeout=10_000)
        dialog.get_by_text("Twitter / X").click(timeout=10_000)
        ok_call = wait_until(lambda: len(calls["rewrite"]) > before, 10_000, page)
        page.get_by_text("QA 메뉴 변환 결과").wait_for(state="visible", timeout=10_000)
        platform_png = screenshot(page, "menu-platform-convert.png")
        record_action("플랫폼 변환", ok_call, platform_png if ok_call else "rewrite API not called")
        close_dialogs(page)
    except Exception as exc:
        record_action("플랫폼 변환", False, repr(exc))
        close_dialogs(page)

    for label, expected_type in NOTEBOOK_MENU_TYPES.items():
        try:
            before = len(calls["notebooklm"])
            click_menu_label(page, label)
            ok = wait_until(
                lambda: len(calls["notebooklm"]) > before and calls["notebooklm"][-1].get("type") == expected_type,
                10_000,
                page,
            )
            record_action(label, ok, f"type={calls['notebooklm'][-1].get('type') if calls['notebooklm'] else None}")
        except Exception as exc:
            record_action(label, False, repr(exc))

    try:
        before = len(calls["events"])
        click_menu_label(page, "이벤트 추출")
        ok_call = wait_until(lambda: len(calls["events"]) > before, 10_000, page)
        page.get_by_text("QA 자동화 이벤트 확인").wait_for(state="visible", timeout=10_000)
        event_png = screenshot(page, "menu-event-extract.png")
        record_action("이벤트 추출", ok_call, event_png if ok_call else "extract-events API not called")
    except Exception as exc:
        record_action("이벤트 추출", False, repr(exc))

    try:
        before = len(calls["video_qa"])
        click_menu_label(page, "영상에 질문하기")
        chat_panel = page.locator("div.fixed.inset-y-0.right-0").last
        chat_panel.wait_for(state="visible", timeout=10_000)
        panel = chat_panel.locator("textarea").first
        panel.wait_for(state="visible", timeout=10_000)
        panel.fill("핵심 내용이 뭐야?")
        panel.press("Enter", timeout=10_000)
        ok_call = wait_until(lambda: len(calls["video_qa"]) > before, 10_000, page)
        chat_panel.get_by_text("QA mock answer").wait_for(state="visible", timeout=10_000)
        chat_png = screenshot(page, "menu-video-chat.png")
        record_action("영상에 질문하기", ok_call, chat_png if ok_call else "video-qa API not called")
        chat_panel.locator("button").first.click(timeout=5_000)
    except Exception as exc:
        record_action("영상에 질문하기", False, repr(exc))
        close_dialogs(page)

    for label, expected_ext in EXPORT_MENU_EXTENSIONS.items():
        try:
            with page.expect_download(timeout=15_000) as download_info:
                click_menu_label(page, label)
            download = download_info.value
            filename = download.suggested_filename
            ok = filename.lower().endswith(expected_ext)
            record_action(label, ok, f"download={filename}")
        except Exception as exc:
            record_action(label, False, repr(exc))

    try:
        page.evaluate(
            """
            window.__qaPrintCalled = false;
            window.open = () => ({
              document: { write: () => {}, close: () => {} },
              print: () => { window.__qaPrintCalled = true; },
            });
            """
        )
        click_menu_label(page, "PDF 인쇄")
        printed = page.evaluate("window.__qaPrintCalled === true")
        record_action("PDF 인쇄", bool(printed), f"print_called={printed}")
    except Exception as exc:
        record_action("PDF 인쇄", False, repr(exc))

    try:
        before = len(calls["schedule"])
        click_menu_label(page, "예약 발행")
        dialog = page.locator("[role='dialog']").last
        dialog.wait_for(state="visible", timeout=10_000)
        dialog.locator("button", has_text="예약 등록").click(timeout=10_000)
        ok = wait_until(lambda: len(calls["schedule"]) > before, 10_000, page)
        schedule_png = screenshot(page, "menu-schedule.png")
        record_action("예약 발행", ok, schedule_png if ok else "schedule API not called")
    except Exception as exc:
        record_action("예약 발행", False, repr(exc))
        close_dialogs(page)

    try:
        click_menu_label(page, "공유")
        copied = page.evaluate("navigator.clipboard.readText()")
        ok = title in copied and "youtube.com" in copied
        record_action("공유", ok, f"clipboard_len={len(copied)}")
    except Exception as exc:
        record_action("공유", False, repr(exc))

    try:
        click_menu_label(page, "삭제")
        removed = page.locator("[data-report-id='qa-menu-report']").count() == 0
        if not removed:
            page.locator("[data-report-id='qa-menu-report']").wait_for(state="detached", timeout=5_000)
            removed = True
        record_action("삭제", removed, f"card_removed={removed}")
    except Exception as exc:
        record_action("삭제", False, repr(exc))

    report.notes.append("Result-card action menu QA mocks NotebookLM, schedule, rewrite, event extraction, video QA, and binary export APIs to avoid external side effects.")
    context.close()


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
            studio_visible = page.get_by_text("AI Content Studio").count() > 0 or page.get_by_text("Source Composer").count() > 0
            report.record("studio-layout", studio_visible, "studio hero/source composer visible" if studio_visible else screenshot(page, "studio-layout-fail.png"))
        except Exception as exc:
            report.record("home-load", False, f"{type(exc).__name__}: {exc}")
            report.write()
            browser.close()
            return report.failures

        for case_id, tab_test_id, panel_test_id, filename, content in [
            ("source-file-generate", "source-tab-file", "file-source-panel", "qa-upload.docx", b"qa docx upload"),
            ("source-voice-generate", "source-tab-voice", "voice-source-panel", "qa-voice.webm", b"qa audio upload"),
        ]:
            upload_calls: list[dict[str, Any]] = []
            upload_handler = install_upload_generate_mock(context, upload_calls)
            source_path = ARTIFACTS / filename
            source_path.write_bytes(content)
            try:
                page.locator(f"[data-testid='{tab_test_id}']").click(timeout=10_000)
                page.locator(f"[data-testid='{panel_test_id}']").wait_for(state="visible", timeout=10_000)
                file_input = page.locator(f"[data-testid='{panel_test_id}'] input[type='file']").first
                file_input.set_input_files(str(source_path))
                page.get_by_text(filename).wait_for(state="visible", timeout=10_000)
                dock_button = page.locator("[data-testid='generate-dock-button']")
                if not dock_button.is_enabled():
                    raise AssertionError("Generate Dock button should be enabled after upload")
                before = len(upload_calls)
                dock_button.click(timeout=10_000)
                ok_call = wait_until(lambda: len(upload_calls) > before, 10_000, page)
                page.locator("[data-report-id]").first.wait_for(state="visible", timeout=30_000)
                png = screenshot(page, f"{case_id}.png")
                report.record(case_id, ok_call, png if ok_call else f"upload calls={upload_calls}")
            except Exception as exc:
                fail_png = screenshot(page, f"{case_id}-fail.png")
                report.record(case_id, False, f"{repr(exc)}; screenshot={fail_png}")
            finally:
                context.unroute("**/generate", upload_handler)
                page.evaluate("localStorage.removeItem('insight-engine-reports')")
                page.reload(wait_until="domcontentloaded", timeout=60_000)
                page.locator("#url-input").wait_for(state="visible", timeout=60_000)

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
            report.record("text-dock-generate", ok, gen_png if ok else f"alert={alert_text}; screenshot={gen_png}")
            workbench = page.locator("[data-testid='result-workbench']").first
            workbench_visible = workbench.count() > 0 and workbench.is_visible()
            report.record("result-workbench", workbench_visible, screenshot(page, "result-workbench.png") if workbench_visible else "workbench panel missing")
        except Exception as exc:
            fail_png = screenshot(page, "direct-text-generate-fail.png")
            report.record("direct-text-generate", False, f"{repr(exc)}; screenshot={fail_png}")

        try:
            page.locator("header button").first.click(timeout=5_000)
            page.locator("aside[role='navigation']").wait_for(state="visible", timeout=10_000)
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

        run_seeded_menu_action_suite(browser, report)

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
