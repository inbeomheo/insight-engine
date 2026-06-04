from __future__ import annotations

import json
import os
import pathlib
import re
import time
import traceback
from datetime import datetime, timezone
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
                lines.append(f"- `{err[:6000]}`")
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
    try:
        page.screenshot(path=str(path), full_page=True, caret="initial", timeout=10_000)
        return _rel(path)
    except Exception as exc:
        return f"screenshot-unavailable:{name}:{type(exc).__name__}:{str(exc)[:300]}"


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
    dialog = page.locator("[role='dialog'][aria-labelledby='settings-popover-title']")
    if dialog.count() > 0 and dialog.is_visible(timeout=1_000):
        return
    trigger = page.locator("[data-testid='settings-popover-trigger']").first
    trigger.wait_for(state="visible", timeout=10_000)
    trigger.click(timeout=10_000)
    if wait_until(lambda: dialog.count() > 0 and dialog.is_visible(timeout=1_000), 5_000, page):
        return
    trigger.click(timeout=10_000)
    dialog.wait_for(state="visible", timeout=10_000)


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
        "notebooklm": {
            "artifacts": [
                {"artifact_id": "qa-study-guide", "content_type": "study_guide", "status": "completed"},
            ],
        },
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
        options = payload.get("options") or payload.get("plugin_options") or {}
        if isinstance(options, dict) and options.get("category") == "QA_FAIL":
            fulfill_json(route, {"success": False, "error": "schedule failed"})
            return
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
    def notebook_rendered_download(route) -> None:
        calls["notebooklm_downloads"].append({"url": route.request.url})
        route.fulfill(
            status=200,
            headers={"Content-Type": "text/markdown", "Content-Disposition": "attachment; filename=qa-study-guide.md"},
            body="# QA NotebookLM markdown\n\nThis simulates a stale backend markdown attachment.",
        )

    context.route("**/api/notebooklm/rendered-download/*", notebook_rendered_download)
    context.route(
        "**/api/notebooklm/view/*",
        lambda route: route.fulfill(
            status=200,
            content_type="text/html; charset=utf-8",
            body="<!doctype html><html><body><h1>QA NotebookLM HTML</h1></body></html>",
        ),
    )

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
        "html": ("qa-menu.html", "text/html", "<!doctype html><html><body><h1>html mock</h1></body></html>"),
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
        localStorage.setItem('insight-engine-wordpress-defaults', JSON.stringify({{
            site_url: 'https://stored.wp.example.com',
            username: 'stored-writer',
            status: 'pending',
        }}));
        localStorage.setItem('insight-engine-naver-defaults', JSON.stringify({{
            webhook_url: 'https://stored.naver.example.com/webhook',
            blog_id: 'stored-blog',
            category: 'AI 자동화',
            tags: 'ai,자동화',
        }}));
        localStorage.setItem('ie_view_mode', 'full');
        localStorage.setItem('insight-engine-reports', JSON.stringify({json.dumps([report], ensure_ascii=False)}));
        localStorage.removeItem('insight_engine_pinned_ids');
        """
    )


def seed_right_panel_context(context) -> None:
    report = menu_report_fixture()
    report["notebooklm"] = {
        "artifacts": [
            {"artifact_id": "rp-briefing", "content_type": "briefing", "status": "completed"},
            {"artifact_id": "rp-audio", "content_type": "audio", "status": "in_progress"},
            {"artifact_id": "rp-quiz", "content_type": "quiz", "status": "failed"},
        ]
    }
    context.add_init_script(
        f"""
        localStorage.setItem('insight-engine-onboarding-done', JSON.stringify(true));
        localStorage.setItem('insight-engine-selected-provider', JSON.stringify('chatmock'));
        localStorage.setItem('insight-engine-selected-model', JSON.stringify('chatmock/gpt-5.5'));
        localStorage.setItem('ie_view_mode', 'full');
        localStorage.setItem('insight-engine-reports', JSON.stringify({json.dumps([report], ensure_ascii=False)}));
        """
    )


def run_notebooklm_auth_notice_suite(browser, report: QaReport) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 1100}, accept_downloads=True)
    context.route(
        "**/api/notebooklm/auth-check",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "valid": False,
                    "message": "NotebookLM 인증이 필요합니다. 터미널에서 nlm login을 실행해주세요.",
                },
                ensure_ascii=False,
            ),
        ),
    )
    seed_menu_context(context)
    page = context.new_page()
    page.on("console", lambda msg: report.console_errors.append(f"[nlm-auth] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[nlm-auth] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("[data-report-id='qa-menu-report']").wait_for(state="visible", timeout=60_000)
        page.locator("[data-testid='workbench-action-nlm-study-guide']").click(timeout=10_000)
        notice = page.locator("[data-testid='workbench-nlm-auth-notice']")
        notice.wait_for(state="visible", timeout=10_000)
        notice_text = notice.inner_text(timeout=5_000)
        ok = "nlm login" in notice_text and "NotebookLM" in notice_text
        report.record(
            "workbench-nlm-auth-notice",
            ok,
            screenshot(page, "workbench-nlm-auth-notice.png") if ok else notice_text[:300],
        )
    except Exception as exc:
        fail_png = screenshot(page, "workbench-nlm-auth-notice-fail.png")
        report.record("workbench-nlm-auth-notice", False, f"{repr(exc)}; screenshot={fail_png}")
    finally:
        context.close()


def run_right_panel_suite(browser, report: QaReport) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    today = datetime.now(timezone.utc)
    today_key = today.strftime("%Y-%m-%d")
    seeded_schedule = {
        "id": "qa-calendar-wordpress",
        "title": "캘린더 WordPress 예약",
        "content": "예약 캘린더 라벨 검증",
        "target_plugin": "wordpress",
        "plugin_options": {
            "site_url": "https://wp.example.com",
            "username": "qa-writer",
            "app_password": "qa-secret",
            "status": "draft",
        },
        "scheduled_at": today.replace(hour=9, minute=0, second=0, microsecond=0).isoformat(),
        "status": "pending",
        "created_at": today.isoformat(),
    }
    seeded_naver_schedule = {
        "id": "qa-calendar-naver",
        "title": "캘린더 네이버 예약",
        "content": "네이버 예약 캘린더 옵션 검증",
        "target_plugin": "naver_blog",
        "plugin_options": {
            "webhook_url": "https://qa-webhook-secret.example.com/naver",
            "blog_id": "qa-naver",
            "category": "AI 자동화",
            "tags": "ai,자동화",
        },
        "scheduled_at": today.replace(hour=10, minute=30, second=0, microsecond=0).isoformat(),
        "status": "pending",
        "created_at": today.isoformat(),
    }
    calendar_delete_calls: list[str] = []

    def handle_calendar_delete(route) -> None:
        calendar_delete_calls.append(route.request.url)
        if "qa-calendar-naver" in route.request.url:
            route.fulfill(status=200, content_type="application/json", body=json.dumps({"success": False}))
            return
        route.fulfill(status=200, content_type="application/json", body=json.dumps({"success": True}))

    context.route("**/api/schedule/*", handle_calendar_delete)
    context.route("**/api/schedule", lambda route: route.fulfill(status=200, content_type="application/json", body=json.dumps({"schedules": [seeded_schedule, seeded_naver_schedule]}, ensure_ascii=False)))
    seed_right_panel_context(context)
    context.add_init_script(
        """
        window.__qaOpenedUrls = [];
        window.open = (url, target, features) => {
            window.__qaOpenedUrls.push({ url: String(url), target, features });
            return null;
        };
        """
    )
    page = context.new_page()
    page.on("console", lambda msg: report.console_errors.append(f"[right-panel] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[right-panel] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        panel = page.locator("[data-testid='studio-right-panel']")
        panel.wait_for(state="visible", timeout=60_000)

        settings_ok = (
            panel.locator("[data-testid='right-panel-setting-style']").count() == 1
            and panel.locator("[data-testid='right-panel-setting-mode']").count() == 1
            and panel.locator("[data-testid='right-panel-setting-model']").count() == 1
        )
        report.record("right-panel-settings", settings_ok, screenshot(page, "right-panel-settings.png") if settings_ok else panel.inner_text(timeout=5_000)[:500])

        semantic_regions = [
            ("right-panel-workspace-section", "region", "right-panel-workspace-title"),
            ("right-panel-settings-section", "region", "right-panel-settings-title"),
            ("right-panel-actions-section", "region", "right-panel-actions-title"),
            ("right-panel-nlm-artifacts", "region", "right-panel-nlm-title"),
            ("right-panel-recent-section", "region", "right-panel-recent-title"),
        ]
        semantic_missing: list[str] = []
        for test_id, role, labelledby in semantic_regions:
            region = panel.locator(f"[data-testid='{test_id}']")
            if (
                region.count() != 1
                or region.get_attribute("role", timeout=2_000) != role
                or region.get_attribute("aria-labelledby", timeout=2_000) != labelledby
                or page.locator(f"#{labelledby}").count() != 1
            ):
                semantic_missing.append(test_id)
        quick_status = panel.locator("[data-testid='quick-action-workspace-status']")
        notice = panel.locator("[data-testid='quick-action-export-status']")
        nlm_list = panel.locator("[data-testid='right-panel-nlm-list']")
        nlm_item = panel.locator("[data-testid='right-panel-nlm-artifact']").first
        recent_list = panel.locator("[data-testid='right-panel-recent-list']")
        recent_item = panel.locator("[data-testid='right-panel-recent-item']").first
        schedule = panel.locator("[data-testid='right-panel-schedule-card']")
        semantic_ok = (
            not semantic_missing
            and quick_status.get_attribute("role", timeout=2_000) == "status"
            and (quick_status.get_attribute("aria-label", timeout=2_000) or "").startswith("\uacb0\uacfc")
            and notice.count() == 0
            and nlm_list.get_attribute("role", timeout=2_000) == "list"
            and nlm_item.get_attribute("role", timeout=2_000) == "listitem"
            and recent_list.get_attribute("role", timeout=2_000) == "list"
            and recent_item.get_attribute("role", timeout=2_000) == "listitem"
            and (schedule.get_attribute("aria-label", timeout=2_000) or "").startswith("\uc608\uc57d \uce98\ub9b0\ub354 \uc5f4\uae30")
        )
        report.record(
            "right-panel-semantic-regions",
            semantic_ok,
            "right panel exposes labelled regions, live status, NLM/recent lists, and schedule label" if semantic_ok else f"missing={semantic_missing}; quick_role={quick_status.get_attribute('role') if quick_status.count() else None}; quick_label={quick_status.get_attribute('aria-label') if quick_status.count() else None}; nlm_list={nlm_list.get_attribute('role') if nlm_list.count() else None}; nlm_item={nlm_item.get_attribute('role') if nlm_item.count() else None}; recent_list={recent_list.get_attribute('role') if recent_list.count() else None}; recent_item={recent_item.get_attribute('role') if recent_item.count() else None}; schedule={schedule.get_attribute('aria-label') if schedule.count() else None}",
        )

        advanced_summary = panel.locator("[data-testid='right-panel-advanced-summary']")
        advanced_text = advanced_summary.inner_text(timeout=5_000) if advanced_summary.count() == 1 else ""
        advanced_required = ["상세도 표준", "웹 보강 꺼짐", "웹 리서치 켜짐", "댓글 켜짐", "에이전트 꺼짐"]
        advanced_missing = [token for token in advanced_required if token not in advanced_text]
        report.record(
            "right-panel-advanced-summary",
            advanced_summary.count() == 1 and not advanced_missing,
            screenshot(page, "right-panel-advanced-summary.png") if advanced_summary.count() == 1 and not advanced_missing else f"missing={advanced_missing}; text={advanced_text[:300]!r}",
        )

        nlm_ok = wait_until(lambda: panel.locator("[data-testid='right-panel-nlm-artifact']").count() >= 3, 10_000, page)
        nlm_count = panel.locator("[data-testid='right-panel-nlm-artifact']").count()
        report.record("right-panel-nlm", nlm_ok, f"nlm_count={nlm_count}")

        try:
            nlm_action = panel.locator("[data-testid='quick-action-nlm']")
            href_ready = wait_until(
                lambda: "/api/notebooklm/view/rp-briefing" in (nlm_action.get_attribute("href", timeout=1_000) or ""),
                10_000,
                page,
            )
            nlm_href = nlm_action.get_attribute("href", timeout=5_000)
            nlm_action.click(timeout=10_000)
            opened = wait_until(
                lambda: len(page.evaluate("window.__qaOpenedUrls || []")) > 0,
                10_000,
                page,
            )
            opened_urls = page.evaluate("window.__qaOpenedUrls || []")
            opened_url = opened_urls[-1]["url"] if opened_urls else ""
            opened_target = opened_urls[-1].get("target") if opened_urls else None
            url_ok = (
                opened
                and href_ready
                and "/api/notebooklm/view/rp-briefing" in opened_url
                and "/api/notebooklm/view/rp-briefing" in (nlm_href or "")
                and opened_target == "_blank"
            )
            report.record(
                "right-panel-nlm-quick-view",
                url_ok,
                f"url={opened_url}; href={nlm_href}" if url_ok else f"opened={opened_urls}; href={nlm_href}; screenshot={screenshot(page, 'right-panel-nlm-quick-view-fail.png')}",
            )
        except Exception as exc:
            report.record("right-panel-nlm-quick-view", False, repr(exc))

        guided_action_ids = ["export", "schedule", "nlm", "rewrite", "prompt", "settings"]
        missing_guidance = [
            action_id for action_id in guided_action_ids
            if panel.locator(f"[data-testid='quick-action-{action_id}-desc']").count() == 0
        ]
        status_missing = panel.locator("[data-testid='quick-action-workspace-status']").count() == 0
        report.record(
            "right-panel-action-guidance",
            not missing_guidance and not status_missing,
            screenshot(page, "right-panel-action-guidance.png") if not missing_guidance and not status_missing else f"missing={missing_guidance}; status_missing={status_missing}",
        )

        try:
            with page.expect_download(timeout=8_000) as download_info:
                panel.locator("[data-testid='quick-action-export']").click(timeout=10_000)
            download = download_info.value
            notice = panel.locator("[data-testid='quick-action-export-status']")
            notice.wait_for(state="visible", timeout=10_000)
            notice_text = notice.inner_text(timeout=5_000)
            export_ok = (
                download.suggested_filename.lower().endswith(".md")
                and "전체" in notice_text
                and "완료" in notice_text
            )
            report.record(
                "right-panel-export-all",
                export_ok,
                f"download={download.suggested_filename}; notice={notice_text}" if export_ok else screenshot(page, "right-panel-export-all-fail.png"),
            )
        except Exception as exc:
            report.record("right-panel-export-all", False, repr(exc))

        try:
            panel.locator("[data-testid='quick-action-rewrite']").click(timeout=10_000)
            rewrite_title = page.get_by_text("플랫폼별 카피 변환")
            rewrite_title.wait_for(state="visible", timeout=10_000)
            report.record(
                "right-panel-rewrite-action",
                True,
                screenshot(page, "right-panel-rewrite-action.png"),
            )
            page.keyboard.press("Escape")
        except Exception as exc:
            report.record("right-panel-rewrite-action", False, repr(exc))

        try:
            recent_button = panel.locator("[data-testid='right-panel-recent-result']").first
            recent_text = recent_button.inner_text(timeout=5_000)
            recent_label = recent_button.get_attribute("aria-label", timeout=2_000) or ""
            readable_style_ok = (
                "\uc694\uc57d" in recent_text
                and "summary" not in recent_text
                and "\uc694\uc57d" in recent_label
                and "\uacb0\uacfc \uc5f4\uae30" in recent_label
            )
            report.record(
                "right-panel-recent-style-readable",
                readable_style_ok,
                screenshot(page, "right-panel-recent-style-readable.png") if readable_style_ok else f"text={recent_text!r}; aria={recent_label!r}",
            )
        except Exception as exc:
            report.record("right-panel-recent-style-readable", False, repr(exc))

        try:
            page.keyboard.press("Escape")
            panel.locator("[data-testid='right-panel-recent-result']").first.click(timeout=10_000)
            target = page.locator("[data-report-id='qa-menu-report']")
            target.wait_for(state="visible", timeout=10_000)
            focused = target.get_attribute("data-focused") == "true"
            report.record(
                "right-panel-recent-result-focus",
                focused,
                screenshot(page, "right-panel-recent-result-focus.png") if focused else f"data-focused={target.get_attribute('data-focused')}",
            )
        except Exception as exc:
            report.record("right-panel-recent-result-focus", False, repr(exc))

        try:
            panel.locator("[data-testid='right-panel-schedule-card']").click(timeout=10_000)
            schedule_card_calendar_visible = page.locator("[data-testid='content-calendar']").count() > 0
            if not schedule_card_calendar_visible:
                page.locator("[data-testid='content-calendar']").wait_for(state="visible", timeout=10_000)
                schedule_card_calendar_visible = True
            report.record(
                "right-panel-schedule-card",
                schedule_card_calendar_visible,
                screenshot(page, "right-panel-schedule-card.png") if schedule_card_calendar_visible else "calendar not opened",
            )
        except Exception as exc:
            report.record("right-panel-schedule-card", False, repr(exc))

        page.locator("[data-testid='quick-action-schedule']").click(timeout=10_000)
        calendar_visible = page.locator("[data-testid='content-calendar']").count() > 0
        if not calendar_visible:
            page.locator("[data-testid='content-calendar']").wait_for(state="visible", timeout=10_000)
            calendar_visible = True
        report.record("right-panel-quick-actions", calendar_visible, screenshot(page, "right-panel-calendar.png") if calendar_visible else "calendar not opened")
        try:
            page.locator(f"button[aria-label='{today_key} 날짜 선택']").click(timeout=10_000)
            calendar_text = page.locator("[data-testid='content-calendar']").inner_text(timeout=10_000)
            label_ok = "WordPress" in calendar_text and "네이버 블로그" in calendar_text and "wordpress" not in calendar_text and "naver_blog" not in calendar_text
            secret_ok = "qa-secret" not in calendar_text and "app_password" not in calendar_text and "qa-webhook-secret" not in calendar_text and "webhook_url" not in calendar_text
            report.record(
                "calendar-plugin-labels",
                label_ok and secret_ok,
                screenshot(page, "calendar-plugin-labels.png") if label_ok and secret_ok else calendar_text[:500],
            )
            naver_summary_ok = (
                "블로그 qa-naver" in calendar_text
                and "카테고리 AI 자동화" in calendar_text
                and "#ai #자동화" in calendar_text
            )
            report.record(
                "calendar-naver-safe-options",
                naver_summary_ok and secret_ok,
                screenshot(page, "calendar-naver-safe-options.png") if naver_summary_ok and secret_ok else calendar_text[:500],
            )
            wordpress_summary_ok = (
                "wp.example.com" in calendar_text
                and "임시글" in calendar_text
                and "작성자 qa-writer" in calendar_text
            )
            report.record(
                "calendar-wordpress-safe-options",
                wordpress_summary_ok and secret_ok,
                screenshot(page, "calendar-wordpress-safe-options.png") if wordpress_summary_ok and secret_ok else calendar_text[:500],
            )
            fail_before_deletes = len(calendar_delete_calls)
            page.locator("button[aria-label='캘린더 네이버 예약 예약 삭제']").click(timeout=10_000)
            fail_dialog = page.locator("[role='dialog']", has_text="예약 삭제").last
            fail_dialog.wait_for(state="visible", timeout=5_000)
            fail_dialog.locator("button", has_text="삭제하기").click(timeout=5_000)
            failure_called = wait_until(lambda: len(calendar_delete_calls) > fail_before_deletes, 5_000, page)
            page.wait_for_timeout(500)
            failure_dialog_stays_open = fail_dialog.is_visible(timeout=1_000)
            failure_text = fail_dialog.inner_text(timeout=5_000) if failure_dialog_stays_open else ""
            failure_hint_ok = "삭제 실패" in failure_text or "다시 시도" in failure_text
            report.record(
                "calendar-delete-failure-stays-open",
                failure_called and failure_dialog_stays_open and failure_hint_ok,
                f"called={failure_called}; stays_open={failure_dialog_stays_open}; text={failure_text[:300]}",
            )
            if failure_dialog_stays_open:
                fail_dialog.locator("button", has_text="취소").click(timeout=5_000)
                page.wait_for_timeout(300)
            before_deletes = len(calendar_delete_calls)
            calendar = page.locator("[data-testid='content-calendar']")
            page.locator("button[aria-label='캘린더 WordPress 예약 예약 삭제']").click(timeout=10_000)
            dialog = page.locator("[role='dialog']", has_text="예약 삭제").last
            try:
                dialog.wait_for(state="visible", timeout=1_000)
                dialog_visible = True
            except Exception:
                dialog_visible = False
            not_deleted_before_confirm = len(calendar_delete_calls) == before_deletes
            still_visible_before_confirm = "캘린더 WordPress 예약" in calendar.inner_text(timeout=5_000) or "캘린더 네이버 예약" in calendar.inner_text(timeout=5_000)
            if dialog_visible:
                dialog.locator("button", has_text="취소").click(timeout=5_000)
                page.wait_for_timeout(300)
            still_visible_after_cancel = len(calendar_delete_calls) == before_deletes and (
                "캘린더 WordPress 예약" in calendar.inner_text(timeout=5_000) or "캘린더 네이버 예약" in calendar.inner_text(timeout=5_000)
            )
            deleted_after_confirm = False
            if still_visible_after_cancel:
                page.locator("button[aria-label='캘린더 WordPress 예약 예약 삭제']").click(timeout=10_000)
                dialog = page.locator("[role='dialog']", has_text="예약 삭제").last
                dialog.wait_for(state="visible", timeout=5_000)
                dialog.locator("button", has_text="삭제하기").click(timeout=5_000)
                deleted_after_confirm = wait_until(lambda: len(calendar_delete_calls) > before_deletes, 5_000, page)
            report.record(
                "calendar-delete-confirmation",
                dialog_visible and not_deleted_before_confirm and still_visible_before_confirm and still_visible_after_cancel and deleted_after_confirm,
                (
                    f"dialog_visible={dialog_visible}; before={before_deletes}; after={len(calendar_delete_calls)}; "
                    f"still_before={still_visible_before_confirm}; still_after_cancel={still_visible_after_cancel}; "
                    f"deleted_after_confirm={deleted_after_confirm}"
                ),
            )
        except Exception as exc:
            report.record("calendar-plugin-labels", False, repr(exc))
            report.record("calendar-naver-safe-options", False, repr(exc))
            report.record("calendar-wordpress-safe-options", False, repr(exc))
            report.record("calendar-delete-failure-stays-open", False, repr(exc))
            report.record("calendar-delete-confirmation", False, repr(exc))
    except Exception as exc:
        fail_png = screenshot(page, "right-panel-fail.png")
        report.record("right-panel-settings", False, f"{repr(exc)}; screenshot={fail_png}")
        report.record("right-panel-nlm", False, f"{repr(exc)}; screenshot={fail_png}")
        report.record("right-panel-nlm-quick-view", False, f"{repr(exc)}; screenshot={fail_png}")
        report.record("right-panel-action-guidance", False, f"{repr(exc)}; screenshot={fail_png}")
        report.record("right-panel-export-all", False, f"{repr(exc)}; screenshot={fail_png}")
        report.record("right-panel-rewrite-action", False, f"{repr(exc)}; screenshot={fail_png}")
        report.record("right-panel-recent-result-focus", False, f"{repr(exc)}; screenshot={fail_png}")
        report.record("right-panel-schedule-card", False, f"{repr(exc)}; screenshot={fail_png}")
        report.record("right-panel-quick-actions", False, f"{repr(exc)}; screenshot={fail_png}")
    finally:
        context.close()


def run_mobile_studio_suite(browser, report: QaReport) -> None:
    context = browser.new_context(viewport={"width": 390, "height": 844}, accept_downloads=True)
    context.add_init_script(
        """
        localStorage.setItem('insight-engine-onboarding-done', JSON.stringify(true));
        localStorage.setItem('insight-engine-selected-provider', JSON.stringify('chatmock'));
        localStorage.setItem('insight-engine-selected-model', JSON.stringify('chatmock/gpt-5.5'));
        localStorage.removeItem('insight-engine-reports');
        """
    )
    page = context.new_page()
    page.on("console", lambda msg: report.console_errors.append(f"[mobile] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[mobile] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("#url-input").wait_for(state="visible", timeout=60_000)
        trigger = page.locator("[data-testid='mobile-right-panel-trigger']")
        trigger.wait_for(state="visible", timeout=10_000)
        trigger_initial_label = trigger.get_attribute("aria-label", timeout=5_000) == "작업 패널 열기"
        trigger.click(timeout=10_000)
        drawer = page.locator("[data-testid='mobile-right-panel']")
        drawer.wait_for(state="visible", timeout=10_000)
        ok = drawer.locator("[data-testid='studio-right-panel']").count() > 0
        report.record("mobile-right-panel-drawer", ok, screenshot(page, "mobile-right-panel-drawer.png") if ok else drawer.inner_text(timeout=5_000)[:500])

        try:
            close = page.locator("[data-testid='mobile-right-panel-close']")
            title = page.locator("[data-testid='mobile-right-panel-title']")
            labelledby = drawer.get_attribute("aria-labelledby", timeout=5_000)
            initial_focus_ok = wait_until(
                lambda: close.evaluate("el => document.activeElement === el"),
                5_000,
                page,
            )
            semantic_ok = (
                drawer.get_attribute("role", timeout=5_000) == "dialog"
                and drawer.get_attribute("aria-modal", timeout=5_000) == "true"
                and bool(labelledby)
                and title.get_attribute("id", timeout=5_000) == labelledby
                and trigger.get_attribute("aria-expanded", timeout=5_000) == "true"
                and trigger.get_attribute("aria-label", timeout=5_000) == "작업 패널 닫기"
            )
            active_in_sheet = lambda: drawer.evaluate(
                """
                drawer => {
                    const sheet = drawer.querySelector('aside');
                    return !!sheet && sheet.contains(document.activeElement);
                }
                """
            )
            page.keyboard.press("Shift+Tab")
            backward_wrap_ok = wait_until(lambda: bool(active_in_sheet()), 3_000, page)
            focusable_count = drawer.evaluate(
                """
                drawer => {
                    const sheet = drawer.querySelector('aside');
                    if (!sheet) return 0;
                    const focusable = Array.from(sheet.querySelectorAll('button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])'))
                        .filter((element) => element.tabIndex >= 0);
                    if (focusable.length > 0) focusable[focusable.length - 1].focus();
                    return focusable.length;
                }
                """
            )
            page.keyboard.press("Tab")
            forward_wrap_ok = wait_until(lambda: close.evaluate("el => document.activeElement === el"), 3_000, page)
            trigger_focused_during_trap = trigger.evaluate("el => document.activeElement === el")
            focus_trap_ok = backward_wrap_ok and forward_wrap_ok and focusable_count > 1 and not trigger_focused_during_trap
            report.record(
                "mobile-right-panel-focus-trap",
                focus_trap_ok,
                (
                    "mobile right panel Tab and Shift+Tab focus stays inside the sheet"
                    if focus_trap_ok
                    else f"backward={backward_wrap_ok}; forward={forward_wrap_ok}; focusable={focusable_count}; trigger_focused={trigger_focused_during_trap}"
                ),
            )
            close.focus()
            page.keyboard.press("Escape")
            closed_ok = wait_until(lambda: drawer.count() == 0 or not drawer.is_visible(), 5_000, page)
            focus_returned = trigger.evaluate("el => document.activeElement === el")
            collapsed_ok = trigger.get_attribute("aria-expanded", timeout=5_000) == "false"
            trigger_closed_label = trigger.get_attribute("aria-label", timeout=5_000) == "작업 패널 열기"
            a11y_ok = trigger_initial_label and semantic_ok and initial_focus_ok and closed_ok and focus_returned and collapsed_ok and trigger_closed_label
            report.record(
                "mobile-right-panel-accessible",
                a11y_ok,
                (
                    "dialog semantics, trigger state labels, focus management, and Escape close are wired"
                    if a11y_ok
                    else f"initial_label={trigger_initial_label}; semantic={semantic_ok}; initial_focus={initial_focus_ok}; closed={closed_ok}; focus_returned={focus_returned}; collapsed={collapsed_ok}; closed_label={trigger_closed_label}"
                ),
            )
        except Exception as exc:
            report.record("mobile-right-panel-accessible", False, repr(exc))
            report.record("mobile-right-panel-focus-trap", False, repr(exc))
    except Exception as exc:
        fail_png = screenshot(page, "mobile-right-panel-drawer-fail.png")
        report.record("mobile-right-panel-drawer", False, f"{repr(exc)}; screenshot={fail_png}")
        report.record("mobile-right-panel-focus-trap", False, f"{repr(exc)}; screenshot={fail_png}")
    finally:
        context.close()


def run_onboarding_provider_accessibility_suite(browser, report: QaReport) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    context.add_init_script(
        """
        localStorage.removeItem('insight-engine-onboarding-done');
        localStorage.setItem('insight-engine-selected-provider', JSON.stringify('chatmock'));
        localStorage.setItem('insight-engine-selected-model', JSON.stringify('chatmock/gpt-5.5'));
        localStorage.removeItem('insight-engine-reports');
        """
    )
    page = context.new_page()
    page.on("console", lambda msg: report.console_errors.append(f"[onboarding-provider-accessible] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[onboarding-provider-accessible] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        dialog = page.locator("[role='dialog']", has_text="환영합니다").last
        dialog.wait_for(state="visible", timeout=60_000)
        group = dialog.locator("[data-testid='onboarding-provider-options']")
        selected = dialog.locator("[data-testid='onboarding-provider-chatmock']")
        start = dialog.get_by_role("button", name="시작하기")
        radio_count = group.locator("[role='radio']").count() if group.count() else 0
        ok = (
            dialog.get_attribute("aria-modal", timeout=5_000) == "true"
            and group.count() == 1
            and group.get_attribute("role", timeout=5_000) == "radiogroup"
            and group.get_attribute("aria-label", timeout=5_000) == "AI 프로바이더"
            and radio_count >= 1
            and selected.count() == 1
            and selected.get_attribute("role", timeout=5_000) == "radio"
            and selected.get_attribute("aria-checked", timeout=5_000) == "true"
            and start.count() == 1
        )
        report.record(
            "onboarding-provider-accessible",
            ok,
            (
                "onboarding provider choices expose radiogroup/radio selected state"
                if ok
                else f"group={group.count()}; role={group.get_attribute('role') if group.count() else None}; label={group.get_attribute('aria-label') if group.count() else None}; radios={radio_count}; selected={selected.count()}; selected_role={selected.get_attribute('role') if selected.count() else None}; selected_checked={selected.get_attribute('aria-checked') if selected.count() else None}; start={start.count()}"
            ),
        )
    except Exception as exc:
        fail_png = screenshot(page, "onboarding-provider-accessible-fail.png")
        report.record("onboarding-provider-accessible", False, f"{repr(exc)}; screenshot={fail_png}")
    finally:
        context.close()


def run_new_analysis_filter_reset_suite(browser, report: QaReport) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    seed_menu_context(context)
    page = context.new_page()
    page.on("console", lambda msg: report.console_errors.append(f"[new-analysis-filter] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[new-analysis-filter] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("[data-report-id]").first.wait_for(state="visible", timeout=60_000)
        search = page.locator("[data-testid='studio-result-toolbar'] input[type='search']").first
        search.fill("no matching result query")
        filtered_to_zero = wait_until(
            lambda: "필터 결과 0개" in page.locator("[data-testid='studio-result-toolbar']").inner_text(timeout=2_000),
            5_000,
            page,
        )
        page.get_by_role("button", name="새 분석").click(timeout=10_000)
        cleared = wait_until(lambda: search.input_value(timeout=2_000) == "", 5_000, page)
        visible_after_reset = wait_until(
            lambda: page.locator("[data-report-id]").count() > 0
            and page.locator("[data-report-id]").first.is_visible(),
            5_000,
            page,
        )
        toolbar_text = page.locator("[data-testid='studio-result-toolbar']").inner_text(timeout=5_000)
        report.record(
            "new-analysis-clears-result-filters",
            filtered_to_zero and cleared and visible_after_reset and "필터 결과 1개" in toolbar_text,
            (
                screenshot(page, "new-analysis-clears-result-filters.png")
                if filtered_to_zero and cleared and visible_after_reset and "필터 결과 1개" in toolbar_text
                else f"filtered_to_zero={filtered_to_zero}; cleared={cleared}; visible={visible_after_reset}; toolbar={toolbar_text[:300]!r}; search={search.input_value(timeout=2_000)!r}"
            ),
        )
    except Exception as exc:
        fail_png = screenshot(page, "new-analysis-clears-result-filters-fail.png")
        report.record("new-analysis-clears-result-filters", False, f"{repr(exc)}; screenshot={fail_png}")
    finally:
        context.close()


def run_result_toolbar_accessibility_suite(browser, report: QaReport) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    seed_menu_context(context)
    page = context.new_page()
    page.on("console", lambda msg: report.console_errors.append(f"[result-toolbar-a11y] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[result-toolbar-a11y] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("[data-report-id]").first.wait_for(state="visible", timeout=60_000)
        toolbar = page.locator("[data-testid='studio-result-toolbar']")
        title = page.locator("[data-testid='studio-result-toolbar-title']")
        summary = page.locator("[data-testid='studio-result-toolbar-summary']")
        filter_panel = page.locator("[data-testid='result-toolbar-filter-panel']")
        empty_notice = page.locator("[data-testid='result-toolbar-empty-notice']")
        ok = (
            toolbar.get_attribute("role", timeout=5_000) == "region"
            and toolbar.get_attribute("aria-labelledby", timeout=5_000) == "studio-result-toolbar-title"
            and title.get_attribute("id", timeout=5_000) == "studio-result-toolbar-title"
            and "생성 결과 관리" in title.inner_text(timeout=5_000)
            and summary.get_attribute("id", timeout=5_000) == "studio-result-toolbar-summary"
            and summary.get_attribute("role", timeout=5_000) == "status"
            and summary.get_attribute("aria-live", timeout=5_000) == "polite"
            and "전체 결과 1개" in summary.inner_text(timeout=5_000)
            and filter_panel.get_attribute("role", timeout=5_000) == "group"
            and filter_panel.get_attribute("aria-label", timeout=5_000) == "결과 필터"
            and empty_notice.count() == 0
        )
        report.record(
            "studio-result-toolbar-accessible",
            ok,
            "result toolbar region, live summary, and filter group are accessible" if ok else toolbar.inner_text(timeout=5_000)[:300],
        )
    except Exception as exc:
        report.record("studio-result-toolbar-accessible", False, repr(exc))
    finally:
        context.close()


def run_result_filter_accessibility_suite(browser, report: QaReport) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    seed_menu_context(context)
    page = context.new_page()
    page.on("console", lambda msg: report.console_errors.append(f"[result-filter-a11y] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[result-filter-a11y] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("[data-report-id]").first.wait_for(state="visible", timeout=60_000)
        search = page.locator("[data-testid='result-filter-search']")
        search_help = page.locator("[data-testid='result-filter-search-help']")
        style_trigger = page.locator("[data-testid='result-filter-style-trigger']")
        style_help = page.locator("[data-testid='result-filter-style-help']")
        summary = page.locator("[data-testid='studio-result-toolbar-summary']")
        initial_ok = (
            search.get_attribute("type", timeout=5_000) == "search"
            and search.get_attribute("aria-label", timeout=5_000) == "결과 검색"
            and search.get_attribute("aria-describedby", timeout=5_000) == "result-filter-search-help"
            and search_help.get_attribute("id", timeout=5_000) == "result-filter-search-help"
            and "제목과 본문" in search_help.inner_text(timeout=5_000)
            and style_trigger.get_attribute("aria-label", timeout=5_000) == "스타일 필터"
            and style_trigger.get_attribute("aria-describedby", timeout=5_000) == "result-filter-style-help"
            and style_help.get_attribute("id", timeout=5_000) == "result-filter-style-help"
            and "산출물 스타일" in style_help.inner_text(timeout=5_000)
        )
        search.fill("no matching result query", timeout=10_000)
        filtered_ok = wait_until(lambda: "필터 결과 0개" in summary.inner_text(timeout=1_000), 5_000, page)
        ok = initial_ok and filtered_ok
        report.record(
            "result-filter-accessible-controls",
            ok,
            "result search and style filter labels/help are accessible and filtering updates summary" if ok else f"initial={initial_ok}; filtered={filtered_ok}",
        )
    except Exception as exc:
        report.record("result-filter-accessible-controls", False, repr(exc))
    finally:
        context.close()


def run_view_mode_accessibility_suite(browser, report: QaReport) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    seed_menu_context(context)
    page = context.new_page()
    page.on("console", lambda msg: report.console_errors.append(f"[view-mode-a11y] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[view-mode-a11y] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("[data-report-id]").first.wait_for(state="visible", timeout=60_000)
        group = page.locator("[data-testid='result-view-mode-selector']")
        compact = page.locator("[data-testid='result-view-mode-compact']")
        full = page.locator("[data-testid='result-view-mode-full']")
        timeline = page.locator("[data-testid='result-view-mode-timeline']")
        initial_ok = (
            group.get_attribute("role", timeout=5_000) == "radiogroup"
            and group.get_attribute("aria-label", timeout=5_000) == "뷰 모드 선택"
            and compact.get_attribute("role", timeout=5_000) == "radio"
            and full.get_attribute("aria-checked", timeout=5_000) == "true"
            and timeline.get_attribute("aria-checked", timeout=5_000) == "false"
        )
        full.focus(timeout=10_000)
        page.keyboard.press("ArrowRight")
        timeline_ok = wait_until(
            lambda: timeline.get_attribute("aria-checked", timeout=1_000) == "true"
            and timeline.evaluate("el => document.activeElement === el"),
            5_000,
            page,
        )
        page.keyboard.press("Home")
        compact_ok = wait_until(
            lambda: compact.get_attribute("aria-checked", timeout=1_000) == "true"
            and compact.evaluate("el => document.activeElement === el"),
            5_000,
            page,
        )
        ok = initial_ok and timeline_ok and compact_ok
        report.record(
            "result-view-mode-accessible",
            ok,
            "view mode radiogroup labels and keyboard navigation update selection" if ok else f"initial={initial_ok}; timeline={timeline_ok}; compact={compact_ok}",
        )
    except Exception as exc:
        report.record("result-view-mode-accessible", False, repr(exc))
    finally:
        context.close()


def run_generate_dock_minimums_suite(browser, report: QaReport) -> None:
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
    page.on("console", lambda msg: report.console_errors.append(f"[dock-minimums] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[dock-minimums] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("#url-input").wait_for(state="visible", timeout=60_000)
        page.locator("#url-input").fill("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        page.locator("#url-input").press("Enter")
        wait_until(lambda: "소스 1개" in page.locator("[data-testid='generate-dock-summary']").inner_text(timeout=1_000), 10_000, page)

        combined_mode = page.locator("[data-testid='blueprint-mode-combined']")
        fusion_mode = page.locator("[data-testid='blueprint-mode-fusion']")
        individual_mode = page.locator("[data-testid='blueprint-mode-individual']")
        mode_hint = page.locator("[data-testid='blueprint-mode-hint']")
        dock_summary = page.locator("[data-testid='generate-dock-summary']").inner_text(timeout=5_000)
        dock_button = page.locator("[data-testid='generate-dock-button']")
        hint_text = mode_hint.inner_text(timeout=5_000) if mode_hint.count() > 0 else ""
        state = {
            "combined_disabled": combined_mode.is_disabled(timeout=5_000),
            "fusion_disabled": fusion_mode.is_disabled(timeout=5_000),
            "individual_checked": individual_mode.get_attribute("aria-checked", timeout=5_000) == "true",
            "hint": hint_text,
            "dock_summary": dock_summary,
            "dock_disabled": dock_button.is_disabled(timeout=5_000),
            "dock_text": dock_button.inner_text(timeout=5_000),
        }

        ok = (
            state["combined_disabled"]
            and state["fusion_disabled"]
            and state["individual_checked"]
            and "URL 소스 2개 이상" in hint_text
            and "통합/퓨전" in hint_text
            and "모드 개별 생성" in dock_summary
            and not state["dock_disabled"]
            and "1개 소스로" in state["dock_text"]
        )
        report.record(
            "generate-dock-url-mode-minimums",
            ok,
            screenshot(page, "generate-dock-url-mode-minimums.png") if ok else str(state),
        )
    except Exception as exc:
        fail_png = screenshot(page, "generate-dock-url-mode-minimums-fail.png")
        report.record("generate-dock-url-mode-minimums", False, f"{repr(exc)}; screenshot={fail_png}")
    finally:
        context.close()


def run_generate_dock_accessibility_suite(browser, report: QaReport) -> None:
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
    page.on("console", lambda msg: report.console_errors.append(f"[dock-a11y] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[dock-a11y] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("#url-input").wait_for(state="visible", timeout=60_000)
        dock = page.locator("[data-testid='generate-dock']")
        status = page.locator("[data-testid='generate-dock-status']")
        summary = page.locator("[data-testid='generate-dock-summary']")
        button = page.locator("[data-testid='generate-dock-button']")
        initial_ok = (
            dock.get_attribute("role", timeout=5_000) == "region"
            and dock.get_attribute("aria-label", timeout=5_000) == "생성 실행"
            and status.get_attribute("id", timeout=5_000) == "generate-dock-status"
            and summary.get_attribute("id", timeout=5_000) == "generate-dock-summary"
            and button.get_attribute("aria-describedby", timeout=5_000) == "generate-dock-status generate-dock-summary"
            and button.get_attribute("aria-label", timeout=5_000) == button.inner_text(timeout=5_000)
            and button.is_disabled(timeout=5_000)
        )
        page.locator("#url-input").fill("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        page.locator("#url-input").press("Enter")
        wait_until(lambda: "소스 1개" in summary.inner_text(timeout=1_000), 10_000, page)
        changed_ok = (
            "생성 준비 완료" in status.inner_text(timeout=5_000)
            and "URL 소스" in summary.inner_text(timeout=5_000)
            and "소스 1개" in summary.inner_text(timeout=5_000)
            and not button.is_disabled(timeout=5_000)
            and button.get_attribute("aria-label", timeout=5_000) == button.inner_text(timeout=5_000)
        )
        ok = initial_ok and changed_ok
        report.record(
            "generate-dock-accessible-action",
            ok,
            "dock region, live status, summary, and action button are linked" if ok else f"initial={initial_ok}; changed={changed_ok}",
        )
    except Exception as exc:
        report.record("generate-dock-accessible-action", False, repr(exc))
    finally:
        context.close()


def run_empty_workbench_accessibility_suite(browser, report: QaReport) -> None:
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
    page.on("console", lambda msg: report.console_errors.append(f"[empty-workbench-a11y] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[empty-workbench-a11y] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("#url-input").wait_for(state="visible", timeout=60_000)
        empty = page.locator("[data-testid='studio-empty-state']")
        title = page.locator("[data-testid='studio-empty-state-title']")
        steps = page.locator("[data-testid='studio-empty-state-steps']")
        action = page.locator("[data-testid='studio-empty-state-focus-source']")
        initial_ok = (
            empty.get_attribute("role", timeout=5_000) == "region"
            and empty.get_attribute("aria-labelledby", timeout=5_000) == "studio-empty-state-title"
            and title.get_attribute("id", timeout=5_000) == "studio-empty-state-title"
            and "아직 결과가 없습니다" in title.inner_text(timeout=5_000)
            and steps.get_attribute("role", timeout=5_000) == "list"
            and steps.get_attribute("aria-label", timeout=5_000) == "진행 단계"
            and page.locator("[data-testid^='studio-empty-state-step-']").count() == 4
            and page.locator("[data-testid='studio-empty-state-step-0']").get_attribute("role", timeout=5_000) == "listitem"
            and page.locator("[data-testid='studio-empty-state-step-0']").get_attribute("aria-label", timeout=5_000).startswith("1. 소스 입력")
            and action.get_attribute("aria-label", timeout=5_000) == "소스 입력으로 이동"
        )
        action.click(timeout=10_000)
        focus_ok = wait_until(lambda: page.locator("#url-input").evaluate("el => document.activeElement === el"), 3_000, page)
        ok = initial_ok and focus_ok
        report.record(
            "studio-empty-state-accessible",
            ok,
            "empty workbench region, step list, and focus action are accessible" if ok else f"initial={initial_ok}; focus={focus_ok}",
        )
    except Exception as exc:
        report.record("studio-empty-state-accessible", False, repr(exc))
    finally:
        context.close()


def run_help_tour_entrypoint_suite(browser, report: QaReport) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    context.add_init_script(
        """
        localStorage.setItem('insight-engine-onboarding-done', JSON.stringify(true));
        localStorage.setItem('insight-engine-selected-provider', JSON.stringify('chatmock'));
        localStorage.setItem('insight-engine-selected-model', JSON.stringify('chatmock/gpt-5.5'));
        localStorage.removeItem('insight-engine-reports');
        localStorage.removeItem('ie_tour_done');
        """
    )
    page = context.new_page()
    page.on("console", lambda msg: report.console_errors.append(f"[help-tour-entrypoint] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[help-tour-entrypoint] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("#url-input").wait_for(state="visible", timeout=60_000)

        trigger = page.locator("[data-testid='header-help-trigger']")
        initial_ok = (
            trigger.count() == 1
            and trigger.get_attribute("aria-label", timeout=5_000) == "도움말 열기"
            and trigger.get_attribute("aria-haspopup", timeout=5_000) == "dialog"
            and trigger.get_attribute("aria-controls", timeout=5_000) == "help-panel"
            and trigger.get_attribute("aria-expanded", timeout=5_000) == "false"
        )
        trigger.click(timeout=10_000)

        panel = page.locator("[data-testid='help-panel']")
        start = page.locator("[data-testid='help-start-tour']")
        panel.wait_for(state="visible", timeout=10_000)
        start.wait_for(state="visible", timeout=10_000)
        header_open_ok = wait_until(
            lambda: trigger.get_attribute("aria-label", timeout=1_000) == "도움말 닫기"
            and trigger.get_attribute("aria-expanded", timeout=1_000) == "true",
            5_000,
            page,
        )
        panel_ok = (
            panel.is_visible(timeout=5_000)
            and panel.get_attribute("id", timeout=5_000) == "help-panel"
            and panel.get_attribute("role", timeout=5_000) == "dialog"
            and panel.get_attribute("aria-modal", timeout=5_000) == "true"
            and panel.get_attribute("aria-labelledby", timeout=5_000) == "help-panel-title"
            and header_open_ok
            and start.get_attribute("aria-label", timeout=5_000) == "가이드 투어 시작"
        )
        start.click(timeout=10_000)

        tour = page.locator("[data-testid='guided-tour-dialog']")
        tour_ok = (
            tour.is_visible(timeout=5_000)
            and tour.get_attribute("role", timeout=5_000) == "dialog"
            and tour.get_attribute("aria-modal", timeout=5_000) == "true"
            and page.locator("[data-testid='help-panel']").count() == 0
            and "URL 입력" in tour.inner_text(timeout=5_000)
        )
        ok = initial_ok and panel_ok and tour_ok
        report.record(
            "help-tour-entrypoint",
            ok,
            screenshot(page, "help-tour-entrypoint.png") if ok else f"initial={initial_ok}; panel={panel_ok}; tour={tour_ok}",
        )
    except Exception as exc:
        fail_png = screenshot(page, "help-tour-entrypoint-fail.png")
        report.record("help-tour-entrypoint", False, f"{repr(exc)}; screenshot={fail_png}")
    finally:
        context.close()


def run_help_panel_accessible_close_suite(browser, report: QaReport) -> None:
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
    page.on("console", lambda msg: report.console_errors.append(f"[help-panel-close] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[help-panel-close] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("#url-input").wait_for(state="visible", timeout=60_000)
        trigger = page.locator("[data-testid='header-help-trigger']")
        trigger.click(timeout=10_000)
        panel = page.locator("[data-testid='help-panel']")
        close_button = page.locator("[data-testid='help-panel-close']")
        panel.wait_for(state="visible", timeout=10_000)
        focus_initial_ok = wait_until(
            lambda: close_button.count() == 1 and close_button.evaluate("el => document.activeElement === el"),
            5_000,
            page,
        )
        page.keyboard.press("Escape")
        closed_ok = wait_until(lambda: panel.count() == 0 or not panel.is_visible(), 5_000, page)
        focus_returned_ok = wait_until(lambda: trigger.evaluate("el => document.activeElement === el"), 5_000, page)
        ok = focus_initial_ok and closed_ok and focus_returned_ok
        report.record(
            "help-panel-accessible-close",
            ok,
            "help panel initial focus, Escape close, and trigger focus return are wired" if ok else f"focus_initial={focus_initial_ok}; closed={closed_ok}; focus_returned={focus_returned_ok}",
        )
    except Exception as exc:
        fail_png = screenshot(page, "help-panel-accessible-close-fail.png")
        report.record("help-panel-accessible-close", False, f"{repr(exc)}; screenshot={fail_png}")
    finally:
        context.close()


def run_help_panel_focus_trap_suite(browser, report: QaReport) -> None:
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
    page.on("console", lambda msg: report.console_errors.append(f"[help-panel-focus-trap] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[help-panel-focus-trap] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("#url-input").wait_for(state="visible", timeout=60_000)
        page.locator("[data-testid='header-help-trigger']").click(timeout=10_000)
        panel = page.locator("[data-testid='help-panel']")
        close_button = page.locator("[data-testid='help-panel-close']")
        panel.wait_for(state="visible", timeout=10_000)
        wait_until(lambda: close_button.evaluate("el => document.activeElement === el"), 5_000, page)

        active_inside = lambda: panel.evaluate("panel => panel.contains(document.activeElement)")
        page.keyboard.press("Shift+Tab")
        backward_wrap_ok = wait_until(active_inside, 3_000, page)
        forward_sequence: list[bool] = []
        for _ in range(8):
            page.keyboard.press("Tab")
            page.wait_for_timeout(50)
            forward_sequence.append(bool(active_inside()))
        forward_trap_ok = all(forward_sequence)
        trigger_focused = page.locator("[data-testid='header-help-trigger']").evaluate("el => document.activeElement === el")
        ok = backward_wrap_ok and forward_trap_ok and not trigger_focused
        report.record(
            "help-panel-focus-trap",
            ok,
            "help panel Tab and Shift+Tab focus stays inside dialog" if ok else f"backward={backward_wrap_ok}; forward={forward_sequence}; trigger_focused={trigger_focused}",
        )
    except Exception as exc:
        fail_png = screenshot(page, "help-panel-focus-trap-fail.png")
        report.record("help-panel-focus-trap", False, f"{repr(exc)}; screenshot={fail_png}")
    finally:
        context.close()


def run_guided_tour_accessible_close_suite(browser, report: QaReport) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    context.add_init_script(
        """
        localStorage.setItem('insight-engine-onboarding-done', JSON.stringify(true));
        localStorage.setItem('insight-engine-selected-provider', JSON.stringify('chatmock'));
        localStorage.setItem('insight-engine-selected-model', JSON.stringify('chatmock/gpt-5.5'));
        localStorage.removeItem('insight-engine-reports');
        localStorage.removeItem('ie_tour_done');
        """
    )
    page = context.new_page()
    page.on("console", lambda msg: report.console_errors.append(f"[guided-tour-close] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[guided-tour-close] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("#url-input").wait_for(state="visible", timeout=60_000)
        trigger = page.locator("[data-testid='header-help-trigger']")
        trigger.click(timeout=10_000)
        start = page.locator("[data-testid='help-start-tour']")
        start.wait_for(state="visible", timeout=10_000)
        start.click(timeout=10_000)

        tour = page.locator("[data-testid='guided-tour-dialog']")
        close_button = page.locator("[data-testid='guided-tour-close']")
        tour.wait_for(state="visible", timeout=10_000)
        focus_initial_ok = wait_until(
            lambda: close_button.count() == 1 and close_button.evaluate("el => document.activeElement === el"),
            5_000,
            page,
        )
        page.keyboard.press("Escape")
        closed_ok = wait_until(lambda: tour.count() == 0 or not tour.is_visible(), 5_000, page)
        focus_returned_ok = wait_until(lambda: trigger.evaluate("el => document.activeElement === el"), 5_000, page)
        ok = focus_initial_ok and closed_ok and focus_returned_ok
        report.record(
            "guided-tour-accessible-close",
            ok,
            "guided tour initial focus, Escape close, and help trigger focus return are wired" if ok else f"focus_initial={focus_initial_ok}; closed={closed_ok}; focus_returned={focus_returned_ok}",
        )
    except Exception as exc:
        fail_png = screenshot(page, "guided-tour-accessible-close-fail.png")
        report.record("guided-tour-accessible-close", False, f"{repr(exc)}; screenshot={fail_png}")
    finally:
        context.close()


def run_guided_tour_focus_trap_suite(browser, report: QaReport) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    context.add_init_script(
        """
        localStorage.setItem('insight-engine-onboarding-done', JSON.stringify(true));
        localStorage.setItem('insight-engine-selected-provider', JSON.stringify('chatmock'));
        localStorage.setItem('insight-engine-selected-model', JSON.stringify('chatmock/gpt-5.5'));
        localStorage.removeItem('insight-engine-reports');
        localStorage.removeItem('ie_tour_done');
        """
    )
    page = context.new_page()
    page.on("console", lambda msg: report.console_errors.append(f"[guided-tour-focus-trap] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[guided-tour-focus-trap] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("#url-input").wait_for(state="visible", timeout=60_000)
        trigger = page.locator("[data-testid='header-help-trigger']")
        panel = page.locator("[data-testid='help-panel']")
        opened = False
        for attempt in range(3):
            if attempt > 0:
                page.reload(wait_until="domcontentloaded", timeout=60_000)
                page.locator("#url-input").wait_for(state="visible", timeout=60_000)
                trigger = page.locator("[data-testid='header-help-trigger']")
                panel = page.locator("[data-testid='help-panel']")
            page.keyboard.press("Escape")
            trigger.scroll_into_view_if_needed(timeout=10_000)
            trigger.click(timeout=10_000, force=True)
            opened = wait_until(lambda: panel.count() == 1 and panel.is_visible(), 5_000, page)
            if opened:
                break
            page.evaluate("document.querySelector('[data-testid=\"header-help-trigger\"]')?.click()")
            opened = wait_until(lambda: panel.count() == 1 and panel.is_visible(), 5_000, page)
            if opened:
                break
        if not opened:
            panel.wait_for(state="visible", timeout=10_000)
        start = page.locator("[data-testid='help-start-tour']")
        start.wait_for(state="visible", timeout=10_000)
        start.click(timeout=10_000)

        tour = page.locator("[data-testid='guided-tour-dialog']")
        close_button = page.locator("[data-testid='guided-tour-close']")
        tour.wait_for(state="visible", timeout=10_000)
        wait_until(lambda: close_button.evaluate("el => document.activeElement === el"), 5_000, page)

        active_inside = lambda: tour.evaluate("tour => tour.contains(document.activeElement)")
        page.keyboard.press("Shift+Tab")
        backward_wrap_ok = wait_until(active_inside, 3_000, page)
        forward_sequence: list[bool] = []
        for _ in range(8):
            page.keyboard.press("Tab")
            page.wait_for_timeout(50)
            forward_sequence.append(bool(active_inside()))
        forward_trap_ok = all(forward_sequence)
        trigger_focused = trigger.evaluate("el => document.activeElement === el")
        ok = backward_wrap_ok and forward_trap_ok and not trigger_focused
        report.record(
            "guided-tour-focus-trap",
            ok,
            "guided tour Tab and Shift+Tab focus stays inside dialog" if ok else f"backward={backward_wrap_ok}; forward={forward_sequence}; trigger_focused={trigger_focused}",
        )
    except Exception as exc:
        fail_png = screenshot(page, "guided-tour-focus-trap-fail.png")
        report.record("guided-tour-focus-trap", False, f"{repr(exc)}; screenshot={fail_png}")
    finally:
        context.close()


def run_non_url_fusion_progress_suite(browser, report: QaReport) -> None:
    captured: list[dict[str, Any]] = []
    pending_routes: list[Any] = []
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    context.add_init_script(
        """
        localStorage.setItem('insight-engine-onboarding-done', JSON.stringify(true));
        localStorage.setItem('insight-engine-selected-provider', JSON.stringify('chatmock'));
        localStorage.setItem('insight-engine-selected-model', JSON.stringify('chatmock/gpt-5.5'));
        localStorage.removeItem('insight-engine-reports');
        """
    )

    def hold_generate(route) -> None:
        data = route.request.post_data_json
        if callable(data):
            data = data()
        captured.append(data if isinstance(data, dict) else {})
        pending_routes.append(route)

    context.route("**/generate", hold_generate)
    page = context.new_page()
    page.on("console", lambda msg: report.console_errors.append(f"[non-url-fusion-progress] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[non-url-fusion-progress] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("#url-input").fill("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        page.locator("#url-input").press("Enter")
        page.locator("#url-input").fill("https://www.youtube.com/watch?v=wr4nCMUy1dk")
        page.locator("#url-input").press("Enter")
        wait_until(lambda: "소스 2개" in page.locator("[data-testid='generate-dock-summary']").inner_text(timeout=1_000), 10_000, page)
        page.locator("[data-testid='blueprint-mode-fusion']").click(timeout=10_000)
        page.locator("[data-testid='source-tab-text']").click(timeout=10_000)
        page.locator("[data-testid='text-source-panel'] textarea").fill(
            "Fusion progress should not be shown for direct text generation even when URL fusion mode was selected before switching sources."
        )
        page.locator("[data-testid='generate-dock-button']").click(timeout=10_000)
        request_seen = wait_until(lambda: len(pending_routes) > 0, 10_000, page)
        progress = page.get_by_text("퓨전 분석 진행 중", exact=False)
        progress_visible = progress.count() > 0 and progress.first.is_visible(timeout=1_000)
        ok = request_seen and not progress_visible
        report.record(
            "non-url-hides-fusion-progress",
            ok,
            screenshot(page, "non-url-hides-fusion-progress.png") if ok else f"request_seen={request_seen}; progress_visible={progress_visible}",
        )
        dock = page.locator("[data-testid='generate-dock']")
        dock_button = page.locator("[data-testid='generate-dock-button']")
        dock_text = dock.inner_text(timeout=5_000)
        button_text = dock_button.inner_text(timeout=5_000)
        dock_busy = dock.get_attribute("aria-busy") == "true"
        loading_copy_ok = request_seen and dock_busy and "생성 중" in dock_text and "생성 중" in button_text
        report.record(
            "generate-dock-loading-copy",
            loading_copy_ok,
            screenshot(page, "generate-dock-loading-copy.png") if loading_copy_ok else f"busy={dock_busy}; dock={dock_text!r}; button={button_text!r}",
        )
    except Exception as exc:
        fail_png = screenshot(page, "non-url-hides-fusion-progress-fail.png")
        report.record("non-url-hides-fusion-progress", False, f"{repr(exc)}; screenshot={fail_png}")
    finally:
        for route in pending_routes:
            try:
                route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({
                        "title": "QA direct text",
                        "content": "# QA direct text",
                        "html": "<h1>QA direct text</h1>",
                        "usage": {"total_tokens": 1},
                        "elapsed_time": 0.1,
                        "transcript_source": "direct_input",
                        "prompt": "qa",
                        "cached": False,
                        "comment_summary_included": False,
                    }, ensure_ascii=False),
                )
            except Exception:
                pass
        context.close()

def run_direct_text_advanced_request_suite(browser, report: QaReport) -> None:
    captured: list[dict[str, Any]] = []
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    context.add_init_script(
        """
        localStorage.setItem('insight-engine-onboarding-done', JSON.stringify(true));
        localStorage.setItem('insight-engine-selected-provider', JSON.stringify('chatmock'));
        localStorage.setItem('insight-engine-selected-model', JSON.stringify('chatmock/gpt-5.5'));
        localStorage.removeItem('insight-engine-reports');
        """
    )

    def generate(route) -> None:
        data = route.request.post_data_json
        if callable(data):
            data = data()
        captured.append(data if isinstance(data, dict) else {})
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "title": "QA 고급 옵션 요청",
                "content": "# QA 고급 옵션 요청\n\n요청 옵션 검증 결과입니다.",
                "html": "<h1>QA 고급 옵션 요청</h1>",
                "usage": {"total_tokens": 12},
                "elapsed_time": 0.1,
                "transcript_source": "direct_input",
                "prompt": "qa advanced request",
                "cached": False,
                "comment_summary_included": False,
            }, ensure_ascii=False),
        )

    context.route("**/generate", generate)
    page = context.new_page()
    page.on("console", lambda msg: report.console_errors.append(f"[direct-advanced] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[direct-advanced] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("[data-testid='source-tab-text']").click(timeout=10_000)
        textarea = page.locator("textarea").first
        textarea.fill(
            "Direct text advanced option QA source. "
            "This text is intentionally longer than fifty characters so generation is enabled."
        )
        page.locator("[data-testid='blueprint-detail-level']").get_by_text("심층").click(timeout=10_000)
        page.locator("[data-testid='blueprint-web-search']").click(timeout=10_000)
        page.locator("[data-testid='blueprint-agent-mode']").click(timeout=10_000)
        page.locator("[data-testid='generate-dock-button']").click(timeout=10_000)

        sent = wait_until(lambda: len(captured) > 0, 10_000, page)
        payload = captured[-1] if captured else {}
        ok = (
            sent
            and payload.get("detail_level") == "deep"
            and payload.get("web_search") is True
            and payload.get("agent_mode") is True
        )
        report.record(
            "direct-text-advanced-request-options",
            ok,
            f"payload={payload}" if ok else f"missing advanced options; payload={payload}",
        )
    except Exception as exc:
        report.record("direct-text-advanced-request-options", False, repr(exc))
    finally:
        context.close()


def run_single_url_failure_retains_source_suite(browser, report: QaReport) -> None:
    captured: dict[str, list[dict[str, Any]]] = {"direct": [], "batch": []}
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    context.add_init_script(
        """
        localStorage.setItem('insight-engine-onboarding-done', JSON.stringify(true));
        localStorage.setItem('insight-engine-selected-provider', JSON.stringify('chatmock'));
        localStorage.setItem('insight-engine-selected-model', JSON.stringify('chatmock/gpt-5.5'));
        localStorage.removeItem('insight-engine-reports');
        """
    )

    def direct(route) -> None:
        data = route.request.post_data_json
        if callable(data):
            data = data()
        captured["direct"].append(data if isinstance(data, dict) else {})
        route.fulfill(
            status=500,
            content_type="application/json",
            body=json.dumps({"detail": "QA forced single URL failure"}, ensure_ascii=False),
        )

    def batch(route) -> None:
        data = route.request.post_data_json
        if callable(data):
            data = data()
        captured["batch"].append(data if isinstance(data, dict) else {})
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"success": True, "results": []}, ensure_ascii=False),
        )

    context.route("**/generate-batch", batch)
    context.route("**/generate", direct)
    page = context.new_page()
    page.on("pageerror", lambda exc: report.console_errors.append(f"[single-url-failure] {exc}"))

    try:
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("#url-input").fill(url)
        page.locator("#url-input").press("Enter")
        wait_until(lambda: "소스 1개" in page.locator("[data-testid='generate-dock-summary']").inner_text(timeout=1_000), 10_000, page)
        page.locator("[data-testid='generate-dock-button']").click(timeout=10_000)

        sent = wait_until(lambda: len(captured["direct"]) > 0, 10_000, page)
        page.wait_for_timeout(500)
        summary = page.locator("[data-testid='generate-dock-summary']").inner_text(timeout=10_000)
        direct_payload = captured["direct"][-1] if captured["direct"] else {}
        ok = (
            sent
            and len(captured["batch"]) == 0
            and direct_payload.get("url") == url
            and "소스 1개" in summary
            and page.locator("[data-report-id]").count() == 0
        )
        report.record(
            "single-url-failure-retains-source",
            ok,
            (
                f"payload={direct_payload}; summary={summary!r}"
                if ok
                else f"direct={captured['direct']}; batch={captured['batch']}; summary={summary!r}; screenshot={screenshot(page, 'single-url-failure-retains-source.png')}"
            ),
        )
    except Exception as exc:
        report.record("single-url-failure-retains-source", False, repr(exc))
    finally:
        context.close()


def run_url_chip_reorder_suite(browser, report: QaReport) -> None:
    captured: list[dict[str, Any]] = []
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    context.add_init_script(
        """
        localStorage.setItem('insight-engine-onboarding-done', JSON.stringify(true));
        localStorage.setItem('insight-engine-selected-provider', JSON.stringify('chatmock'));
        localStorage.setItem('insight-engine-selected-model', JSON.stringify('chatmock/gpt-5.5'));
        localStorage.removeItem('insight-engine-reports');
        """
    )

    def batch(route) -> None:
        data = route.request.post_data_json
        if callable(data):
            data = data()
        payload = data if isinstance(data, dict) else {}
        captured.append(payload)
        urls = payload.get("urls") if isinstance(payload.get("urls"), list) else []
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "success": True,
                "results": [
                    {"success": True, "url": url, "title": f"QA reordered {idx}", "content": "# QA reordered", "html": "<h1>QA reordered</h1>"}
                    for idx, url in enumerate(urls)
                ],
                "total_processed": len(urls),
                "successful": len(urls),
                "failed": 0,
            }, ensure_ascii=False),
        )

    context.route("**/generate-batch", batch)
    page = context.new_page()
    page.on("console", lambda msg: report.console_errors.append(f"[url-chip-reorder] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[url-chip-reorder] {exc}"))

    try:
        first = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        second = "https://www.youtube.com/watch?v=wr4nCMUy1dk"
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("#url-input").fill(first)
        page.locator("#url-input").press("Enter")
        page.locator("#url-input").fill(second)
        page.locator("#url-input").press("Enter")
        wait_until(lambda: page.locator("[draggable='true']").count() >= 2, 10_000, page)

        chips = page.locator("[draggable='true']")
        chips.nth(1).drag_to(chips.nth(0), timeout=10_000)
        page.locator("[data-testid='generate-dock-button']").click(timeout=10_000)

        sent = wait_until(lambda: len(captured) > 0, 10_000, page)
        payload = captured[-1] if captured else {}
        urls = payload.get("urls") if isinstance(payload.get("urls"), list) else []
        ok = sent and urls[:2] == [second, first]
        report.record(
            "url-chip-drag-reorder",
            ok,
            f"urls={urls}" if ok else f"urls={urls}; expected={[second, first]}",
        )
    except Exception as exc:
        report.record("url-chip-drag-reorder", False, repr(exc))
    finally:
        context.close()


def run_drop_bulk_url_limit_suite(browser, report: QaReport) -> None:
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
    page.on("console", lambda msg: report.console_errors.append(f"[drop-bulk-url-limit] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[drop-bulk-url-limit] {exc}"))

    try:
        urls = [f"https://example.com/source-{idx}" for idx in range(12)]
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("#url-input").wait_for(state="visible", timeout=60_000)
        page.evaluate(
            """(text) => {
                const data = new DataTransfer();
                data.setData('text/plain', text);
                const target = document.querySelector('main') || document.body;
                target.dispatchEvent(new DragEvent('dragenter', { bubbles: true, dataTransfer: data }));
                target.dispatchEvent(new DragEvent('drop', { bubbles: true, dataTransfer: data }));
            }""",
            "\n".join(urls),
        )
        wait_until(lambda: page.locator("[draggable='true']").count() >= 10, 10_000, page)
        chip_count = page.locator("[draggable='true']").count()
        summary = page.locator("[data-testid='generate-dock-summary']").inner_text(timeout=10_000)
        ok = chip_count == 10 and "소스 10개" in summary
        report.record(
            "drop-bulk-url-limit",
            ok,
            f"chip_count={chip_count}; summary={summary!r}",
        )
    except Exception as exc:
        report.record("drop-bulk-url-limit", False, repr(exc))
    finally:
        context.close()


def run_source_composer_accessibility_suite(browser, report: QaReport) -> None:
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
    page.on("console", lambda msg: report.console_errors.append(f"[source-tabs-a11y] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[source-tabs-a11y] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("#url-input").wait_for(state="visible", timeout=60_000)

        tablist_visible = page.get_by_role("tablist", name="소스 종류").is_visible(timeout=5_000)
        url_tab = page.locator("[data-testid='source-tab-url']")
        text_tab = page.locator("[data-testid='source-tab-text']")
        url_selected = url_tab.get_attribute("aria-selected") == "true"
        url_tabindex = url_tab.get_attribute("tabindex") == "0"
        text_tabindex_initial = text_tab.get_attribute("tabindex") == "-1"
        url_panel = page.locator("#source-panel-url")
        url_panel_linked = (
            url_panel.count() > 0
            and url_panel.get_attribute("role") == "tabpanel"
            and url_panel.get_attribute("aria-labelledby") == (url_tab.get_attribute("id") or "")
            and url_tab.get_attribute("aria-controls") == "source-panel-url"
        )

        url_tab.focus(timeout=10_000)
        wait_until(lambda: url_tab.evaluate("el => document.activeElement === el"), 3_000, page)
        url_tab.press("ArrowRight", timeout=10_000)
        text_panel = page.locator("#source-panel-text")
        keyboard_switch_ok = wait_until(
            lambda: text_tab.get_attribute("aria-selected", timeout=1_000) == "true"
            and text_tab.get_attribute("tabindex", timeout=1_000) == "0"
            and url_tab.get_attribute("tabindex", timeout=1_000) == "-1"
            and text_tab.evaluate("el => document.activeElement === el")
            and text_panel.count() > 0
            and text_panel.is_visible(timeout=1_000),
            5_000,
            page,
        )
        text_selected = text_tab.get_attribute("aria-selected") == "true"
        text_tabindex_after_key = text_tab.get_attribute("tabindex") == "0"
        url_tabindex_after_key = url_tab.get_attribute("tabindex") == "-1"
        text_focused = text_tab.evaluate("el => document.activeElement === el")
        text_panel_linked = (
            text_panel.count() > 0
            and text_panel.is_visible(timeout=5_000)
            and text_panel.get_attribute("role") == "tabpanel"
            and text_panel.get_attribute("aria-labelledby") == (text_tab.get_attribute("id") or "")
            and text_tab.get_attribute("aria-controls") == "source-panel-text"
        )
        file_tab = page.locator("[data-testid='source-tab-file']")
        file_tab.click(timeout=10_000)
        file_focused = file_tab.evaluate("el => document.activeElement === el")
        file_selected = file_tab.get_attribute("aria-selected") == "true"
        file_tabindex = file_tab.get_attribute("tabindex") == "0"
        text_tabindex_after_click = text_tab.get_attribute("tabindex") == "-1"

        ok = (
            tablist_visible
            and url_selected
            and url_tabindex
            and text_tabindex_initial
            and url_panel_linked
            and keyboard_switch_ok
            and text_selected
            and text_tabindex_after_key
            and url_tabindex_after_key
            and text_focused
            and text_panel_linked
            and file_selected
            and file_focused
            and file_tabindex
            and text_tabindex_after_click
        )
        report.record(
            "source-composer-tabs-accessible",
            ok,
            (
                "tablist, roving tabindex, keyboard/click focus, and tabpanels linked"
                if ok
                else f"tablist={tablist_visible}; url_selected={url_selected}; url_tabindex={url_tabindex}; text_initial={text_tabindex_initial}; url_panel={url_panel_linked}; text_selected={text_selected}; text_tabindex={text_tabindex_after_key}; url_after={url_tabindex_after_key}; text_focused={text_focused}; text_panel={text_panel_linked}; file_selected={file_selected}; file_focused={file_focused}; file_tabindex={file_tabindex}; text_after_click={text_tabindex_after_click}"
            ),
        )
    except Exception as exc:
        report.record("source-composer-tabs-accessible", False, repr(exc))
    finally:
        context.close()


def run_url_input_accessibility_suite(browser, report: QaReport) -> None:
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
    page.on("console", lambda msg: report.console_errors.append(f"[url-input-a11y] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[url-input-a11y] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        input_box = page.locator("#url-input")
        input_box.wait_for(state="visible", timeout=60_000)
        hint = page.locator("[data-testid='url-input-help']")
        submit = page.locator("[data-testid='url-input-submit']")
        initial_ok = (
            input_box.get_attribute("aria-label", timeout=5_000) == "URL 입력"
            and input_box.get_attribute("aria-describedby", timeout=5_000) == "url-input-help"
            and input_box.get_attribute("aria-invalid", timeout=5_000) == "false"
            and hint.get_attribute("id", timeout=5_000) == "url-input-help"
            and "최대 10개" in hint.inner_text(timeout=5_000)
            and submit.get_attribute("aria-label", timeout=5_000) == "URL을 입력하면 추가할 수 있습니다"
            and submit.is_disabled(timeout=5_000)
        )
        input_box.fill("not-a-url", timeout=10_000)
        submit.click(timeout=10_000)
        error = page.locator("[data-testid='url-input-error']")
        error_ok = (
            input_box.get_attribute("aria-invalid", timeout=5_000) == "true"
            and input_box.get_attribute("aria-describedby", timeout=5_000) == "url-input-error"
            and error.get_attribute("id", timeout=5_000) == "url-input-error"
            and error.get_attribute("role", timeout=5_000) == "alert"
            and "유효한 URL" in error.inner_text(timeout=5_000)
        )
        ok = initial_ok and error_ok
        report.record(
            "url-input-accessible-state",
            ok,
            "url input help, invalid state, and error alert are linked" if ok else f"initial={initial_ok}; error={error_ok}",
        )
    except Exception as exc:
        report.record("url-input-accessible-state", False, repr(exc))
    finally:
        context.close()


def run_url_chip_accessibility_suite(browser, report: QaReport) -> None:
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
    page.on("console", lambda msg: report.console_errors.append(f"[url-chip-a11y] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[url-chip-a11y] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        input_box = page.locator("#url-input")
        input_box.wait_for(state="visible", timeout=60_000)
        input_box.fill("https://www.youtube.com/watch?v=dQw4w9WgXcQ", timeout=10_000)
        input_box.press("Enter")
        chip_list = page.locator("[data-testid='url-chip-list']")
        chip = page.locator("[data-testid='url-chip-0']")
        remove = page.locator("[data-testid='url-chip-remove-0']")
        wait_until(lambda: chip.count() > 0, 10_000, page)
        initial_ok = (
            chip_list.get_attribute("role", timeout=5_000) == "list"
            and chip_list.get_attribute("aria-label", timeout=5_000) == "추가된 URL 소스"
            and chip_list.get_attribute("aria-live", timeout=5_000) == "polite"
            and chip.get_attribute("role", timeout=5_000) == "listitem"
            and chip.get_attribute("aria-label", timeout=5_000) == "YouTube dQw4w9WgXcQ"
            and remove.get_attribute("aria-label", timeout=5_000) == "YouTube dQw4w9WgXcQ 제거"
        )
        remove.click(timeout=10_000)
        removed_ok = wait_until(lambda: chip_list.count() == 0, 10_000, page)
        ok = initial_ok and removed_ok
        report.record(
            "url-chip-list-accessible",
            ok,
            "url chip list, item label, and remove action are accessible" if ok else f"initial={initial_ok}; removed={removed_ok}",
        )
    except Exception as exc:
        report.record("url-chip-list-accessible", False, repr(exc))
    finally:
        context.close()


def run_source_text_input_accessibility_suite(browser, report: QaReport) -> None:
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
    page.on("console", lambda msg: report.console_errors.append(f"[source-text-a11y] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[source-text-a11y] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("#url-input").wait_for(state="visible", timeout=60_000)
        page.locator("[data-testid='source-tab-text']").click(timeout=10_000)
        text_input = page.locator("[data-testid='text-source-input']")
        counter = page.locator("[data-testid='text-source-counter']")
        generate = page.locator("[data-testid='text-source-generate']")
        initial_ok = (
            text_input.get_attribute("aria-label", timeout=5_000) == "텍스트 소스"
            and text_input.get_attribute("aria-describedby", timeout=5_000) == "text-source-counter"
            and counter.get_attribute("id", timeout=5_000) == "text-source-counter"
            and counter.get_attribute("role", timeout=5_000) == "status"
            and counter.get_attribute("aria-live", timeout=5_000) == "polite"
            and "0자" in counter.inner_text(timeout=5_000)
            and generate.get_attribute("aria-label", timeout=5_000) == "텍스트 생성"
            and generate.is_disabled(timeout=5_000)
        )
        text_input.fill("자동화 QA가 접근 가능한 텍스트 소스 입력을 검증합니다. 이 문장은 최소 글자 수를 충분히 넘깁니다.", timeout=10_000)
        changed_ok = "최소" not in counter.inner_text(timeout=5_000) and not generate.is_disabled(timeout=5_000)
        ok = initial_ok and changed_ok
        report.record(
            "source-text-input-accessible",
            ok,
            "text input label, live counter, and generate state update" if ok else f"initial={initial_ok}; changed={changed_ok}",
        )
    except Exception as exc:
        report.record("source-text-input-accessible", False, repr(exc))
    finally:
        context.close()


def run_source_file_input_accessibility_suite(browser, report: QaReport) -> None:
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
    page.on("console", lambda msg: report.console_errors.append(f"[source-file-a11y] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[source-file-a11y] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("#url-input").wait_for(state="visible", timeout=60_000)
        page.locator("[data-testid='source-tab-file']").click(timeout=10_000)
        dropzone = page.locator("[data-testid='file-source-dropzone']")
        file_input = page.locator("[data-testid='file-source-input']")
        help_text = page.locator("[data-testid='file-source-help']")
        generate = page.locator("[data-testid='file-source-generate']")
        initial_ok = (
            dropzone.get_attribute("role", timeout=5_000) == "button"
            and dropzone.get_attribute("aria-label", timeout=5_000) == "PDF/DOCX 파일 업로드"
            and dropzone.get_attribute("aria-describedby", timeout=5_000) == "file-source-help"
            and file_input.get_attribute("accept", timeout=5_000) == ".pdf,.docx"
            and help_text.get_attribute("id", timeout=5_000) == "file-source-help"
            and "최대 10MB" in help_text.inner_text(timeout=5_000)
            and generate.get_attribute("aria-label", timeout=5_000) == "파일 생성"
            and generate.is_disabled(timeout=5_000)
        )
        invalid_path = ARTIFACTS / "qa-upload.txt"
        invalid_path.write_bytes(b"qa invalid upload")
        file_input.set_input_files(str(invalid_path))
        error = page.locator("[data-testid='file-source-error']")
        error.wait_for(state="visible", timeout=5_000)
        error_text = error.inner_text(timeout=5_000)
        error_ok = (
            error.get_attribute("role", timeout=2_000) == "status"
            and error.get_attribute("aria-live", timeout=2_000) == "assertive"
            and "PDF \ub610\ub294 DOCX" in error_text
            and generate.is_disabled(timeout=5_000)
        )
        report.record(
            "source-file-error-accessible",
            error_ok,
            "invalid file error is announced and generate remains disabled" if error_ok else f"text={error_text!r}; role={error.get_attribute('role') if error.count() else None}; live={error.get_attribute('aria-live') if error.count() else None}; disabled={generate.is_disabled()}",
        )
        source_path = ARTIFACTS / "qa-upload.docx"
        source_path.write_bytes(b"qa docx upload")
        file_input.set_input_files(str(source_path))
        selected = page.locator("[data-testid='file-source-selected']")
        selected_ok = (
            selected.get_attribute("role", timeout=5_000) == "status"
            and selected.get_attribute("aria-live", timeout=5_000) == "polite"
            and "qa-upload.docx" in selected.inner_text(timeout=10_000)
            and not generate.is_disabled(timeout=5_000)
        )
        ok = initial_ok and selected_ok
        report.record(
            "source-file-input-accessible",
            ok,
            "file dropzone label, help, selected state, and generate state update" if ok else f"initial={initial_ok}; selected={selected_ok}",
        )
    except Exception as exc:
        report.record("source-file-input-accessible", False, repr(exc))
    finally:
        context.close()


def run_source_voice_input_accessibility_suite(browser, report: QaReport) -> None:
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
    page.on("console", lambda msg: report.console_errors.append(f"[source-voice-a11y] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[source-voice-a11y] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("#url-input").wait_for(state="visible", timeout=60_000)
        page.locator("[data-testid='source-tab-voice']").click(timeout=10_000)
        panel = page.locator("[data-testid='voice-source-panel']")
        record = page.locator("[data-testid='voice-record-button']")
        file_input = page.locator("[data-testid='voice-file-input']")
        help_text = page.locator("[data-testid='voice-source-help']")
        generate = page.locator("[data-testid='voice-source-generate']")
        initial_ok = (
            panel.get_attribute("aria-describedby", timeout=5_000) == "voice-source-help"
            and record.get_attribute("aria-label", timeout=5_000) == "음성 녹음 시작"
            and file_input.get_attribute("aria-label", timeout=5_000) == "오디오 파일 업로드"
            and "audio/*" in (file_input.get_attribute("accept", timeout=5_000) or "")
            and help_text.get_attribute("id", timeout=5_000) == "voice-source-help"
            and "MP3/WAV/WEBM" in help_text.inner_text(timeout=5_000)
            and generate.get_attribute("aria-label", timeout=5_000) == "음성 생성"
            and generate.is_disabled(timeout=5_000)
        )
        source_path = ARTIFACTS / "qa-voice.webm"
        source_path.write_bytes(b"qa audio upload")
        file_input.set_input_files(str(source_path))
        selected = page.locator("[data-testid='voice-source-selected']")
        remove = page.locator("[data-testid='voice-source-remove']")
        selected_ok = (
            selected.get_attribute("role", timeout=5_000) == "status"
            and selected.get_attribute("aria-live", timeout=5_000) == "polite"
            and "qa-voice.webm" in selected.inner_text(timeout=10_000)
            and remove.get_attribute("aria-label", timeout=5_000) == "오디오 파일 선택 제거"
            and not generate.is_disabled(timeout=5_000)
        )
        ok = initial_ok and selected_ok
        report.record(
            "source-voice-input-accessible",
            ok,
            "voice record/upload labels, selected state, and generate state update" if ok else f"initial={initial_ok}; selected={selected_ok}",
        )
    except Exception as exc:
        report.record("source-voice-input-accessible", False, repr(exc))
    finally:
        context.close()


def run_output_blueprint_style_accessibility_suite(browser, report: QaReport) -> None:
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
    page.on("console", lambda msg: report.console_errors.append(f"[blueprint-style-a11y] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[blueprint-style-a11y] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("#url-input").wait_for(state="visible", timeout=60_000)
        group = page.locator("[data-testid='blueprint-style-options']")
        blog = page.locator("[data-testid='blueprint-style-blog_seo']")
        summary = page.locator("[data-testid='blueprint-style-summary']")
        course = page.locator("[data-testid='blueprint-style-course']")
        initial_ok = (
            group.count() > 0
            and group.get_attribute("role") == "radiogroup"
            and group.get_attribute("aria-label") == "산출물 스타일"
            and blog.get_attribute("role") == "radio"
            and blog.get_attribute("aria-checked") == "true"
            and summary.get_attribute("aria-checked") == "false"
        )
        blog.focus(timeout=10_000)
        page.keyboard.press("ArrowRight")
        next_ok = wait_until(
            lambda: summary.get_attribute("aria-checked", timeout=1_000) == "true"
            and summary.evaluate("el => document.activeElement === el"),
            5_000,
            page,
        )
        page.keyboard.press("End")
        end_ok = wait_until(
            lambda: course.get_attribute("aria-checked", timeout=1_000) == "true"
            and course.evaluate("el => document.activeElement === el"),
            5_000,
            page,
        )
        report.record(
            "output-blueprint-style-accessible",
            initial_ok and next_ok and end_ok,
            "style radiogroup, radio state, and keyboard navigation update selection" if initial_ok and next_ok and end_ok else f"initial={initial_ok}; next={next_ok}; end={end_ok}",
        )
    except Exception as exc:
        report.record("output-blueprint-style-accessible", False, repr(exc))
    finally:
        context.close()


def run_output_blueprint_mode_accessibility_suite(browser, report: QaReport) -> None:
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
    page.on("console", lambda msg: report.console_errors.append(f"[blueprint-mode-a11y] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[blueprint-mode-a11y] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("#url-input").wait_for(state="visible", timeout=60_000)
        page.locator("#url-input").fill("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        page.locator("#url-input").press("Enter")
        wait_until(lambda: "소스 1개" in page.locator("[data-testid='generate-dock-summary']").inner_text(timeout=1_000), 10_000, page)

        group = page.locator("[data-testid='blueprint-mode-options']")
        individual = page.locator("[data-testid='blueprint-mode-individual']")
        combined = page.locator("[data-testid='blueprint-mode-combined']")
        fusion = page.locator("[data-testid='blueprint-mode-fusion']")
        initial_ok = (
            group.get_attribute("role", timeout=5_000) == "radiogroup"
            and group.get_attribute("aria-label", timeout=5_000) == "제작 모드"
            and individual.get_attribute("role", timeout=5_000) == "radio"
            and individual.get_attribute("aria-checked", timeout=5_000) == "true"
            and combined.get_attribute("aria-checked", timeout=5_000) == "false"
            and fusion.get_attribute("aria-checked", timeout=5_000) == "false"
            and combined.is_disabled(timeout=5_000)
            and fusion.is_disabled(timeout=5_000)
            and combined.get_attribute("aria-describedby", timeout=5_000) == "blueprint-mode-hint"
            and fusion.get_attribute("aria-describedby", timeout=5_000) == "blueprint-mode-hint"
        )

        page.locator("#url-input").fill("https://www.youtube.com/watch?v=wr4nCMUy1dk")
        page.locator("#url-input").press("Enter")
        wait_until(lambda: "소스 2개" in page.locator("[data-testid='generate-dock-summary']").inner_text(timeout=1_000), 10_000, page)
        wait_until(lambda: not combined.is_disabled(timeout=1_000) and not fusion.is_disabled(timeout=1_000), 10_000, page)
        individual.focus(timeout=10_000)
        page.keyboard.press("ArrowRight")
        combined_ok = (
            combined.get_attribute("aria-checked", timeout=5_000) == "true"
            and combined.evaluate("el => document.activeElement === el")
        )
        page.keyboard.press("End")
        fusion_ok = (
            fusion.get_attribute("aria-checked", timeout=5_000) == "true"
            and fusion.evaluate("el => document.activeElement === el")
        )
        ok = initial_ok and combined_ok and fusion_ok
        report.record(
            "output-blueprint-mode-accessible",
            ok,
            "mode radiogroup, disabled hints, and keyboard navigation update selection" if ok else f"initial={initial_ok}; combined={combined_ok}; fusion={fusion_ok}",
        )
    except Exception as exc:
        report.record("output-blueprint-mode-accessible", False, repr(exc))
    finally:
        context.close()


def run_output_blueprint_detail_accessibility_suite(browser, report: QaReport) -> None:
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
    page.on("console", lambda msg: report.console_errors.append(f"[blueprint-detail-a11y] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[blueprint-detail-a11y] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("#url-input").wait_for(state="visible", timeout=60_000)
        group = page.locator("[data-testid='blueprint-detail-level']")
        brief = page.locator("[data-testid='blueprint-detail-brief']")
        standard = page.locator("[data-testid='blueprint-detail-standard']")
        deep = page.locator("[data-testid='blueprint-detail-deep']")
        initial_ok = (
            group.get_attribute("role") == "radiogroup"
            and group.get_attribute("aria-label") == "상세도"
            and standard.get_attribute("role") == "radio"
            and standard.get_attribute("aria-checked") == "true"
            and deep.get_attribute("aria-checked") == "false"
        )
        standard.focus(timeout=10_000)
        page.keyboard.press("ArrowLeft")
        brief_ok = wait_until(
            lambda: brief.get_attribute("aria-checked", timeout=1_000) == "true"
            and brief.evaluate("el => document.activeElement === el"),
            5_000,
            page,
        )
        page.keyboard.press("End")
        deep_ok = wait_until(
            lambda: deep.get_attribute("aria-checked", timeout=1_000) == "true"
            and deep.evaluate("el => document.activeElement === el"),
            5_000,
            page,
        )
        report.record(
            "output-blueprint-detail-accessible",
            initial_ok and brief_ok and deep_ok,
            "detail radiogroup, radio state, and keyboard navigation update selection" if initial_ok and brief_ok and deep_ok else f"initial={initial_ok}; brief={brief_ok}; deep={deep_ok}",
        )
    except Exception as exc:
        report.record("output-blueprint-detail-accessible", False, repr(exc))
    finally:
        context.close()


def run_output_blueprint_modifier_accessibility_suite(browser, report: QaReport) -> None:
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
    page.on("console", lambda msg: report.console_errors.append(f"[blueprint-modifier-a11y] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[blueprint-modifier-a11y] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("#url-input").wait_for(state="visible", timeout=60_000)
        group = page.locator("[data-testid='blueprint-modifier-controls']")
        length = page.locator("[data-testid='blueprint-length-select']")
        tone = page.locator("[data-testid='blueprint-tone-select']")
        language = page.locator("[data-testid='blueprint-language-select']")
        initial_ok = (
            group.get_attribute("role") == "group"
            and group.get_attribute("aria-label") == "길이 · 톤 · 언어"
            and length.get_attribute("aria-label") == "길이"
            and tone.get_attribute("aria-label") == "톤"
            and language.get_attribute("aria-label") == "언어"
            and length.input_value() == "medium"
            and tone.input_value() == "conversational"
            and language.input_value() == "ko"
        )
        length.focus(timeout=10_000)
        page.keyboard.press("End")
        tone.select_option("expert", timeout=10_000)
        language.select_option("en", timeout=10_000)
        changed_ok = wait_until(
            lambda: length.input_value() == "long" and tone.input_value() == "expert" and language.input_value() == "en",
            10_000,
            page,
        )
        values = {"length": length.input_value(), "tone": tone.input_value(), "language": language.input_value()}
        report.record(
            "output-blueprint-modifier-accessible",
            initial_ok and changed_ok,
            "modifier group, labels, and values update" if initial_ok and changed_ok else f"initial={initial_ok}; changed={changed_ok}; values={values}",
        )
    except Exception as exc:
        report.record("output-blueprint-modifier-accessible", False, repr(exc))
    finally:
        context.close()


def run_output_blueprint_advanced_accessibility_suite(browser, report: QaReport) -> None:
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
    page.on("console", lambda msg: report.console_errors.append(f"[blueprint-advanced-a11y] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[blueprint-advanced-a11y] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("#url-input").wait_for(state="visible", timeout=60_000)
        group = page.locator("[data-testid='blueprint-advanced-panel']")
        web_search = page.locator("[data-testid='blueprint-web-search']")
        web_research = page.locator("[data-testid='blueprint-web-research']")
        deep_comments = page.locator("[data-testid='blueprint-deep-comments']")
        agent_mode = page.locator("[data-testid='blueprint-agent-mode']")
        initial_ok = (
            group.get_attribute("role") == "group"
            and group.get_attribute("aria-label") == "고급 옵션"
            and web_search.get_attribute("role") == "switch"
            and web_search.get_attribute("aria-checked") == "false"
            and web_research.get_attribute("aria-checked") == "true"
            and deep_comments.get_attribute("aria-checked") == "true"
            and agent_mode.get_attribute("aria-checked") == "false"
        )
        def toggle_until_checked(locator, expected: str, key: str) -> bool:
            locator.scroll_into_view_if_needed(timeout=10_000)
            for _ in range(3):
                if locator.get_attribute("aria-checked", timeout=1_000) == expected:
                    return True
                locator.focus(timeout=10_000)
                page.keyboard.press(key)
                wait_until(lambda: locator.get_attribute("aria-checked", timeout=1_000) == expected, 2_000, page)
            return locator.get_attribute("aria-checked", timeout=1_000) == expected

        toggled = (
            toggle_until_checked(web_search, "true", "Space")
            and toggle_until_checked(web_research, "false", "Enter")
            and toggle_until_checked(deep_comments, "false", "Space")
            and toggle_until_checked(agent_mode, "true", "Enter")
        )
        changed_ok = (
            toggled
            and web_search.get_attribute("aria-checked") == "true"
            and web_research.get_attribute("aria-checked") == "false"
            and deep_comments.get_attribute("aria-checked") == "false"
            and agent_mode.get_attribute("aria-checked") == "true"
        )
        report.record(
            "output-blueprint-advanced-accessible",
            initial_ok and changed_ok,
            "advanced option group, switch states, and keyboard toggles update" if initial_ok and changed_ok else f"initial={initial_ok}; changed={changed_ok}",
        )
    except Exception as exc:
        report.record("output-blueprint-advanced-accessible", False, repr(exc))
    finally:
        context.close()


def run_batch_advanced_request_suite(browser, report: QaReport) -> None:
    captured: list[dict[str, Any]] = []
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    context.add_init_script(
        """
        localStorage.setItem('insight-engine-onboarding-done', JSON.stringify(true));
        localStorage.setItem('insight-engine-selected-provider', JSON.stringify('chatmock'));
        localStorage.setItem('insight-engine-selected-model', JSON.stringify('chatmock/gpt-5.5'));
        localStorage.removeItem('insight-engine-reports');
        """
    )

    def batch(route) -> None:
        data = route.request.post_data_json
        if callable(data):
            data = data()
        payload = data if isinstance(data, dict) else {}
        captured.append(payload)
        urls = payload.get("urls") if isinstance(payload.get("urls"), list) else []
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "success": True,
                "results": [
                    {
                        "success": True,
                        "url": url,
                        "title": f"QA 배치 {idx + 1}",
                        "content": "# QA 배치\n\n고급 옵션 배치 요청입니다.",
                        "html": "<h1>QA 배치</h1>",
                    }
                    for idx, url in enumerate(urls)
                ],
                "total_processed": len(urls),
                "successful": len(urls),
                "failed": 0,
            }, ensure_ascii=False),
        )

    context.route("**/generate-batch", batch)
    page = context.new_page()
    page.on("console", lambda msg: report.console_errors.append(f"[batch-advanced] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[batch-advanced] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("#url-input").fill("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        page.locator("#url-input").press("Enter")
        page.locator("#url-input").fill("https://www.youtube.com/watch?v=wr4nCMUy1dk")
        page.locator("#url-input").press("Enter")
        page.locator("[data-testid='blueprint-detail-level']").get_by_text("심층").click(timeout=10_000)
        page.locator("[data-testid='blueprint-web-search']").click(timeout=10_000)
        page.locator("[data-testid='blueprint-agent-mode']").click(timeout=10_000)
        page.locator("[data-testid='generate-dock-button']").click(timeout=10_000)

        sent = wait_until(lambda: len(captured) > 0, 10_000, page)
        payload = captured[-1] if captured else {}
        ok = (
            sent
            and payload.get("detail_level") == "deep"
            and payload.get("web_search") is True
            and payload.get("agent_mode") is True
            and len(payload.get("urls", [])) == 2
        )
        report.record(
            "batch-advanced-request-options",
            ok,
            f"payload={payload}" if ok else f"missing advanced options; payload={payload}",
        )
    except Exception as exc:
        report.record("batch-advanced-request-options", False, repr(exc))
    finally:
        context.close()


def run_url_mode_advanced_request_suite(browser, report: QaReport) -> None:
    captured: dict[str, list[dict[str, Any]]] = {"merged": [], "fusion": []}
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    context.add_init_script(
        """
        localStorage.setItem('insight-engine-onboarding-done', JSON.stringify(true));
        localStorage.setItem('insight-engine-selected-provider', JSON.stringify('chatmock'));
        localStorage.setItem('insight-engine-selected-model', JSON.stringify('chatmock/gpt-5.5'));
        localStorage.removeItem('insight-engine-reports');
        """
    )

    def body_json(route) -> dict[str, Any]:
        data = route.request.post_data_json
        if callable(data):
            data = data()
        return data if isinstance(data, dict) else {}

    def merged(route) -> None:
        payload = body_json(route)
        captured["merged"].append(payload)
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "id": "qa-merged-advanced",
                "title": "QA 통합 고급 옵션",
                "content": "# QA 통합 고급 옵션",
                "html": "<h1>QA 통합 고급 옵션</h1>",
                "usage": {"total_tokens": 10},
                "elapsed_time": 0.1,
                "transcript_source": "qa",
                "prompt": "qa merged",
                "cached": False,
                "comment_summary_included": False,
                "source_videos": [],
            }, ensure_ascii=False),
        )

    def fusion(route) -> None:
        payload = body_json(route)
        captured["fusion"].append(payload)
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "title": "QA 퓨전 고급 옵션",
                "content": "# QA 퓨전 고급 옵션",
                "html": "<h1>QA 퓨전 고급 옵션</h1>",
                "usage": {"total_tokens": 10},
                "fusion_meta": {"processing_time": 0.1},
                "sections": {},
            }, ensure_ascii=False),
        )

    context.route("**/api/generate-merged", merged)
    context.route("**/api/generate-fusion", fusion)
    page = context.new_page()
    page.on("console", lambda msg: report.console_errors.append(f"[url-advanced] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[url-advanced] {exc}"))

    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        page.locator("#url-input").fill("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        page.locator("#url-input").press("Enter")
        page.locator("#url-input").fill("https://www.youtube.com/watch?v=wr4nCMUy1dk")
        page.locator("#url-input").press("Enter")
        page.locator("[data-testid='blueprint-detail-level']").get_by_text("심층").click(timeout=10_000)
        page.locator("[data-testid='blueprint-web-search']").click(timeout=10_000)
        page.locator("[data-testid='blueprint-agent-mode']").click(timeout=10_000)

        page.get_by_text("통합").click(timeout=10_000)
        page.locator("[data-testid='generate-dock-button']").click(timeout=10_000)
        merged_sent = wait_until(lambda: len(captured["merged"]) > 0, 10_000, page)
        merged_payload = captured["merged"][-1] if captured["merged"] else {}
        merged_ok = (
            merged_sent
            and merged_payload.get("detail_level") == "deep"
            and merged_payload.get("web_search") is True
            and merged_payload.get("agent_mode") is True
        )
        report.record(
            "merged-advanced-request-options",
            merged_ok,
            f"payload={merged_payload}" if merged_ok else f"missing advanced options; payload={merged_payload}",
        )

        page.locator("#url-input").fill("https://www.youtube.com/watch?v=aaaaaaaaaaa")
        page.locator("#url-input").press("Enter")
        page.locator("#url-input").fill("https://www.youtube.com/watch?v=bbbbbbbbbbb")
        page.locator("#url-input").press("Enter")
        wait_until(lambda: "소스 2개" in page.locator("[data-testid='generate-dock-summary']").inner_text(timeout=1_000), 10_000, page)
        page.get_by_text("퓨전").click(timeout=10_000)
        page.locator("[data-testid='generate-dock-button']").click(timeout=10_000)
        fusion_sent = wait_until(lambda: len(captured["fusion"]) > 0, 10_000, page)
        fusion_payload = captured["fusion"][-1] if captured["fusion"] else {}
        fusion_ok = (
            fusion_sent
            and fusion_payload.get("detail_level") == "deep"
            and fusion_payload.get("web_search") is True
            and fusion_payload.get("agent_mode") is True
            and fusion_payload.get("enable_web_research") is True
            and fusion_payload.get("enable_deep_comments") is True
        )
        report.record(
            "fusion-advanced-request-options",
            fusion_ok,
            f"payload={fusion_payload}" if fusion_ok else f"missing advanced options; payload={fusion_payload}",
        )
    except Exception as exc:
        if not any(row["case"] == "merged-advanced-request-options" for row in report.rows):
            report.record("merged-advanced-request-options", False, repr(exc))
        if not any(row["case"] == "fusion-advanced-request-options" for row in report.rows):
            report.record("fusion-advanced-request-options", False, repr(exc))
    finally:
        context.close()


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
        "notebooklm_downloads": [],
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
        nlm_text = page.locator("[data-testid='notebooklm-artifact']").first.inner_text(timeout=10_000)
        nlm_labels_ok = "브라우저 보기" in nlm_text and "HTML 저장" in nlm_text and "원본 MD 저장" not in nlm_text
        report.record(
            "notebooklm-view-download-labels",
            nlm_labels_ok,
            screenshot(page, "notebooklm-view-download-labels.png") if nlm_labels_ok else nlm_text[:300],
        )
        try:
            with page.expect_download(timeout=10_000) as download_info:
                page.locator("[data-testid='notebooklm-download-artifact']").first.click(timeout=10_000)
            download = download_info.value
            filename = download.suggested_filename
            hit_rendered_download = len(calls["notebooklm_downloads"]) > 0
            html_ok = filename.lower().endswith(".html") and hit_rendered_download
            report.record(
                "notebooklm-html-download-extension",
                html_ok,
                f"download={filename}" if html_ok else f"expected .html via rendered-download, got {filename}, hits={len(calls['notebooklm_downloads'])}",
            )
        except Exception as exc:
            report.record("notebooklm-html-download-extension", False, repr(exc))
        try:
            panel = page.locator("[data-testid='notebooklm-artifacts-panel']").first
            artifact_list = page.locator("[data-testid='notebooklm-artifact-list']").first
            artifact = page.locator("[data-testid='notebooklm-artifact']").first
            status = page.locator("[data-testid='notebooklm-artifact-status']").first
            view = page.locator("[data-testid='notebooklm-view-artifact']").first
            download_button = page.locator("[data-testid='notebooklm-download-artifact']").first
            panel_a11y_ok = (
                panel.count() == 1
                and panel.get_attribute("role", timeout=2_000) == "region"
                and panel.get_attribute("aria-label", timeout=2_000) == "NotebookLM \uc0b0\ucd9c\ubb3c"
                and artifact_list.count() == 1
                and artifact_list.get_attribute("role", timeout=2_000) == "list"
                and artifact.count() >= 1
                and artifact.get_attribute("role", timeout=2_000) == "listitem"
                and (artifact.get_attribute("aria-label", timeout=2_000) or "").startswith("\uc2a4\ud130\ub514 \uac00\uc774\ub4dc")
                and status.count() == 1
                and status.get_attribute("role", timeout=2_000) == "status"
                and status.get_attribute("aria-live", timeout=2_000) == "polite"
                and view.get_attribute("aria-label", timeout=2_000) == "\uc2a4\ud130\ub514 \uac00\uc774\ub4dc \ube0c\ub77c\uc6b0\uc800 \ubcf4\uae30"
                and download_button.get_attribute("aria-label", timeout=2_000) == "\uc2a4\ud130\ub514 \uac00\uc774\ub4dc HTML \uc800\uc7a5"
            )
            report.record(
                "notebooklm-artifact-panel-accessible",
                panel_a11y_ok,
                "NotebookLM artifact panel exposes region, list, status, and action labels" if panel_a11y_ok else f"panel={panel.count()}; list={artifact_list.count()}; artifact_role={artifact.get_attribute('role') if artifact.count() else None}; status={status.count()}; view={view.get_attribute('aria-label') if view.count() else None}; download={download_button.get_attribute('aria-label') if download_button.count() else None}",
            )
        except Exception as exc:
            report.record("notebooklm-artifact-panel-accessible", False, repr(exc))
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
        options = dialog.locator("[data-testid='platform-rewrite-options']")
        twitter = dialog.locator("[data-testid='platform-rewrite-twitter']")
        options_initial_ok = (
            options.count() == 1
            and options.get_attribute("role", timeout=2_000) == "radiogroup"
            and options.get_attribute("aria-label", timeout=2_000) == "변환 플랫폼"
            and twitter.count() == 1
            and twitter.get_attribute("role", timeout=2_000) == "radio"
            and twitter.get_attribute("aria-checked", timeout=2_000) == "false"
        )
        if twitter.count() == 1:
            twitter.click(timeout=10_000)
        else:
            dialog.get_by_text("Twitter / X").click(timeout=10_000)
        ok_call = wait_until(lambda: len(calls["rewrite"]) > before, 10_000, page)
        page.get_by_text("QA 메뉴 변환 결과").wait_for(state="visible", timeout=10_000)
        result_region = dialog.locator("[data-testid='platform-rewrite-result']")
        copy_button = dialog.locator("[data-testid='platform-rewrite-copy']")
        options_result_ok = (
            ok_call
            and options_initial_ok
            and twitter.count() == 1
            and twitter.get_attribute("aria-checked", timeout=2_000) == "true"
            and result_region.count() == 1
            and result_region.get_attribute("role", timeout=2_000) == "region"
            and result_region.get_attribute("aria-live", timeout=2_000) == "polite"
            and result_region.get_attribute("aria-label", timeout=2_000) == "플랫폼 변환 결과"
            and copy_button.count() == 1
            and copy_button.get_attribute("aria-label", timeout=2_000) == "변환 결과 복사"
        )
        platform_png = screenshot(page, "menu-platform-convert.png")
        record_action("플랫폼 변환", ok_call, platform_png if ok_call else "rewrite API not called")
        report.record(
            "platform-rewrite-options-accessible",
            options_result_ok,
            "platform rewrite choices and result region expose accessible state" if options_result_ok else f"initial={options_initial_ok}; ok_call={ok_call}; selected_checked={twitter.get_attribute('aria-checked') if twitter.count() else None}; result={result_region.count()}; copy_label={copy_button.get_attribute('aria-label') if copy_button.count() else None}",
        )
        close_dialogs(page)
    except Exception as exc:
        record_action("플랫폼 변환", False, repr(exc))
        report.record("platform-rewrite-options-accessible", False, repr(exc))
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
        card = page.locator("[data-report-id='qa-menu-report']").first
        card.scroll_into_view_if_needed(timeout=10_000)
        with page.expect_download(timeout=15_000) as download_info:
            card.locator("[data-testid='workbench-action-export-md']").click(timeout=10_000)
        download = download_info.value
        notice = card.locator("[data-testid='workbench-export-status']")
        notice.wait_for(state="visible", timeout=10_000)
        notice_text = notice.inner_text(timeout=5_000)
        ok = download.suggested_filename.lower().endswith(".md") and "MD" in notice_text and "완료" in notice_text
        report.record(
            "result-workbench-export-status",
            ok,
            screenshot(page, "result-workbench-export-status.png") if ok else f"download={download.suggested_filename}; notice={notice_text[:300]}",
        )
    except Exception as exc:
        report.record("result-workbench-export-status", False, repr(exc))

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
        dialog.locator("select").first.select_option("wordpress", timeout=10_000)
        prefill_ok = (
            dialog.locator("[data-testid='schedule-option-wordpress-site-url']").input_value(timeout=10_000) == "https://stored.wp.example.com"
            and dialog.locator("[data-testid='schedule-option-wordpress-username']").input_value(timeout=10_000) == "stored-writer"
            and dialog.locator("[data-testid='schedule-option-wordpress-status']").input_value(timeout=10_000) == "pending"
        )
        dialog.locator("[data-testid='schedule-option-wordpress-app-password']").fill("qa-secret")
        dialog.locator("button", has_text="예약 등록").click(timeout=10_000)
        ok = wait_until(lambda: len(calls["schedule"]) > before, 10_000, page)
        payload = calls["schedule"][-1] if ok else {}
        options = payload.get("options") or payload.get("plugin_options") or {}
        options_ok = (
            payload.get("target_plugin") == "wordpress"
            and options.get("site_url") == "https://stored.wp.example.com"
            and options.get("username") == "stored-writer"
            and options.get("app_password") == "qa-secret"
            and options.get("status") == "pending"
        )
        schedule_png = screenshot(page, "menu-schedule.png")
        redacted_payload = json.loads(json.dumps(payload, ensure_ascii=False))
        redacted_options = redacted_payload.get("options") or redacted_payload.get("plugin_options") or {}
        if isinstance(redacted_options, dict) and "app_password" in redacted_options:
            redacted_options["app_password"] = "***"
        record_action("예약 발행", prefill_ok and ok and options_ok, schedule_png if prefill_ok and ok and options_ok else f"prefill_ok={prefill_ok}; payload={redacted_payload}")
    except Exception as exc:
        record_action("예약 발행", False, repr(exc))
        close_dialogs(page)

    try:
        before = len(calls["schedule"])
        click_menu_label(page, "예약 발행")
        dialog = page.locator("[role='dialog']").last
        dialog.wait_for(state="visible", timeout=10_000)
        dialog.locator("select").first.select_option("naver_blog", timeout=10_000)
        prefill_ok = (
            dialog.locator("[data-testid='schedule-option-naver-webhook-url']").input_value(timeout=10_000) == "https://stored.naver.example.com/webhook"
            and dialog.locator("[data-testid='schedule-option-naver-blog-id']").input_value(timeout=10_000) == "stored-blog"
            and dialog.locator("[data-testid='schedule-option-naver-category']").input_value(timeout=10_000) == "AI 자동화"
            and dialog.locator("[data-testid='schedule-option-naver-tags']").input_value(timeout=10_000) == "ai,자동화"
        )
        dialog.locator("button", has_text="예약 등록").click(timeout=10_000)
        ok = wait_until(lambda: len(calls["schedule"]) > before, 10_000, page)
        payload = calls["schedule"][-1] if ok else {}
        options = payload.get("options") or payload.get("plugin_options") or {}
        options_ok = (
            payload.get("target_plugin") == "naver_blog"
            and options.get("webhook_url") == "https://stored.naver.example.com/webhook"
            and options.get("blog_id") == "stored-blog"
            and options.get("category") == "AI 자동화"
            and options.get("tags") == "ai,자동화"
        )
        report.record(
            "menu-schedule-naver-defaults",
            prefill_ok and ok and options_ok,
            f"payload={payload}" if prefill_ok and ok and options_ok else f"prefill_ok={prefill_ok}; payload={payload}",
        )
    except Exception as exc:
        report.record("menu-schedule-naver-defaults", False, repr(exc))
        close_dialogs(page)

    try:
        before = len(calls["schedule"])
        click_menu_label(page, "예약 발행")
        dialog = page.locator("[role='dialog']").last
        dialog.wait_for(state="visible", timeout=10_000)
        dialog.locator("select").first.select_option("naver_blog", timeout=10_000)
        dialog.locator("[data-testid='schedule-option-naver-webhook-url']").fill("")
        submit = dialog.locator("button", has_text="예약 등록")
        disabled = not submit.is_enabled()
        if submit.is_enabled():
            submit.click(timeout=10_000)
        page.wait_for_timeout(400)
        no_call = len(calls["schedule"]) == before
        text = dialog.inner_text(timeout=1_000) if dialog.is_visible(timeout=1_000) else ""
        has_hint = "네이버 발행 웹훅 URL" in text and ("필수" in text or "입력" in text)
        naver_webhook = dialog.locator("[data-testid='schedule-option-naver-webhook-url']")
        validation = dialog.locator("[data-testid='schedule-validation-message']")
        describedby = naver_webhook.get_attribute("aria-describedby", timeout=2_000) if naver_webhook.count() else ""
        validation_accessible = (
            validation.count() == 1
            and validation.get_attribute("role", timeout=2_000) == "alert"
            and validation.get_attribute("aria-live", timeout=2_000) == "assertive"
            and naver_webhook.get_attribute("aria-invalid", timeout=2_000) == "true"
            and describedby
            and "schedule-validation-message" in describedby
        )
        report.record(
            "menu-schedule-required-options",
            no_call and has_hint and disabled,
            f"disabled={disabled}; calls_before={before}; calls_after={len(calls['schedule'])}; text={text[:300]}",
        )
        report.record(
            "menu-schedule-validation-accessible",
            no_call and has_hint and validation_accessible,
            "schedule required validation is announced and linked to the invalid field" if no_call and has_hint and validation_accessible else f"no_call={no_call}; has_hint={has_hint}; validation_accessible={validation_accessible}; invalid={naver_webhook.get_attribute('aria-invalid') if naver_webhook.count() else None}; describedby={describedby!r}",
        )
        close_dialogs(page)
    except Exception as exc:
        report.record("menu-schedule-required-options", False, repr(exc))
        report.record("menu-schedule-validation-accessible", False, repr(exc))
        close_dialogs(page)

    try:
        before = len(calls["schedule"])
        click_menu_label(page, "예약 발행")
        dialog = page.locator("[role='dialog']").last
        dialog.wait_for(state="visible", timeout=10_000)
        dialog.locator("select").first.select_option("naver_blog", timeout=10_000)
        dialog.locator("input[type='datetime-local']").fill("2020-01-01T09:00")
        submit = dialog.locator("button", has_text="예약 등록")
        disabled = not submit.is_enabled()
        if submit.is_enabled():
            submit.click(timeout=10_000)
        page.wait_for_timeout(400)
        no_call = len(calls["schedule"]) == before
        text = dialog.inner_text(timeout=1_000) if dialog.is_visible(timeout=1_000) else ""
        has_hint = "미래" in text or "이후" in text
        report.record(
            "menu-schedule-future-time",
            no_call and has_hint and disabled,
            f"disabled={disabled}; calls_before={before}; calls_after={len(calls['schedule'])}; text={text[:300]}",
        )
        close_dialogs(page)
    except Exception as exc:
        report.record("menu-schedule-future-time", False, repr(exc))
        close_dialogs(page)

    try:
        before = len(calls["schedule"])
        click_menu_label(page, "예약 발행")
        dialog = page.locator("[role='dialog']").last
        dialog.wait_for(state="visible", timeout=10_000)
        dialog.locator("select").first.select_option("naver_blog", timeout=10_000)
        dialog.locator("[data-testid='schedule-option-naver-category']").fill("QA_FAIL")
        dialog.locator("button", has_text="예약 등록").click(timeout=10_000)
        called = wait_until(lambda: len(calls["schedule"]) > before, 5_000, page)
        page.wait_for_timeout(500)
        stays_open = dialog.is_visible(timeout=1_000)
        text = dialog.inner_text(timeout=5_000) if stays_open else ""
        has_hint = "예약 등록 실패" in text or "다시 시도" in text
        report.record(
            "menu-schedule-failure-stays-open",
            called and stays_open and has_hint,
            f"called={called}; stays_open={stays_open}; text={text[:300]}",
        )
        dialog.locator("[data-testid='schedule-option-naver-category']").fill("AI 자동화")
        page.wait_for_timeout(300)
        edited_text = dialog.inner_text(timeout=5_000) if dialog.is_visible(timeout=1_000) else ""
        cleared = "예약 등록 실패" not in edited_text and "다시 시도" not in edited_text
        report.record(
            "menu-schedule-error-clears-on-edit",
            called and has_hint and cleared,
            f"cleared={cleared}; text={edited_text[:300]}",
        )
        close_dialogs(page)
    except Exception as exc:
        report.record("menu-schedule-failure-stays-open", False, repr(exc))
        report.record("menu-schedule-error-clears-on-edit", False, repr(exc))
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
        dialog = page.locator("[role='dialog']", has_text="결과 삭제").last
        dialog.wait_for(state="visible", timeout=5_000)
        not_removed_before_confirm = page.locator("[data-report-id='qa-menu-report']").count() == 1
        dialog.locator("button", has_text="취소").click(timeout=5_000)
        page.wait_for_timeout(300)
        still_visible_after_cancel = page.locator("[data-report-id='qa-menu-report']").count() == 1
        click_menu_label(page, "삭제")
        dialog = page.locator("[role='dialog']", has_text="결과 삭제").last
        dialog.wait_for(state="visible", timeout=5_000)
        dialog.locator("button", has_text="삭제하기").click(timeout=5_000)
        page.locator("[data-report-id='qa-menu-report']").wait_for(state="detached", timeout=5_000)
        removed = page.locator("[data-report-id='qa-menu-report']").count() == 0
        ok = not_removed_before_confirm and still_visible_after_cancel and removed
        record_action("삭제", ok, f"not_removed_before_confirm={not_removed_before_confirm}; still_visible_after_cancel={still_visible_after_cancel}; card_removed={removed}")
        report.record("menu-delete-confirmation", ok, f"card_removed={removed}")
    except Exception as exc:
        record_action("삭제", False, repr(exc))
        report.record("menu-delete-confirmation", False, repr(exc))

    report.notes.append("Result-card action menu QA mocks NotebookLM, schedule, rewrite, event extraction, video QA, and binary export APIs to avoid external side effects.")
    context.close()


def run_history_clear_suite(browser, report: QaReport) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    seed_menu_context(context)
    page = context.new_page()
    native_dialog_seen = False

    def on_dialog(dialog) -> None:
        nonlocal native_dialog_seen
        native_dialog_seen = True
        dialog.dismiss()

    page.on("dialog", on_dialog)
    page.on("console", lambda msg: report.console_errors.append(f"[history-clear] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: report.console_errors.append(f"[history-clear] {exc}"))
    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60_000)
        if page.locator("aside[role='navigation']").count() == 0 or not page.locator("aside[role='navigation']").is_visible():
            page.locator("header button").first.click(timeout=5_000, force=True)
            page.locator("aside[role='navigation']").wait_for(state="visible", timeout=10_000)
        sidebar = page.locator("aside[role='navigation']")
        clear_button = sidebar.locator("button", has_text="전체 삭제")
        clear_button.wait_for(state="visible", timeout=10_000)
        before_clear_visible = True
        clear_button.click(timeout=10_000)
        app_dialog = page.locator("[role='dialog']", has_text="전체 히스토리 삭제").last
        try:
            app_dialog.wait_for(state="visible", timeout=1_000)
            app_dialog_visible = True
        except Exception:
            app_dialog_visible = False
        not_removed_before_confirm = sidebar.locator("button", has_text="전체 삭제").count() > 0
        still_visible_after_cancel = False
        removed_after_confirm = False
        if app_dialog_visible:
            app_dialog.locator("button", has_text="취소").click(timeout=5_000)
            page.wait_for_timeout(300)
            still_visible_after_cancel = sidebar.locator("button", has_text="전체 삭제").count() > 0
            clear_button = sidebar.locator("button", has_text="전체 삭제")
            clear_button.wait_for(state="visible", timeout=10_000)
            clear_button.click(timeout=10_000)
            app_dialog = page.locator("[role='dialog']", has_text="전체 히스토리 삭제").last
            app_dialog.wait_for(state="visible", timeout=5_000)
            app_dialog.locator("button", has_text="삭제하기").click(timeout=5_000)
            removed_after_confirm = wait_until(lambda: sidebar.locator("button", has_text="전체 삭제").count() == 0, 5_000, page)
        report.record(
            "history-clear-confirmation",
            before_clear_visible and (not native_dialog_seen) and app_dialog_visible and not_removed_before_confirm and still_visible_after_cancel and removed_after_confirm,
            (
                f"native_dialog_seen={native_dialog_seen}; app_dialog_visible={app_dialog_visible}; "
                f"before_clear_visible={before_clear_visible}; not_removed_before_confirm={not_removed_before_confirm}; "
                f"still_visible_after_cancel={still_visible_after_cancel}; removed_after_confirm={removed_after_confirm}"
            ),
        )
    except Exception as exc:
        report.record("history-clear-confirmation", False, repr(exc))
    finally:
        context.close()


def run_no_native_confirm_suite(report: QaReport) -> None:
    pattern = re.compile(r"(?<![A-Za-z0-9_])(?:window\.)?confirm\s*\(")
    offenders: list[str] = []
    ignored_dirs = {"node_modules", ".next", "out", "dist", "build"}
    for path in (ROOT / "frontend").rglob("*"):
        if any(part in ignored_dirs for part in path.parts):
            continue
        if path.suffix not in {".ts", ".tsx"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                rel = path.relative_to(ROOT).as_posix()
                offenders.append(f"{rel}:{lineno}:{line.strip()[:120]}")
    report.record(
        "no-native-confirm-destructive",
        not offenders,
        "clean" if not offenders else " | ".join(offenders[:20]),
    )


def run_no_native_alert_suite(report: QaReport) -> None:
    pattern = re.compile(r"(?<![A-Za-z0-9_])(?:window\.)?alert\s*\(")
    offenders: list[str] = []
    ignored_dirs = {"node_modules", ".next", "out", "dist", "build"}
    for path in (ROOT / "frontend").rglob("*"):
        if any(part in ignored_dirs for part in path.parts):
            continue
        if path.suffix not in {".ts", ".tsx"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                rel = path.relative_to(ROOT).as_posix()
                offenders.append(f"{rel}:{lineno}:{line.strip()[:120]}")
    report.record(
        "no-native-alerts",
        not offenders,
        "clean" if not offenders else " | ".join(offenders[:20]),
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
            "content": "직접 API 회귀 테스트입니다. ChatMock 5.5 경로로 짧은 한국어 요약을 생성합니다. 이 문장은 50자 이상입니다.",
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

        def recycle_browser() -> None:
            nonlocal browser
            browser.close()
            browser = p.chromium.launch(headless=True)

        run_onboarding_provider_accessibility_suite(browser, report)
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
            header_model = page.locator("[data-testid='header-model-badge']")
            header_status = page.locator("[data-testid='header-status-badge']")
            header_model_text = header_model.inner_text(timeout=5_000).replace("모델 ", "", 1).strip() if header_model.count() > 0 else ""
            header_ok = (
                header_model.count() > 0
                and header_status.count() > 0
                and header_model.get_attribute("aria-label", timeout=5_000) == f"선택 모델: {header_model_text}"
                and header_status.get_attribute("role", timeout=5_000) == "status"
                and header_status.get_attribute("aria-live", timeout=5_000) == "polite"
                and header_status.get_attribute("aria-label", timeout=5_000) == "작업 상태: 소스 대기"
            )
            report.record("header-status-summary", header_ok, screenshot(page, "header-status-summary.png") if header_ok else "header model/status badges missing or not exposed to assistive tech")
            settings_trigger = page.locator("[data-testid='header-settings-trigger']").first
            settings_trigger_initial = (
                settings_trigger.count() == 1
                and settings_trigger.get_attribute("aria-haspopup", timeout=5_000) == "dialog"
                and settings_trigger.get_attribute("aria-controls", timeout=5_000) == "settings-dialog"
                and settings_trigger.get_attribute("aria-expanded", timeout=5_000) == "false"
                and settings_trigger.get_attribute("aria-label", timeout=5_000) == "설정 열기"
            )
            if settings_trigger.count() == 1:
                settings_trigger.click(timeout=10_000)
            settings_dialog = page.locator("#settings-dialog")
            settings_dialog_open = wait_until(
                lambda: settings_dialog.count() == 1
                and settings_dialog.is_visible()
                and settings_dialog.get_attribute("role", timeout=1_000) == "dialog"
                and settings_trigger.get_attribute("aria-expanded", timeout=1_000) == "true"
                and settings_trigger.get_attribute("aria-label", timeout=1_000) == "설정 닫기",
                5_000,
                page,
            )
            settings_close_label_ok = (
                settings_dialog.get_by_role("button", name="닫기").count() > 0
                and settings_dialog.get_by_role("button", name="Close").count() == 0
            )
            page.keyboard.press("Escape")
            settings_dialog_closed = wait_until(
                lambda: (settings_dialog.count() == 0 or not settings_dialog.is_visible())
                and settings_trigger.get_attribute("aria-expanded", timeout=1_000) == "false"
                and settings_trigger.get_attribute("aria-label", timeout=1_000) == "설정 열기",
                5_000,
                page,
            )
            settings_focus_returned = settings_trigger.count() == 1 and settings_trigger.evaluate("el => document.activeElement === el")
            report.record(
                "header-settings-trigger-accessible",
                settings_trigger_initial and settings_dialog_open and settings_close_label_ok and settings_dialog_closed and settings_focus_returned,
                "header settings trigger exposes dialog state, Korean close label, stateful labels, and returns focus after close" if settings_trigger_initial and settings_dialog_open and settings_close_label_ok and settings_dialog_closed and settings_focus_returned else f"initial={settings_trigger_initial}; open={settings_dialog_open}; close_label={settings_close_label_ok}; closed={settings_dialog_closed}; focus_returned={settings_focus_returned}",
            )
            sidebar_trigger = page.locator("header button").first
            sidebar = page.locator("#app-sidebar")
            sidebar_initial = sidebar_trigger.get_attribute("aria-expanded", timeout=5_000) == "true"
            sidebar_open_label = sidebar_trigger.get_attribute("aria-label", timeout=5_000) == "메뉴 닫기"
            sidebar_linked = (
                sidebar_trigger.get_attribute("aria-controls", timeout=5_000) == "app-sidebar"
                and sidebar.get_attribute("id", timeout=5_000) == "app-sidebar"
                and sidebar.get_attribute("role", timeout=5_000) == "navigation"
                and sidebar.get_attribute("aria-label", timeout=5_000) == "사이드바 내비게이션"
            )
            sidebar_trigger.click(timeout=10_000)
            sidebar_collapsed = sidebar_trigger.get_attribute("aria-expanded", timeout=5_000) == "false"
            sidebar_closed_label = sidebar_trigger.get_attribute("aria-label", timeout=5_000) == "메뉴 열기"
            sidebar_hidden = (
                sidebar.get_attribute("aria-hidden", timeout=5_000) == "true"
                and sidebar.evaluate("el => el.inert === true")
            )
            report.record(
                "sidebar-trigger-accessible",
                sidebar_initial and sidebar_open_label and sidebar_linked and sidebar_collapsed and sidebar_closed_label and sidebar_hidden,
                "sidebar trigger exposes controls, expanded state, stateful labels, and hides collapsed navigation" if sidebar_initial and sidebar_open_label and sidebar_linked and sidebar_collapsed and sidebar_closed_label and sidebar_hidden else f"initial={sidebar_initial}; open_label={sidebar_open_label}; linked={sidebar_linked}; collapsed={sidebar_collapsed}; closed_label={sidebar_closed_label}; hidden={sidebar_hidden}",
            )
            if sidebar_collapsed:
                sidebar_trigger.click(timeout=10_000)
            sidebar_reopened = sidebar_trigger.get_attribute("aria-expanded", timeout=5_000) == "true"
            new_analysis = page.get_by_role("button", name="새 분석")
            new_analysis.focus(timeout=10_000)
            sidebar_focus_inside = new_analysis.evaluate("el => document.activeElement === el")
            page.keyboard.press("Escape")
            sidebar_escape_collapsed = sidebar_trigger.get_attribute("aria-expanded", timeout=5_000) == "false"
            sidebar_escape_hidden = (
                sidebar.get_attribute("aria-hidden", timeout=5_000) == "true"
                and sidebar.evaluate("el => el.inert === true")
            )
            sidebar_focus_returned = sidebar_trigger.evaluate("el => document.activeElement === el")
            report.record(
                "sidebar-escape-close-accessible",
                sidebar_reopened and sidebar_focus_inside and sidebar_escape_collapsed and sidebar_escape_hidden and sidebar_focus_returned,
                "sidebar closes with Escape, hides navigation, and returns focus to trigger" if sidebar_reopened and sidebar_focus_inside and sidebar_escape_collapsed and sidebar_escape_hidden and sidebar_focus_returned else f"reopened={sidebar_reopened}; focus_inside={sidebar_focus_inside}; collapsed={sidebar_escape_collapsed}; hidden={sidebar_escape_hidden}; focus_returned={sidebar_focus_returned}",
            )
            if sidebar_escape_collapsed:
                sidebar_trigger.click(timeout=10_000)
            expected_copy = ["요약", "튜토리얼", "앱 아이디어", "뉴스레터", "짧게", "보통", "길게", "대화체", "설명체", "한국어", "아직 결과가 없습니다"]
            missing_copy = [label for label in expected_copy if page.get_by_text(label, exact=True).count() == 0]
            report.record(
                "studio-copy-polish",
                not missing_copy,
                screenshot(page, "studio-copy-polish.png") if not missing_copy else f"missing={missing_copy}",
            )
            empty_state = page.locator("[data-testid='studio-empty-state']").first
            empty_visible = empty_state.count() > 0 and empty_state.is_visible()
            empty_text = empty_state.inner_text(timeout=10_000) if empty_visible else ""
            empty_required = ["1. 소스 입력", "2. 산출물 설계", "3. Generate Dock", "4. Result Workbench"]
            empty_missing = [label for label in empty_required if label not in empty_text]
            report.record(
                "studio-empty-state-guidance",
                empty_visible and not empty_missing,
                screenshot(page, "studio-empty-state-guidance.png") if empty_visible and not empty_missing else f"missing={empty_missing}; text={empty_text[:300]!r}",
            )
            page.locator("main").evaluate("(el) => { el.scrollTop = 650; }")
            page.wait_for_timeout(200)
            empty_box = empty_state.bounding_box()
            dock_box = page.locator("[data-testid='generate-dock-button']").locator("xpath=ancestor::section[1]").bounding_box()
            overlaps = bool(
                empty_box
                and dock_box
                and not (
                    empty_box["y"] + empty_box["height"] <= dock_box["y"]
                    or dock_box["y"] + dock_box["height"] <= empty_box["y"]
                )
            )
            report.record(
                "generate-dock-empty-state-clearance",
                empty_visible and empty_box is not None and dock_box is not None and not overlaps,
                (
                    screenshot(page, "generate-dock-empty-state-clearance.png")
                    if empty_visible and empty_box is not None and dock_box is not None and not overlaps
                    else f"empty={empty_box}; dock={dock_box}; overlaps={overlaps}"
                ),
            )
            empty_dock_text = page.locator("[data-testid='generate-dock']").inner_text(timeout=10_000)
            page.locator("main").evaluate("(el) => { el.scrollTop = 0; }")
            result_toolbar = page.locator("[data-testid='studio-result-toolbar']").first
            result_toolbar_text = result_toolbar.inner_text(timeout=10_000)
            empty_notice_visible = result_toolbar.locator("[data-testid='result-toolbar-empty-notice']").count() > 0
            filter_label_visible = result_toolbar.get_by_text("필터", exact=True).count() > 0
            report.record(
                "result-workbench-empty-controls",
                empty_notice_visible and not filter_label_visible and "필터와 보기 모드" in result_toolbar_text,
                (
                    screenshot(page, "result-workbench-empty-controls.png")
                    if empty_notice_visible and not filter_label_visible and "필터와 보기 모드" in result_toolbar_text
                    else f"notice={empty_notice_visible}; filter_label={filter_label_visible}; text={result_toolbar_text[:300]!r}"
                ),
            )
            panel = page.locator("[data-testid='studio-right-panel']").first
            empty_action_texts: dict[str, str] = {}
            for action_id in ["prompt", "nlm", "rewrite"]:
                panel.locator(f"[data-testid='quick-action-{action_id}']").click(timeout=10_000)
                notice = panel.locator("[data-testid='quick-action-export-status']")
                text = notice.inner_text(timeout=2_000) if notice.count() > 0 else ""
                empty_action_texts[action_id] = text
            report.record(
                "right-panel-empty-action-feedback",
                all("먼저 결과를 생성하세요" in text for text in empty_action_texts.values()),
                (
                    screenshot(page, "right-panel-empty-action-feedback.png")
                    if all("먼저 결과를 생성하세요" in text for text in empty_action_texts.values())
                    else str(empty_action_texts)
                ),
            )
            readable_copy = [
                "분석할 소스를 준비하세요",
                "텍스트",
                "파일",
                "음성",
                "작업 요약",
                "현재 설정",
                "빠른 액션",
                "최근 NLM 산출물",
                "최근 결과",
            ]
            body_text = page.locator("body").inner_text(timeout=10_000)
            missing_readable = [label for label in readable_copy if label not in body_text]
            has_mojibake = "??" in body_text
            report.record(
                "studio-copy-readable",
                not missing_readable and not has_mojibake,
                screenshot(page, "studio-copy-readable.png") if not missing_readable and not has_mojibake else f"missing={missing_readable}; has_mojibake={has_mojibake}",
            )
            status_label_required = ["모드 개별 생성", "보통 · 대화체 · 한국어"]
            status_label_forbidden = ["모드 individual", "medium · conversational · ko"]
            missing_status_labels = [label for label in status_label_required if label not in body_text]
            raw_status_labels = [label for label in status_label_forbidden if label in body_text]
            report.record(
                "studio-status-labels",
                not missing_status_labels and not raw_status_labels,
                screenshot(page, "studio-status-labels.png") if not missing_status_labels and not raw_status_labels else f"missing={missing_status_labels}; raw={raw_status_labels}",
            )
            page.locator("#url-input").fill("https://www.youtube.com/watch?v=aaaaaaaaaaa")
            page.locator("#url-input").press("Enter")
            page.locator("#url-input").fill("https://www.youtube.com/watch?v=bbbbbbbbbbb")
            page.locator("#url-input").press("Enter")
            wait_until(lambda: "소스 2개" in page.locator("[data-testid='generate-dock-summary']").inner_text(timeout=1_000), 10_000, page)
            page.locator("[data-testid='blueprint-mode-combined']").click(timeout=10_000)
            page.locator("[data-testid='source-tab-text']").click(timeout=10_000)
            page.locator("[data-testid='text-source-panel'] textarea").fill(
                "Generate Dock source summary QA text. This source is long enough to become a valid text input."
            )
            page.wait_for_timeout(300)
            dock_summary = page.locator("[data-testid='generate-dock-summary']").inner_text(timeout=10_000)
            report.record(
                "generate-dock-source-summary",
                "텍스트 소스" in dock_summary and "소스 1개" in dock_summary,
                screenshot(page, "generate-dock-source-summary.png") if "텍스트 소스" in dock_summary and "소스 1개" in dock_summary else dock_summary,
            )
            ready_dock_text = page.locator("[data-testid='generate-dock']").inner_text(timeout=10_000)
            state_copy_ok = "소스를 추가하세요" in empty_dock_text and "생성 준비 완료" in ready_dock_text and "Ready to Generate" not in empty_dock_text + ready_dock_text
            report.record(
                "generate-dock-state-copy",
                state_copy_ok,
                screenshot(page, "generate-dock-state-copy.png") if state_copy_ok else f"empty={empty_dock_text!r}; ready={ready_dock_text!r}",
            )
            right_mode = page.locator("[data-testid='right-panel-setting-mode']").inner_text(timeout=10_000)
            effective_mode_ok = "개별 생성" in right_mode and "통합 생성" not in right_mode and "모드 개별 생성" in dock_summary
            report.record(
                "right-panel-effective-mode",
                effective_mode_ok,
                screenshot(page, "right-panel-effective-mode.png") if effective_mode_ok else f"dock={dock_summary!r}; right={right_mode!r}",
            )
            mode_hint = page.locator("[data-testid='blueprint-mode-hint']")
            individual_mode = page.locator("[data-testid='blueprint-mode-individual']")
            combined_mode = page.locator("[data-testid='blueprint-mode-combined']")
            fusion_mode = page.locator("[data-testid='blueprint-mode-fusion']")
            mode_hint_text = mode_hint.inner_text(timeout=2_000) if mode_hint.count() > 0 else ""
            individual_checked = individual_mode.get_attribute("aria-checked", timeout=2_000) == "true" if individual_mode.count() > 0 else False
            combined_disabled = combined_mode.is_disabled(timeout=2_000) if combined_mode.count() > 0 else False
            fusion_disabled = fusion_mode.is_disabled(timeout=2_000) if fusion_mode.count() > 0 else False
            contextual_mode_ok = (
                "개별 생성" in mode_hint_text
                and "통합/퓨전" in mode_hint_text
                and individual_checked
                and combined_disabled
                and fusion_disabled
            )
            report.record(
                "blueprint-contextual-mode",
                contextual_mode_ok,
                (
                    screenshot(page, "blueprint-contextual-mode.png")
                    if contextual_mode_ok
                    else f"hint={mode_hint_text!r}; individual={individual_checked}; combined_disabled={combined_disabled}; fusion_disabled={fusion_disabled}"
                ),
            )
            mode_status_ok = (
                mode_hint.count() == 1
                and mode_hint.get_attribute("role", timeout=2_000) == "status"
                and mode_hint.get_attribute("aria-live", timeout=2_000) == "polite"
                and combined_mode.get_attribute("aria-disabled", timeout=2_000) == "true"
                and fusion_mode.get_attribute("aria-disabled", timeout=2_000) == "true"
                and combined_mode.get_attribute("aria-describedby", timeout=2_000) == "blueprint-mode-hint"
                and fusion_mode.get_attribute("aria-describedby", timeout=2_000) == "blueprint-mode-hint"
            )
            report.record(
                "blueprint-mode-accessible-status",
                mode_status_ok,
                "blueprint mode hint is a live status and disabled modes expose aria-disabled" if mode_status_ok else f"role={mode_hint.get_attribute('role') if mode_hint.count() else None}; live={mode_hint.get_attribute('aria-live') if mode_hint.count() else None}; combined_aria_disabled={combined_mode.get_attribute('aria-disabled') if combined_mode.count() else None}; fusion_aria_disabled={fusion_mode.get_attribute('aria-disabled') if fusion_mode.count() else None}",
            )
            page.evaluate("window.dispatchEvent(new Event('insight-engine-new-analysis'))")
            page.locator("#url-input").wait_for(state="visible", timeout=10_000)
            page.wait_for_timeout(300)
            advanced_controls = [
                "blueprint-web-search",
                "blueprint-web-research",
                "blueprint-deep-comments",
                "blueprint-agent-mode",
                "blueprint-detail-level",
                "blueprint-model-summary",
            ]
            missing_controls = [test_id for test_id in advanced_controls if page.locator(f"[data-testid='{test_id}']").count() == 0]
            report.record(
                "output-blueprint-advanced",
                not missing_controls,
                screenshot(page, "output-blueprint-advanced.png") if not missing_controls else f"missing={missing_controls}",
            )
            page.locator("[data-testid='source-tab-url']").click(timeout=10_000)
            page.locator("#url-input").wait_for(state="visible", timeout=10_000)
            empty_url_submit = page.locator("#url-input").locator("xpath=following-sibling::button").nth(1)
            empty_url_disabled = empty_url_submit.is_disabled(timeout=5_000)
            empty_url_label = empty_url_submit.get_attribute("aria-label") or ""
            report.record(
                "url-empty-submit-disabled",
                empty_url_disabled and "URL" in empty_url_label,
                (
                    screenshot(page, "url-empty-submit-disabled.png")
                    if empty_url_disabled and "URL" in empty_url_label
                    else f"disabled={empty_url_disabled}; aria={empty_url_label!r}"
                ),
            )
            page.locator("[data-testid='source-tab-text']").click(timeout=10_000)
            page.locator("[data-testid='text-source-panel'] textarea").fill(
                "New analysis reset QA text. This source is long enough to make the Generate Dock active."
            )
            page.wait_for_timeout(300)
            before_reset_summary = page.locator("[data-testid='generate-dock-summary']").inner_text(timeout=10_000)
            page.get_by_role("button", name="새 분석").click(timeout=10_000)
            url_visible_after_reset = wait_until(
                lambda: page.locator("#url-input").count() > 0 and page.locator("#url-input").first.is_visible(),
                3_000,
                page,
            )
            after_reset_summary = page.locator("[data-testid='generate-dock-summary']").inner_text(timeout=10_000)
            reset_button = page.locator("#url-input").locator("xpath=following-sibling::button").nth(1) if url_visible_after_reset else None
            reset_button_disabled = bool(reset_button and reset_button.is_disabled(timeout=2_000))
            report.record(
                "new-analysis-resets-source-draft",
                "텍스트 소스" in before_reset_summary
                and url_visible_after_reset
                and "URL 소스 대기" in after_reset_summary
                and reset_button_disabled,
                (
                    screenshot(page, "new-analysis-resets-source-draft.png")
                    if "텍스트 소스" in before_reset_summary
                    and url_visible_after_reset
                    and "URL 소스 대기" in after_reset_summary
                    and reset_button_disabled
                    else f"before={before_reset_summary!r}; after={after_reset_summary!r}; url_visible={url_visible_after_reset}; disabled={reset_button_disabled}"
                ),
            )
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
                tab = page.locator(f"[data-testid='{tab_test_id}']").first
                panel_locator = page.locator(f"[data-testid='{panel_test_id}']")
                tab.wait_for(state="visible", timeout=10_000)
                tab.scroll_into_view_if_needed(timeout=10_000)
                tab.click(timeout=10_000)
                try:
                    panel_locator.wait_for(state="visible", timeout=4_000)
                except PlaywrightTimeoutError:
                    tab.evaluate("(el) => el.click()")
                    panel_locator.wait_for(state="visible", timeout=10_000)
                file_input = page.locator(f"[data-testid='{panel_test_id}'] input[type='file']").first
                file_input.set_input_files(str(source_path))
                page.locator(f"[data-testid='{panel_test_id}']").get_by_text(filename).wait_for(state="visible", timeout=10_000)
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
            dialog = page.locator("[role='dialog']")
            dialog_text = dialog.inner_text(timeout=5_000)
            ok = "ChatMock" in dialog_text or "GPT-5.5" in dialog_text or "5.5" in dialog_text
            report.record("settings-open", True, settings_png)
            report.record("provider-chatmock", ok, "settings popover contains ChatMock/GPT-5.5" if ok else dialog_text[:300])
            metrics = dialog.evaluate(
                """el => {
                    const rect = el.getBoundingClientRect();
                    const style = getComputedStyle(el);
                    return {
                        top: rect.top,
                        bottom: rect.bottom,
                        viewportHeight: window.innerHeight,
                        scrollHeight: el.scrollHeight,
                        clientHeight: el.clientHeight,
                        overflowY: style.overflowY,
                    };
                }"""
            )
            fits = metrics["top"] >= 8 and metrics["bottom"] <= metrics["viewportHeight"] - 8
            scrolls = metrics["scrollHeight"] <= metrics["clientHeight"] or metrics["overflowY"] in ("auto", "scroll")
            report.record(
                "settings-popover-scroll",
                fits and scrolls,
                f"metrics={metrics}" if fits and scrolls else f"clipped_or_unscrollable={metrics}",
            )
            title = dialog.locator("[data-testid='settings-popover-title']")
            close_button = dialog.locator("[data-testid='settings-popover-close']")
            labelledby = dialog.get_attribute("aria-labelledby", timeout=2_000) or ""
            describedby = dialog.get_attribute("aria-describedby", timeout=2_000) or ""
            dialog_a11y_initial_ok = (
                labelledby
                and title.count() == 1
                and title.get_attribute("id", timeout=2_000) == labelledby
                and "settings-popover-desc" in describedby
                and dialog.get_attribute("aria-modal", timeout=2_000) == "true"
                and close_button.count() == 1
                and close_button.get_attribute("aria-label", timeout=2_000) == "생성 설정 닫기"
                and close_button.evaluate("el => document.activeElement === el")
            )
            active_inside_settings = lambda: dialog.evaluate("dialog => dialog.contains(document.activeElement)")
            page.keyboard.press("Shift+Tab")
            backward_wrap_ok = wait_until(active_inside_settings, 3_000, page)
            focusable_count = dialog.evaluate(
                """
                dialog => {
                    const focusable = Array.from(dialog.querySelectorAll('button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])'))
                        .filter((element) => element.tabIndex >= 0 && element.getAttribute('aria-hidden') !== 'true' && (element.offsetWidth > 0 || element.offsetHeight > 0 || element.getClientRects().length > 0));
                    if (focusable.length > 0) focusable[focusable.length - 1].focus();
                    return focusable.length;
                }
                """
            )
            page.keyboard.press("Tab")
            forward_wrap_ok = wait_until(lambda: close_button.evaluate("el => document.activeElement === el"), 3_000, page)
            trigger_focused_during_trap = page.locator("[data-testid='settings-popover-trigger']").first.evaluate("el => document.activeElement === el")
            focus_trap_ok = backward_wrap_ok and forward_wrap_ok and focusable_count > 1 and not trigger_focused_during_trap
            report.record(
                "settings-popover-focus-trap",
                focus_trap_ok,
                (
                    "settings dialog Tab and Shift+Tab focus stays inside dialog"
                    if focus_trap_ok
                    else f"backward={backward_wrap_ok}; forward={forward_wrap_ok}; focusable={focusable_count}; trigger_focused={trigger_focused_during_trap}"
                ),
            )

            style_group = dialog.locator("[data-testid='settings-style-options']")
            blog_style = dialog.locator("[data-testid='settings-style-blog_seo']")
            summary_style = dialog.locator("[data-testid='settings-style-summary']")
            course_style = dialog.locator("[data-testid='settings-style-course']")
            initial_style_ok = (
                style_group.get_attribute("role", timeout=5_000) == "radiogroup"
                and style_group.get_attribute("aria-label", timeout=5_000) == "스타일"
                and blog_style.get_attribute("role", timeout=5_000) == "radio"
                and blog_style.get_attribute("aria-checked", timeout=5_000) == "true"
                and summary_style.get_attribute("aria-checked", timeout=5_000) == "false"
            )
            blog_style.focus(timeout=10_000)
            page.keyboard.press("ArrowRight")
            summary_style_ok = wait_until(
                lambda: summary_style.get_attribute("aria-checked", timeout=1_000) == "true"
                and summary_style.evaluate("el => document.activeElement === el"),
                5_000,
                page,
            )
            page.keyboard.press("End")
            course_style_ok = wait_until(
                lambda: course_style.get_attribute("aria-checked", timeout=1_000) == "true"
                and course_style.evaluate("el => document.activeElement === el"),
                5_000,
                page,
            )
            style_ok = initial_style_ok and summary_style_ok and course_style_ok
            report.record(
                "style-selection",
                style_ok,
                "settings style radiogroup and keyboard navigation update selection" if style_ok else f"initial={initial_style_ok}; summary={summary_style_ok}; course={course_style_ok}",
            )

            length_group = dialog.locator("[data-testid='settings-length-options']")
            length_medium = dialog.locator("[data-testid='settings-length-medium']")
            length_long = dialog.locator("[data-testid='settings-length-long']")
            tone_group = dialog.locator("[data-testid='settings-tone-options']")
            tone_conversational = dialog.locator("[data-testid='settings-tone-conversational']")
            tone_expert = dialog.locator("[data-testid='settings-tone-expert']")
            language_group = dialog.locator("[data-testid='settings-language-options']")
            language_ko = dialog.locator("[data-testid='settings-language-ko']")
            language_en = dialog.locator("[data-testid='settings-language-en']")
            modifier_initial_ok = (
                length_group.get_attribute("role", timeout=5_000) == "radiogroup"
                and length_group.get_attribute("aria-label", timeout=5_000) == "길이"
                and length_medium.get_attribute("role", timeout=5_000) == "radio"
                and length_medium.get_attribute("aria-checked", timeout=5_000) == "true"
                and tone_group.get_attribute("role", timeout=5_000) == "radiogroup"
                and tone_group.get_attribute("aria-label", timeout=5_000) == "문체"
                and tone_conversational.get_attribute("aria-checked", timeout=5_000) == "true"
                and language_group.get_attribute("role", timeout=5_000) == "radiogroup"
                and language_group.get_attribute("aria-label", timeout=5_000) == "출력 언어"
                and language_ko.get_attribute("aria-checked", timeout=5_000) == "true"
            )
            length_medium.focus(timeout=10_000)
            page.keyboard.press("ArrowRight")
            length_ok = wait_until(
                lambda: length_long.get_attribute("aria-checked", timeout=1_000) == "true"
                and length_long.evaluate("el => document.activeElement === el"),
                5_000,
                page,
            )
            tone_conversational.focus(timeout=10_000)
            page.keyboard.press("End")
            tone_ok = wait_until(
                lambda: tone_expert.get_attribute("aria-checked", timeout=1_000) == "true"
                and tone_expert.evaluate("el => document.activeElement === el"),
                5_000,
                page,
            )
            language_ko.focus(timeout=10_000)
            page.keyboard.press("ArrowRight")
            language_ok = wait_until(
                lambda: language_en.get_attribute("aria-checked", timeout=1_000) == "true"
                and language_en.evaluate("el => document.activeElement === el"),
                5_000,
                page,
            )
            modifiers_ok = modifier_initial_ok and length_ok and tone_ok and language_ok
            report.record(
                "settings-modifier-accessible",
                modifiers_ok,
                "settings modifier radiogroups and keyboard navigation update selection" if modifiers_ok else f"initial={modifier_initial_ok}; length={length_ok}; tone={tone_ok}; language={language_ok}",
            )
            web_switch = dialog.locator("[data-testid='settings-web-search-switch']")
            web_status = dialog.locator("[data-testid='settings-web-search-status']")
            web_help = dialog.locator("[data-testid='settings-web-search-help']")
            describedby = web_switch.get_attribute("aria-describedby", timeout=2_000) if web_switch.count() > 0 else ""
            web_initial_ok = (
                web_switch.count() == 1
                and web_switch.get_attribute("role", timeout=2_000) == "switch"
                and web_switch.get_attribute("aria-checked", timeout=2_000) == "false"
                and describedby
                and "settings-web-search-help" in describedby
                and "settings-web-search-status" in describedby
                and web_help.count() == 1
                and web_status.count() == 1
                and "꺼짐" in web_status.inner_text(timeout=2_000)
            )
            if web_switch.count() > 0:
                web_switch.focus(timeout=10_000)
                page.keyboard.press("Space")
            web_toggled_ok = wait_until(
                lambda: web_switch.count() == 1
                and web_switch.get_attribute("aria-checked", timeout=1_000) == "true"
                and "켜짐" in web_status.inner_text(timeout=1_000)
                and web_switch.evaluate("el => document.activeElement === el"),
                5_000,
                page,
            )
            web_switch_ok = web_initial_ok and web_toggled_ok
            report.record(
                "settings-web-search-switch-accessible",
                web_switch_ok,
                "settings web search switch help/status and keyboard toggle update" if web_switch_ok else f"initial={web_initial_ok}; toggled={web_toggled_ok}; describedby={describedby!r}",
            )
            settings_trigger = page.locator("[data-testid='settings-popover-trigger']").first
            if close_button.count() > 0:
                close_button.click(timeout=10_000)
            else:
                page.keyboard.press("Escape")
            dialog_closed_ok = wait_until(lambda: dialog.count() == 0 or not dialog.is_visible(), 5_000, page)
            focus_returned_ok = wait_until(lambda: settings_trigger.evaluate("el => document.activeElement === el"), 5_000, page)
            dialog_a11y_ok = bool(dialog_a11y_initial_ok and dialog_closed_ok and focus_returned_ok)
            report.record(
                "settings-popover-dialog-accessible",
                dialog_a11y_ok,
                "settings dialog title, description, close focus, close action, and trigger focus return are wired" if dialog_a11y_ok else f"initial={dialog_a11y_initial_ok}; closed={dialog_closed_ok}; focus_returned={focus_returned_ok}; labelledby={labelledby!r}; describedby={describedby!r}",
            )
        except Exception as exc:
            report.record("settings-open", False, repr(exc))
            report.record("provider-chatmock", False, repr(exc))
            report.record("style-selection", False, repr(exc))
            report.record("settings-modifier-accessible", False, repr(exc))
            report.record("settings-web-search-switch-accessible", False, repr(exc))
            report.record("settings-popover-dialog-accessible", False, repr(exc))
            report.record("settings-popover-focus-trap", False, repr(exc))

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
            toolbar = page.locator("[data-testid='studio-result-toolbar']").first
            toolbar_visible = toolbar.count() > 0 and toolbar.is_visible()
            toolbar_text = toolbar.inner_text(timeout=10_000) if toolbar_visible else ""
            toolbar_required = ["Result Workbench", "전체 결과", "표시 중", "필터"]
            toolbar_missing = [label for label in toolbar_required if label not in toolbar_text]
            report.record(
                "studio-result-toolbar",
                toolbar_visible and not toolbar_missing,
                screenshot(page, "studio-result-toolbar.png") if toolbar_visible and not toolbar_missing else f"missing={toolbar_missing}; text={toolbar_text[:300]!r}",
            )
            workbench = page.locator("[data-testid='result-workbench']").first
            workbench_visible = workbench.count() > 0 and workbench.is_visible()
            report.record("result-workbench", workbench_visible, screenshot(page, "result-workbench.png") if workbench_visible else "workbench panel missing")
            workbench_text = workbench.inner_text(timeout=10_000) if workbench_visible else ""
            expected_workbench_copy = ["본문 복사", "플랫폼 변환", "NLM 가이드", "예약", "이벤트"]
            missing_workbench_copy = [label for label in expected_workbench_copy if label not in workbench_text]
            report.record(
                "result-workbench-copy-readable",
                workbench_visible and not missing_workbench_copy and "??" not in workbench_text,
                screenshot(page, "result-workbench-copy-readable.png") if workbench_visible and not missing_workbench_copy and "??" not in workbench_text else f"missing={missing_workbench_copy}; text={workbench_text[:300]!r}",
            )
            workbench_sections = [
                "workbench-section-read",
                "workbench-section-improve",
                "workbench-section-nlm",
                "workbench-section-export",
                "workbench-section-publish",
                "workbench-section-manage",
            ]
            workbench_actions = [
                "workbench-action-copy-content",
                "workbench-action-prompt",
                "workbench-action-rewrite",
                "workbench-action-nlm-study-guide",
                "workbench-action-export-docx",
                "workbench-action-schedule",
                "workbench-action-delete",
            ]
            missing_sections = [test_id for test_id in workbench_sections + workbench_actions if workbench.locator(f"[data-testid='{test_id}']").count() == 0]
            report.record(
                "result-workbench-sections",
                workbench_visible and not missing_sections,
                screenshot(page, "result-workbench-sections.png") if workbench_visible and not missing_sections else f"missing={missing_sections}",
            )
            semantic_section_ids = [
                "read",
                "improve",
                "nlm",
                "export",
                "publish",
                "manage",
            ]
            semantic_missing: list[str] = []
            for section_id in semantic_section_ids:
                section = workbench.locator(f"[data-testid='workbench-section-{section_id}']")
                labelledby = f"workbench-section-{section_id}-title"
                if (
                    section.count() != 1
                    or section.get_attribute("role", timeout=2_000) != "region"
                    or section.get_attribute("aria-labelledby", timeout=2_000) != labelledby
                    or workbench.locator(f"#{labelledby}").count() != 1
                ):
                    semantic_missing.append(section_id)
            workbench_region_ok = (
                workbench.get_attribute("role", timeout=2_000) == "region"
                and workbench.get_attribute("aria-labelledby", timeout=2_000) == "result-workbench-title"
                and workbench.locator("#result-workbench-title").count() == 1
            )
            export_status = workbench.locator("[data-testid='workbench-export-status']")
            auth_notice = workbench.locator("[data-testid='workbench-nlm-auth-notice']")
            status_semantics_ok = (
                export_status.count() == 0
                and (auth_notice.count() == 0 or auth_notice.get_attribute("role", timeout=2_000) == "status")
            )
            semantic_ok = workbench_visible and workbench_region_ok and not semantic_missing and status_semantics_ok
            report.record(
                "result-workbench-semantic-regions",
                semantic_ok,
                "workbench and action groups expose labelled regions and live statuses" if semantic_ok else f"workbench_region={workbench_region_ok}; missing={semantic_missing}; status={status_semantics_ok}",
            )
            read_action_ids = [
                "workbench-action-copy-title",
                "workbench-action-copy-content",
                "workbench-action-copy-rich",
                "workbench-action-toggle-transcript",
            ]
            missing_read_actions = [test_id for test_id in read_action_ids if workbench.locator(f"[data-testid='{test_id}']").count() == 0]
            report.record(
                "result-workbench-read-actions",
                workbench_visible and not missing_read_actions,
                screenshot(page, "result-workbench-read-actions.png") if workbench_visible and not missing_read_actions else f"missing={missing_read_actions}",
            )
            preview_action_ids = [
                "workbench-action-preview-markdown",
                "workbench-action-preview-html",
                "workbench-action-timeline",
            ]
            missing_preview_actions = [test_id for test_id in preview_action_ids if workbench.locator(f"[data-testid='{test_id}']").count() == 0]
            preview_execution_ok = False
            preview_evidence = f"missing={missing_preview_actions}"
            if workbench_visible and not missing_preview_actions:
                workbench.locator("[data-testid='workbench-action-preview-markdown']").click(timeout=10_000)
                page.locator("[data-testid='result-markdown-preview']").wait_for(state="visible", timeout=10_000)
                markdown_ok = page.locator("[data-testid='result-markdown-preview']").is_visible()
                workbench.locator("[data-testid='workbench-action-preview-html']").click(timeout=10_000)
                page.locator("[data-testid='result-html-preview']").wait_for(state="visible", timeout=10_000)
                html_ok = page.locator("[data-testid='result-html-preview']").is_visible()
                workbench.locator("[data-testid='workbench-action-timeline']").click(timeout=10_000)
                timeline_ok = workbench.locator("[data-testid='workbench-action-timeline']").get_attribute("aria-pressed") == "true"
                preview_execution_ok = markdown_ok and html_ok and timeline_ok
                preview_evidence = screenshot(page, "result-workbench-preview-actions.png") if preview_execution_ok else f"markdown={markdown_ok}; html={html_ok}; timeline={timeline_ok}"
            report.record(
                "result-workbench-preview-actions",
                preview_execution_ok,
                preview_evidence,
            )
            nlm_action_ids = [
                "workbench-action-nlm-video",
                "workbench-action-nlm-infographic",
                "workbench-action-nlm-slide-deck",
                "workbench-action-nlm-mindmap",
                "workbench-action-nlm-quiz",
                "workbench-action-nlm-flashcards",
                "workbench-action-nlm-briefing",
                "workbench-action-nlm-study-guide",
            ]
            missing_nlm_actions = [test_id for test_id in nlm_action_ids if workbench.locator(f"[data-testid='{test_id}']").count() == 0]
            report.record(
                "result-workbench-nlm-all",
                workbench_visible and not missing_nlm_actions,
                screenshot(page, "result-workbench-nlm-all.png") if workbench_visible and not missing_nlm_actions else f"missing={missing_nlm_actions}",
            )
            podcast_removed = (
                workbench.locator("[data-testid='workbench-action-nlm-audio']").count() == 0
                and page.get_by_text("NLM 팟캐스트").count() == 0
            )
            report.record(
                "result-workbench-nlm-podcast-removed",
                workbench_visible and podcast_removed,
                "NLM 팟캐스트 액션 없음" if podcast_removed else screenshot(page, "result-workbench-nlm-podcast-removed-fail.png"),
            )
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

        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(200)
            if page.locator("aside[role='navigation']").count() == 0 or not page.locator("aside[role='navigation']").is_visible():
                page.locator("header button").first.click(timeout=5_000, force=True)
                page.locator("aside[role='navigation']").wait_for(state="visible", timeout=10_000)
            sidebar = page.locator("aside[role='navigation']")
            before_cards = page.locator("[data-report-id]").count()
            delete_button = sidebar.locator("button[aria-label*='삭제']").first
            delete_button.click(timeout=10_000)
            dialog = page.locator("[role='dialog']", has_text="결과 삭제").last
            try:
                dialog.wait_for(state="visible", timeout=1_000)
                dialog_visible = True
            except Exception:
                dialog_visible = False
            not_removed_before_confirm = page.locator("[data-report-id]").count() == before_cards
            still_visible_after_cancel = False
            removed_after_confirm = False
            if dialog_visible:
                dialog.locator("button", has_text="취소").click(timeout=5_000)
                page.wait_for_timeout(300)
                still_visible_after_cancel = page.locator("[data-report-id]").count() == before_cards
                delete_button = sidebar.locator("button[aria-label*='삭제']").first
                delete_button.click(timeout=10_000)
                dialog = page.locator("[role='dialog']", has_text="결과 삭제").last
                dialog.wait_for(state="visible", timeout=5_000)
                dialog.locator("button", has_text="삭제하기").click(timeout=5_000)
                removed_after_confirm = wait_until(lambda: page.locator("[data-report-id]").count() < before_cards, 5_000, page)
            report.record(
                "history-delete-confirmation",
                dialog_visible and not_removed_before_confirm and still_visible_after_cancel and removed_after_confirm,
                (
                    f"dialog_visible={dialog_visible}; before_cards={before_cards}; "
                    f"not_removed_before_confirm={not_removed_before_confirm}; "
                    f"still_visible_after_cancel={still_visible_after_cancel}; removed_after_confirm={removed_after_confirm}"
                ),
            )
        except Exception as exc:
            report.record("history-delete-confirmation", False, repr(exc))

        context.close()

        run_seeded_menu_action_suite(browser, report)
        run_history_clear_suite(browser, report)
        run_no_native_confirm_suite(report)
        run_no_native_alert_suite(report)
        run_notebooklm_auth_notice_suite(browser, report)
        run_non_url_fusion_progress_suite(browser, report)
        run_direct_text_advanced_request_suite(browser, report)
        run_single_url_failure_retains_source_suite(browser, report)
        run_url_chip_reorder_suite(browser, report)
        run_drop_bulk_url_limit_suite(browser, report)
        run_source_composer_accessibility_suite(browser, report)
        run_url_input_accessibility_suite(browser, report)
        run_url_chip_accessibility_suite(browser, report)
        run_source_text_input_accessibility_suite(browser, report)
        run_source_file_input_accessibility_suite(browser, report)
        run_source_voice_input_accessibility_suite(browser, report)
        recycle_browser()
        run_output_blueprint_style_accessibility_suite(browser, report)
        run_output_blueprint_mode_accessibility_suite(browser, report)
        run_output_blueprint_detail_accessibility_suite(browser, report)
        run_output_blueprint_modifier_accessibility_suite(browser, report)
        run_output_blueprint_advanced_accessibility_suite(browser, report)
        run_batch_advanced_request_suite(browser, report)
        run_url_mode_advanced_request_suite(browser, report)
        recycle_browser()
        run_right_panel_suite(browser, report)
        run_mobile_studio_suite(browser, report)
        run_new_analysis_filter_reset_suite(browser, report)
        run_result_toolbar_accessibility_suite(browser, report)
        run_result_filter_accessibility_suite(browser, report)
        run_view_mode_accessibility_suite(browser, report)
        run_generate_dock_minimums_suite(browser, report)
        run_generate_dock_accessibility_suite(browser, report)
        run_empty_workbench_accessibility_suite(browser, report)
        recycle_browser()
        run_help_tour_entrypoint_suite(browser, report)
        run_help_panel_accessible_close_suite(browser, report)
        run_help_panel_focus_trap_suite(browser, report)
        run_guided_tour_accessible_close_suite(browser, report)
        run_guided_tour_focus_trap_suite(browser, report)

        browser.close()

    if report.console_errors:
        # Known browser extension / dev noise should not fail QA; actual app errors are visible in report.
        report.notes.append("브라우저 console error는 참고용으로 기록했습니다.")

    hydration_errors = [
        err for err in report.console_errors
        if "hydrated" in err.lower() or "hydration" in err.lower()
    ]
    report.record(
        "no-hydration-console-errors",
        not hydration_errors,
        "clean" if not hydration_errors else hydration_errors[0][:6000],
    )

    report.write()
    return report.failures


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        (ARTIFACTS / "run_autoqa.crash.log").write_text(traceback.format_exc(), encoding="utf-8")
        raise
