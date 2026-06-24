"""Orchestrates product support Q&A and feedback ticket creation."""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from services.support.feedback_store import FeedbackStore, get_feedback_store
from services.support.feedback_triage_service import classify_message
from services.support.github_handoff_service import github_config_status
from services.support.product_knowledge_service import answer_product_question

_AUTH_HEADER_RE = re.compile(r"(?i)\bauthorization\b\s*[:=]\s*(?:bearer\s+)?[^\s,;]+")
_SECRET_RE = re.compile(
    r"(?i)\b(bearer|token|access[_-]?token|refresh[_-]?token|api[_-]?key|password|secret)\b\s*[:=]\s*[^\s,;]+"
)
_QUERY_SECRET_RE = re.compile(
    r"(?i)([?&](?:token|access_token|refresh_token|api_key|key|sig|signature|X-Amz-Signature)=)[^&\s]+"
)
_URL_RE = re.compile(r"https?://[^\s]+")


def _redact_url(match: re.Match[str]) -> str:
    raw = match.group(0)
    try:
        parts = urlsplit(raw)
        safe_query = _QUERY_SECRET_RE.sub(r"\1[REDACTED]", f"?{parts.query}")[1:] if parts.query else ""
        return urlunsplit((parts.scheme, parts.netloc, parts.path, safe_query, ""))
    except Exception:
        return "[REDACTED_URL]"


def redact_diagnostic(value: str) -> str:
    text = str(value or "")
    text = _AUTH_HEADER_RE.sub("authorization=[REDACTED]", text)
    text = _SECRET_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)
    text = _URL_RE.sub(_redact_url, text)
    return text[:500]


def sanitize_console_errors(console_errors: list[str] | None) -> list[str]:
    if not console_errors:
        return []
    return [redact_diagnostic(item) for item in console_errors[-8:]]


# 접수 '의도'만 표현한 짧은 문장 감지 (#48) — 구체 내용이 없으면 티켓 대신 구체화 유도.
_FEEDBACK_INTENT_MARKERS = (
    "접수하고 싶",
    "접수하고싶",
    "불편사항 접수",
    "불편 사항 접수",
    "피드백 접수",
    "피드백 남기",
    "버그 신고",
    "신고하고 싶",
    "접수할래",
)
_CONCRETE_FEEDBACK_HINTS = (
    "화면", "버튼", "페이지", "에러", "오류", "안 됨", "안됨", "안돼",
    "깨", "느려", "느린", "멈", "크래시", "크래쉬", "http", "://", "동작",
)


def _is_vague_feedback_intent(text: str) -> bool:
    """접수 '의도'만 있고 구체 내용이 부족한지 판별 (#48).

    "불편사항 접수하고 싶어" 처럼 의도만 표현한 짧은 문장은 티켓으로 바로
    만들지 않고 구체 입력을 유도한다.
    """
    if len(text) > 24:
        return False
    if not any(marker in text for marker in _FEEDBACK_INTENT_MARKERS):
        return False
    return not any(hint in text for hint in _CONCRETE_FEEDBACK_HINTS)


def handle_support_chat(
    *,
    message: str,
    route: str = "",
    viewport: dict[str, Any] | None = None,
    user_agent: str = "",
    console_errors: list[str] | None = None,
    screenshot_url: str = "",
    mode: str = "auto",
    user_id: str | None = None,
    store: FeedbackStore | None = None,
) -> dict[str, Any]:
    text = (message or "").strip()
    if not text:
        raise ValueError("메시지를 입력해주세요.")

    store = store or get_feedback_store()
    safe_console_errors = sanitize_console_errors(console_errors)
    triage = classify_message(text)
    forced_feedback = mode in {"feedback", "bug", "feature"}
    forced_question = mode == "question"

    if forced_question or (mode == "auto" and triage["kind"] == "question"):
        answer = answer_product_question(text, {"route": route, "viewport": viewport})
        return {
            "reply": answer["answer"],
            "action": "answered",
            "triage": triage,
            "answer": answer,
            "github": github_config_status(),
            "suggested_next_actions": ["불편사항으로 접수", "GitHub 이슈 올리기", "닫기"],
        }

    # 접수 의도만 있고 구체 내용이 부족하면 티켓 대신 구체화를 유도한다 (#48).
    if not forced_feedback and _is_vague_feedback_intent(text):
        return {
            "reply": "접수 도와드릴게요. 어떤 화면에서 어떤 동작이 불편했는지 조금만 더 알려주세요. (예: \"모바일 메인에서 생성 버튼이 안 눌려요\")",
            "action": "needs_detail",
            "triage": triage,
            "github": github_config_status(),
            "suggested_next_actions": ["구체적으로 입력하기", "닫기"],
        }

    ticket = store.create_ticket({
        "kind": triage["kind"],
        "severity": triage["severity"],
        "title": triage["title"],
        "message": text,
        "route": route,
        "viewport": viewport,
        "user_agent": user_agent,
        "console_errors": safe_console_errors,
        "screenshot_url": redact_diagnostic(screenshot_url) if screenshot_url else "",
        "related_files": triage["related_files"],
        "suggested_fix": triage["suggested_fix"],
        "labels": triage["labels"],
        "metadata": {
            "mode": mode,
            "classification_confidence": triage["confidence"],
        },
    }, user_id=user_id)

    kind_label = {
        "bug": "버그",
        "usability": "사용성 불편",
        "feature": "기능 요청",
        "ops": "운영 이슈",
    }.get(ticket["kind"], "피드백")
    file_hint = ""
    if ticket.get("related_files"):
        file_hint = f" 관련 파일 후보는 `{ticket['related_files'][0]}` 쪽으로 보여."

    return {
        "reply": f"{kind_label}로 접수했어. 심각도는 `{ticket['severity']}`로 분류했고,{file_hint} GitHub 이슈로 넘길 수 있어.",
        "action": "ticket_created",
        "ticket": ticket,
        "triage": triage,
        "github": github_config_status(),
        "suggested_next_actions": ["GitHub 이슈 올리기", "Draft PR 만들기", "닫기"],
    }
