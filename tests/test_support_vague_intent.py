"""접수 의도만 있는 문장의 티켓화 방지 검증 (이슈 #48).

"불편사항 접수하고 싶어" 같은 의도만 표현한 짧은 문장이 바로 티켓으로
쌓이지 않도록 구체화를 유도한다.
"""
import pytest

from services.support.feedback_store import FeedbackStore
from services.support.support_agent_service import (
    _is_vague_feedback_intent,
    handle_support_chat,
)


@pytest.fixture
def store(tmp_path):
    return FeedbackStore(base_dir=str(tmp_path))


@pytest.mark.parametrize(
    "text",
    [
        "불편사항 접수하고 싶어",
        "버그 신고하고 싶어",
        "피드백 남기고 싶어",
        "접수하고 싶어",
    ],
)
def test_vague_intent_detected(text):
    assert _is_vague_feedback_intent(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "모바일 메인 화면에서 생성 버튼이 안 눌려요",  # 구체적
        "결제 페이지에서 에러가 나요",
        "퓨전 분석이 뭐야?",  # 질문 (의도 아님)
        "화면이 깨져요",  # 짧아도 구체 힌트('화면','깨') 있음
    ],
)
def test_not_vague(text):
    assert _is_vague_feedback_intent(text) is False


def test_vague_intent_does_not_create_ticket(store):
    # 이슈 #48의 핵심: 의도만 있는 문장은 티켓으로 저장되지 않는다.
    result = handle_support_chat(message="불편사항 접수하고 싶어", mode="auto", store=store)
    assert result["action"] in {"needs_detail", "answered"}
    assert len(store.list_tickets()) == 0


def test_concrete_feedback_creates_ticket(store):
    result = handle_support_chat(
        message="결제 화면에서 에러가 나요", mode="auto", store=store
    )
    assert result["action"] != "needs_detail"
    assert len(store.list_tickets()) == 1


def test_forced_feedback_mode_bypasses_vague_check(store):
    # 명시적 feedback 모드는 사용자 의도를 존중 — vague 검사를 건너뛴다.
    result = handle_support_chat(message="불편사항 접수하고 싶어", mode="feedback", store=store)
    assert result["action"] != "needs_detail"
