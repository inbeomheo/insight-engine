"""비용 발생 라우트의 인증·선예약·환불 경계 회귀 테스트."""
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest
from flask import g

from app import create_app
from services.usage.usage_lock import UsageLockUnavailable
from services.usage.usage_service import UsageAccountingUnavailable, UsageReservation
from src.contexts.identity.application.ports import QuotaReservation
from src.contexts.identity.domain.exceptions import QuotaExceeded


_H = {"Origin": "http://localhost:3000", "Authorization": "Bearer valid-token"}


def _client():
    return create_app({"TESTING": True}).test_client()


def _authenticate(_token):
    g.user_id = "cost-user"
    g.access_token = "valid-token"
    return {"valid": True, "error": None, "code": None}


def _reservation():
    before = {"usage_count": 3, "max_usage": 5, "can_use": True, "is_admin": False}
    after = {**before, "usage_count": 2}
    quota = QuotaReservation(
        reservation_id="cost-reservation",
        idempotency_key="client:key",
        request_fingerprint="a" * 64,
        owner_token_hash="b" * 64,
        amount=1,
        remaining=2,
        max_usage=5,
        owned=True,
        replayed=False,
    )
    return UsageReservation(quota, before, after, True)


def _base_security_patches(stack: ExitStack):
    stack.enter_context(patch(
        "src.contexts.identity.interface.auth_decorators.is_supabase_enabled",
        return_value=True,
    ))
    stack.enter_context(patch(
        "src.contexts.identity.interface.auth_decorators._validate_token",
        side_effect=_authenticate,
    ))
    stack.enter_context(patch(
        "services.usage.usage_decorator.is_supabase_enabled",
        return_value=True,
    ))


@pytest.mark.parametrize(
    ("path", "payload", "cost_target"),
    [
        ("/api/chat", {
            "question": "질문", "context": "충분한 현재 콘텐츠",
        }, "services.core.ai_service.create_chat_response"),
        ("/api/notes", {
            "content": "새 학습 콘텐츠", "source": {"type": "text", "title": "텍스트"},
        }, "services.core.ai_service.create_content"),
        ("/api/rag/graph/ingest", {
            "text": "Python은 프로그래밍 언어입니다.",
        }, "services.rag.graph_rag_engine.GraphRAGEngine.ingest"),
        ("/api/tts", {"text": "안녕하세요"}, "services.media.tts_service.TTSService.synthesize"),
    ],
)
def test_quota_exhaustion_never_enters_cost_function(path, payload, cost_target):
    client = _client()
    lease = MagicMock(lost=False, released=False)
    with ExitStack() as stack:
        _base_security_patches(stack)
        stack.enter_context(patch(
            "services.usage.usage_decorator.acquire_usage_request_lock",
            return_value=lease,
        ))
        reserve = stack.enter_context(patch(
            "services.usage.usage_decorator.UsageService.reserve_for_request",
            side_effect=QuotaExceeded,
        ))
        cost = stack.enter_context(patch(cost_target))
        response = client.post(path, json=payload, headers=_H)

    assert response.status_code == 429
    reserve.assert_called_once_with("cost-user")
    cost.assert_not_called()


@pytest.mark.parametrize(
    ("failure", "expected_code"),
    [
        ("lock", "USAGE_LOCK_UNAVAILABLE"),
        ("reservation", "USAGE_ACCOUNTING_UNAVAILABLE"),
    ],
)
def test_chat_infrastructure_failure_never_calls_ai(failure, expected_code):
    client = _client()
    with ExitStack() as stack:
        _base_security_patches(stack)
        if failure == "lock":
            stack.enter_context(patch(
                "services.usage.usage_decorator.acquire_usage_request_lock",
                side_effect=UsageLockUnavailable("redis unavailable"),
            ))
            reserve = stack.enter_context(patch(
                "services.usage.usage_decorator.UsageService.reserve_for_request"
            ))
        else:
            stack.enter_context(patch(
                "services.usage.usage_decorator.acquire_usage_request_lock",
                return_value=MagicMock(lost=False, released=False),
            ))
            reserve = stack.enter_context(patch(
                "services.usage.usage_decorator.UsageService.reserve_for_request",
                side_effect=UsageAccountingUnavailable("rpc unavailable"),
            ))
        ai_call = stack.enter_context(patch(
            "services.core.ai_service.create_chat_response"
        ))
        response = client.post(
            "/api/chat",
            json={"question": "질문", "context": "현재 콘텐츠"},
            headers=_H,
        )

    assert response.status_code == 503
    assert response.get_json()["code"] == expected_code
    if failure == "lock":
        reserve.assert_not_called()
    ai_call.assert_not_called()


