"""Orchestrates product support Q&A and feedback ticket creation."""
from __future__ import annotations

from typing import Any

from services.support.feedback_store import FeedbackStore, get_feedback_store
from services.support.feedback_triage_service import classify_message
from services.support.github_handoff_service import github_config_status
from services.support.product_knowledge_service import answer_product_question


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

    ticket = store.create_ticket({
        "kind": triage["kind"],
        "severity": triage["severity"],
        "title": triage["title"],
        "message": text,
        "route": route,
        "viewport": viewport,
        "user_agent": user_agent,
        "console_errors": console_errors or [],
        "screenshot_url": screenshot_url,
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
