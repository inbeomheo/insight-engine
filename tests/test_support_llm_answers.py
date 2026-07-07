"""Support Assistant LLM-backed answer tests."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from services.support.feedback_store import FeedbackStore
from services.support.product_knowledge_service import answer_product_question
from services.support.support_agent_service import handle_support_chat


@pytest.fixture
def store(tmp_path):
    return FeedbackStore(base_dir=str(tmp_path))


def _fake_response(text: str):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


def test_support_question_uses_open_ai_llm(monkeypatch):
    monkeypatch.setenv("SUPPORT_ASSISTANT_LLM_ENABLED", "true")
    monkeypatch.setenv("SUPPORT_ASSISTANT_MODEL", "chatmock/gpt-5.3-codex-spark")

    with patch("services.support.product_knowledge_service._completion", return_value=_fake_response("OPEN AI가 자연어로 답한 내용")) as mock_completion:
        result = answer_product_question("퓨전 분석을 실제로 언제 쓰면 좋아?", {"route": "/"})

    assert result["llm_used"] is True
    assert result["fallback_used"] is False
    assert result["answer"] == "OPEN AI가 자연어로 답한 내용"
    assert mock_completion.call_args.kwargs["model"] == "openai/gpt-5.3-codex-spark"


def test_support_question_falls_back_to_faq_when_llm_fails(monkeypatch):
    monkeypatch.setenv("SUPPORT_ASSISTANT_LLM_ENABLED", "true")

    with patch("services.support.product_knowledge_service._completion", side_effect=RuntimeError("boom")):
        result = answer_product_question("퓨전 분석이 뭐야?", {"route": "/"})

    assert result["llm_used"] is False
    assert result["fallback_used"] is True
    assert "퓨전 분석" in result["answer"]
    assert "llm_error" in result


def test_handle_support_chat_question_returns_llm_answer_without_ticket(store):
    with patch("services.support.product_knowledge_service._completion", return_value=_fake_response("자연스럽게 답변했어")):
        result = handle_support_chat(message="공유 링크는 어떻게 써?", mode="auto", store=store)

    assert result["action"] == "answered"
    assert result["reply"] == "자연스럽게 답변했어"
    assert result["answer"]["llm_used"] is True
    assert len(store.list_tickets()) == 0
