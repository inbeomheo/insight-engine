from services.support.feedback_store import FeedbackStore
from services.support.github_handoff_service import (
    build_issue_body,
    build_issue_payload,
    create_github_issue,
)
from services.support.support_agent_service import handle_support_chat


def _create_feedback_ticket(tmp_path):
    store = FeedbackStore(tmp_path)
    response = handle_support_chat(
        message=(
            "모바일에서 생성 안 되고 token=abc123 "
            "sk-proj-testsecret0000000000000000"
        ),
        route="/generate",
        current_url="https://app.example.com/generate?token=abc123&utm=smoke#local",
        viewport={"width": 390, "height": 844},
        user_agent="pytest-browser",
        console_errors=["Authorization: Bearer should-not-leak"],
        selected_provider="chatmock",
        selected_model="chatmock/gpt-5.3-codex-spark",
        generation_mode="fusion",
        selected_style="blog_seo",
        detail_level="deep",
        mode="feedback",
        user_id="test-user",
        store=store,
    )
    return store, response["ticket"]


def test_support_ticket_stores_redacted_context_and_reproduction(tmp_path):
    _, ticket = _create_feedback_ticket(tmp_path)

    assert ticket["current_url"] == "https://app.example.com/generate?token=[REDACTED]&utm=smoke"
    assert ticket["selected_model"] == "chatmock/gpt-5.3-codex-spark"
    assert ticket["generation_mode"] == "fusion"
    assert ticket["priority"] == "high"
    assert "abc123" not in ticket["message"]
    assert "testsecret" not in ticket["message"]
    assert "should-not-leak" not in "\n".join(ticket["console_errors"])
    assert "재현" not in ticket["message"]
    assert "reproduction" in ticket["metadata"]


def test_issue_body_contains_triage_context_without_secret_values(tmp_path):
    _, ticket = _create_feedback_ticket(tmp_path)

    body = build_issue_body(ticket)
    payload = build_issue_payload(ticket)

    assert "## 자동 분류" in body
    assert "우선순위: `high`" in body
    assert "현재 URL: `https://app.example.com/generate?token=[REDACTED]&utm=smoke`" in body
    assert "생성 모델: `chatmock/gpt-5.3-codex-spark`" in body
    assert "생성 모드: `fusion`" in body
    assert "## 재현 정보" in body
    assert "abc123" not in body
    assert "testsecret" not in body
    assert "should-not-leak" not in body
    assert payload["labels"]
    assert "support-feedback" in payload["labels"]
    assert "priority:high" in payload["labels"]


def test_create_github_issue_uses_mocked_request_and_temp_store(tmp_path, monkeypatch):
    store, ticket = _create_feedback_ticket(tmp_path)
    calls = []

    def fake_github_request(method, path, payload=None):
        calls.append({"method": method, "path": path, "payload": payload})
        return {"html_url": "https://github.com/acme/insight-engine/issues/77", "number": 77}

    monkeypatch.setenv("SUPPORT_GITHUB_REPO", "acme/insight-engine")
    monkeypatch.setattr(
        "services.support.github_handoff_service._github_request",
        fake_github_request,
    )

    result = create_github_issue(ticket["id"], store=store)

    assert result["ticket"]["status"] == "issue_created"
    assert result["ticket"]["github_issue_number"] == 77
    assert calls == [
        {
            "method": "POST",
            "path": "/repos/acme/insight-engine/issues",
            "payload": build_issue_payload(ticket),
        }
    ]