def test_chat_insufficient_evidence_refunds_without_ai():
    client = _client()
    reservation = _reservation()
    with ExitStack() as stack:
        _base_security_patches(stack)
        stack.enter_context(patch(
            "services.usage.usage_decorator.acquire_usage_request_lock",
            return_value=MagicMock(lost=False, released=False),
        ))
        stack.enter_context(patch(
            "services.usage.usage_decorator.UsageService.reserve_for_request",
            return_value=reservation,
        ))
        refund = stack.enter_context(patch(
            "services.usage.usage_decorator.UsageService.refund_reservation",
            return_value=reservation.usage_before,
        ))
        stack.enter_context(patch(
            "services.content.note_index_service.search_notes",
            return_value=[{"id": "low", "score": 0.1}],
        ))
        ai_call = stack.enter_context(patch(
            "services.core.ai_service.create_chat_response"
        ))
        response = client.post(
            "/api/chat",
            json={"question": "질문", "context": "현재 콘텐츠"},
            headers=_H,
        )

    assert response.status_code == 200
    refund.assert_called_once_with("cost-user", reservation)
    ai_call.assert_not_called()


def test_duplicate_note_409_explicitly_refunds_without_ai(tmp_path, monkeypatch):
    from services.content import note_service

    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    note_service.save_note({
        "id": "existing",
        "source": {
            "type": "youtube",
            "url": "https://youtu.be/dQw4w9WgXcQ",
            "title": "기존 영상",
        },
        "key_concepts": ["중복"],
        "summary": "기존 요약",
        "quotes": [],
        "tags": ["테스트"],
        "language": "ko",
        "created_at": "2026-08-01T00:00:00Z",
    }, owner_id="cost-user")
    client = _client()
    reservation = _reservation()
    with ExitStack() as stack:
        _base_security_patches(stack)
        stack.enter_context(patch(
            "services.usage.usage_decorator.acquire_usage_request_lock",
            return_value=MagicMock(lost=False, released=False),
        ))
        stack.enter_context(patch(
            "services.usage.usage_decorator.UsageService.reserve_for_request",
            return_value=reservation,
        ))
        refund = stack.enter_context(patch(
            "services.usage.usage_decorator.UsageService.refund_reservation",
            return_value=reservation.usage_before,
        ))
        ai_call = stack.enter_context(patch("services.core.ai_service.create_content"))
        response = client.post(
            "/api/notes",
            json={
                "content": "중복 원문",
                "source": {
                    "type": "youtube",
                    "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
                    "title": "동일 영상",
                },
            },
            headers=_H,
        )

    assert response.status_code == 409
    refund.assert_called_once_with("cost-user", reservation)
    ai_call.assert_not_called()


def test_oversized_graph_ingest_refunds_and_never_enters_engine():
    client = _client()
    reservation = _reservation()
    with ExitStack() as stack:
        _base_security_patches(stack)
        stack.enter_context(patch(
            "services.usage.usage_decorator.acquire_usage_request_lock",
            return_value=MagicMock(lost=False, released=False),
        ))
        stack.enter_context(patch(
            "services.usage.usage_decorator.UsageService.reserve_for_request",
            return_value=reservation,
        ))
        refund = stack.enter_context(patch(
            "services.usage.usage_decorator.UsageService.refund_reservation_quietly",
            return_value=reservation.usage_before,
        ))
        ingest = stack.enter_context(patch(
            "services.rag.graph_rag_engine.GraphRAGEngine.ingest"
        ))
        response = client.post(
            "/api/rag/graph/ingest",
            json={"text": "x" * 200_001},
            headers=_H,
        )

    assert response.status_code == 400
    refund.assert_called_once_with("cost-user", reservation)
    ingest.assert_not_called()


