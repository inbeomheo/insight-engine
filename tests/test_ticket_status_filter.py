"""티켓 목록 status 필터 검증 (cycle 6).

list_tickets에 status 파라미터를 추가해 미해결(triaged)만 보기 등
티켓 관리를 지원한다.
"""
import pytest

from services.support.feedback_store import FeedbackStore


@pytest.fixture
def store(tmp_path):
    return FeedbackStore(base_dir=str(tmp_path))


def test_filter_by_status(store):
    store.create_ticket({"title": "열린 티켓", "message": "x", "status": "triaged"})
    store.create_ticket({"title": "닫힌 티켓", "message": "y", "status": "closed"})
    triaged = store.list_tickets(status="triaged")
    closed = store.list_tickets(status="closed")
    assert len(triaged) == 1 and triaged[0]["title"] == "열린 티켓"
    assert len(closed) == 1 and closed[0]["title"] == "닫힌 티켓"
    assert len(store.list_tickets()) == 2


def test_no_filter_returns_all(store):
    store.create_ticket({"title": "a", "message": "x", "status": "triaged"})
    store.create_ticket({"title": "b", "message": "y", "status": "closed"})
    assert len(store.list_tickets()) == 2


def test_filter_combines_with_user_id(store):
    store.create_ticket({"title": "a", "message": "x", "status": "triaged"}, user_id="u1")
    store.create_ticket({"title": "b", "message": "y", "status": "triaged"}, user_id="u2")
    only_u1_triaged = store.list_tickets(user_id="u1", status="triaged")
    assert len(only_u1_triaged) == 1
    assert only_u1_triaged[0]["title"] == "a"


def test_filter_nonexistent_status_returns_empty(store):
    store.create_ticket({"title": "a", "message": "x", "status": "triaged"})
    assert store.list_tickets(status="nonexistent") == []
