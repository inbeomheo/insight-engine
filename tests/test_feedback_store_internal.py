"""내부 테스트/스모크 피드백 분리 검증 (이슈 #49).

QA/스모크 목적 티켓이 운영 피드백 큐에 섞이지 않도록:
- 자동 감지(internal 마커/플래그)로 분류
- list_tickets에서 기본 숨김
- GitHub 핸드오프 대상에서 제외
"""
import pytest

from services.support.feedback_store import FeedbackStore
from services.support.github_handoff_service import (
    GitHubHandoffError,
    create_draft_pr,
    create_github_issue,
)


@pytest.fixture
def store(tmp_path):
    return FeedbackStore(base_dir=str(tmp_path))


def test_explicit_internal_flag_marks_ticket(store):
    ticket = store.create_ticket({"title": "실제 버그", "message": "설명", "internal": True})
    assert ticket["internal"] is True


@pytest.mark.parametrize(
    "title",
    ["[Bug] 버그 접수 테스트", "[Question] 테스트 피드백", "smoke test 실행", "[test] 임시"],
)
def test_auto_detect_internal_markers(store, title):
    # 이슈 #49의 실제 티켓 패턴 및 일반 테스트 마커
    ticket = store.create_ticket({"title": title, "message": "본문"})
    assert ticket["internal"] is True


def test_real_feedback_not_internal(store):
    ticket = store.create_ticket({"title": "모바일 화면이 깨져요", "message": "상세 설명"})
    assert ticket["internal"] is False


def test_internal_marker_in_message_only(store):
    # title에 없고 message에만 마커가 있어도 감지
    ticket = store.create_ticket({"title": "피드백", "message": "이건 테스트 피드백 입니다"})
    assert ticket["internal"] is True


def test_list_hides_internal_by_default(store):
    store.create_ticket({"title": "버그 접수 테스트", "message": "x"})
    store.create_ticket({"title": "실제 피드백", "message": "문제"})
    visible = store.list_tickets()
    titles = [t["title"] for t in visible]
    assert "실제 피드백" in titles
    assert "버그 접수 테스트" not in titles


def test_list_includes_internal_when_requested(store):
    store.create_ticket({"title": "버그 접수 테스트", "message": "x"})
    store.create_ticket({"title": "실제 피드백", "message": "문제"})
    visible = store.list_tickets(include_internal=True)
    assert len(visible) == 2


def test_github_issue_handoff_rejects_internal(store):
    ticket = store.create_ticket({"title": "버그 접수 테스트", "message": "x"})
    with pytest.raises(GitHubHandoffError):
        create_github_issue(ticket["id"], store=store)


def test_draft_pr_handoff_rejects_internal(store):
    ticket = store.create_ticket({"title": "테스트 피드백", "message": "x"})
    with pytest.raises(GitHubHandoffError):
        create_draft_pr(ticket["id"], store=store)


def test_real_feedback_handoff_not_blocked_by_internal_guard(store):
    # 실제 피드백은 internal guard를 통과해야 함.
    # token/repo 미설정이므로 GitHubHandoffError가 나지만, internal 사유가 아니어야 한다.
    ticket = store.create_ticket({"title": "실제 버그", "message": "문제"})
    with pytest.raises(GitHubHandoffError) as exc:
        create_github_issue(ticket["id"], store=store)
    assert "내부 테스트" not in str(exc.value)