def test_graph_usage_lock_loss_propagates_to_503_and_refunds():
    client = _client()
    reservation = _reservation()
    with ExitStack() as stack:
        _base_security_patches(stack)
        stack.enter_context(patch(
            "services.usage.usage_decorator.acquire_usage_request_lock",
            return_value=MagicMock(lost=False, released=False),
        ))
        stack.enter_context(patch(
            "services.usage.usage_decorator.UsageService.reserve_for_request",
            return_value=reservation,
        ))
        refund = stack.enter_context(patch(
            "services.usage.usage_decorator.UsageService.refund_reservation_quietly",
            return_value=reservation.usage_before,
        ))
        stack.enter_context(patch(
            "services.rag.graph_rag_engine.GraphRAGEngine.ingest",
            side_effect=UsageLockUnavailable("lease lost"),
        ))

        response = client.post(
            "/api/rag/graph/ingest",
            json={"text": "Python은 프로그래밍 언어입니다."},
            headers=_H,
        )

    assert response.status_code == 503
    assert response.get_json()["code"] == "USAGE_LOCK_UNAVAILABLE"
    refund.assert_called_once_with("cost-user", reservation)


@pytest.mark.parametrize(
    ("path", "payload", "cost_target", "setup_target", "setup_value"),
    [
        (
            "/api/chat",
            {"question": "질문", "context": "충분한 현재 콘텐츠"},
            "services.core.ai_service.create_chat_response",
            "routes.chat_routes._search_related_notes",
            [],
        ),
        (
            "/api/notes",
            {"content": "새 학습 콘텐츠", "source": {"type": "text"}},
            "services.content.note_service.generate_knowledge_note",
            "routes.notes_routes._find_duplicate_notes",
            ("", []),
        ),
        (
            "/api/mindmap",
            {"content": "마인드맵으로 바꿀 충분한 콘텐츠"},
            "services.core.ai_service.create_content",
            None,
            None,
        ),
        (
            "/api/notebooklm/generate",
            {
                "type": "audio",
                "url": "https://example.com/source",
                "source_text": "충분한 원문",
            },
            "routes.notebooklm_routes._service.generate",
            "routes.notebooklm_routes._service.check_auth",
            {"valid": True},
        ),
    ],
)
def test_paid_route_lock_loss_propagates_to_standard_503_and_refunds(
    path,
    payload,
    cost_target,
    setup_target,
    setup_value,
):
    client = _client()
    client.application.config.setdefault("STYLE_PROMPTS", {})["mindmap"] = "변환"
    reservation = _reservation()

    with ExitStack() as stack:
        _base_security_patches(stack)
        stack.enter_context(patch(
            "services.usage.usage_decorator.acquire_usage_request_lock",
            return_value=MagicMock(lost=False, released=False),
        ))
        stack.enter_context(patch(
            "services.usage.usage_decorator.UsageService.reserve_for_request",
            return_value=reservation,
        ))
        refund = stack.enter_context(patch(
            "services.usage.usage_decorator.UsageService.refund_reservation_quietly",
            return_value=reservation.usage_before,
        ))
        if setup_target:
            stack.enter_context(patch(setup_target, return_value=setup_value))
        cost = stack.enter_context(patch(
            cost_target,
            side_effect=UsageLockUnavailable("lease lost"),
        ))

        response = client.post(path, json=payload, headers=_H)

    assert response.status_code == 503
    assert response.get_json()["code"] == "USAGE_LOCK_UNAVAILABLE"
    cost.assert_called_once()
    refund.assert_called_once_with("cost-user", reservation)


def test_playlist_quota_exhaustion_never_enters_provider():
    client = _client()
    lease = MagicMock(lost=False, released=False)
    with ExitStack() as stack:
        _base_security_patches(stack)
        stack.enter_context(patch(
            "services.usage.usage_decorator.acquire_usage_request_lock",
            return_value=lease,
        ))
        stack.enter_context(patch(
            "services.usage.usage_decorator.UsageService.reserve_for_request",
            side_effect=QuotaExceeded,
        ))
        provider = stack.enter_context(patch(
            "services.core.content_service.get_playlist_videos",
        ))
        response = client.post(
            "/api/playlist-videos",
            json={"url": "https://youtube.com/playlist?list=PLquota"},
            headers=_H,
        )

    assert response.status_code == 429
    provider.assert_not_called()


def test_playlist_lock_loss_at_provider_boundary_returns_503_and_refunds():
    client = _client()
    reservation = _reservation()
    lease = MagicMock(lost=False, released=False)
    provider = MagicMock()

    def collect(_url, _max_results, *, on_cost_start=None):
        assert callable(on_cost_start)
        lease.lost = True
        lease.lost_reason = "test lease loss"
        on_cost_start()
        return provider()

    with ExitStack() as stack:
        _base_security_patches(stack)
        stack.enter_context(patch(
            "services.usage.usage_decorator.acquire_usage_request_lock",
            return_value=lease,
        ))
        stack.enter_context(patch(
            "services.usage.usage_decorator.UsageService.reserve_for_request",
            return_value=reservation,
        ))
        refund = stack.enter_context(patch(
            "services.usage.usage_decorator.UsageService.refund_reservation_quietly",
            return_value=reservation.usage_before,
        ))
        stack.enter_context(patch(
            "services.core.content_service.get_playlist_videos",
            side_effect=collect,
        ))
        response = client.post(
            "/api/playlist-videos",
            json={"url": "https://youtube.com/playlist?list=PLlockloss"},
            headers=_H,
        )

    assert response.status_code == 503
    assert response.get_json()["code"] == "USAGE_LOCK_UNAVAILABLE"
    refund.assert_called_once_with("cost-user", reservation)
    provider.assert_not_called()


def test_playlist_cache_hit_refunds_reserved_usage():
    from routes.utility import _state

    client = _client()
    reservation = _reservation()
    cache_key = "playlist:PLcachedcost:10"
    _state._PLAYLIST_CACHE.clear()
    _state.set_playlist_cache(cache_key, {"videos": [], "total": 0})

    with ExitStack() as stack:
        _base_security_patches(stack)
        stack.enter_context(patch.dict("os.environ", {"REDIS_URL": ""}))
        stack.enter_context(patch(
            "services.usage.usage_decorator.acquire_usage_request_lock",
            return_value=MagicMock(lost=False, released=False),
        ))
        stack.enter_context(patch(
            "services.usage.usage_decorator.UsageService.reserve_for_request",
            return_value=reservation,
        ))
        refund = stack.enter_context(patch(
            "services.usage.usage_decorator.UsageService.refund_reservation",
            return_value=reservation.usage_before,
        ))
        provider = stack.enter_context(patch(
            "services.core.content_service.get_playlist_videos",
        ))
        response = client.post(
            "/api/playlist-videos",
            json={"url": "https://youtube.com/playlist?list=PLcachedcost"},
            headers=_H,
        )

    assert response.status_code == 200
    assert response.get_json()["cached"] is True
    refund.assert_called_once_with("cost-user", reservation)
    provider.assert_not_called()


def test_playlist_fresh_provider_commits_reserved_usage():
    from routes.utility import _state

    client = _client()
    reservation = _reservation()
    _state._PLAYLIST_CACHE.clear()

    def collect(_url, _max_results, *, on_cost_start=None):
        assert callable(on_cost_start)
        on_cost_start()
        return {"videos": [], "total": 0}

    with ExitStack() as stack:
        _base_security_patches(stack)
        stack.enter_context(patch.dict("os.environ", {"REDIS_URL": ""}))
        stack.enter_context(patch(
            "services.usage.usage_decorator.acquire_usage_request_lock",
            return_value=MagicMock(lost=False, released=False),
        ))
        stack.enter_context(patch(
            "services.usage.usage_decorator.UsageService.reserve_for_request",
            return_value=reservation,
        ))
        refund = stack.enter_context(patch(
            "services.usage.usage_decorator.UsageService.refund_reservation",
        ))
        quiet_refund = stack.enter_context(patch(
            "services.usage.usage_decorator.UsageService.refund_reservation_quietly",
        ))
        stack.enter_context(patch(
            "services.core.content_service.get_playlist_videos",
            side_effect=collect,
        ))
        response = client.post(
            "/api/playlist-videos",
            json={"url": "https://youtube.com/playlist?list=PLfreshcost"},
            headers=_H,
        )

    assert response.status_code == 200
    refund.assert_not_called()
    quiet_refund.assert_not_called()
