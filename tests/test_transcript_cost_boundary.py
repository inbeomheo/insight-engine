"""유료 자막 폴백의 사용량 확정 경계 회귀 테스트."""
from __future__ import annotations

import threading
import time
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest
from flask import g

from app import create_app
from services.usage.usage_service import UsageReservation
from src.contexts.identity.application.ports import QuotaReservation


_HEADERS = {
    "Origin": "http://localhost:3000",
    "Authorization": "Bearer valid-token",
}


def _usage_reservation() -> UsageReservation:
    before = {
        "usage_count": 3,
        "max_usage": 5,
        "can_use": True,
        "is_admin": False,
    }
    after = {**before, "usage_count": 2}
    quota = QuotaReservation(
        reservation_id="transcript-cost-reservation",
        idempotency_key="client:transcript-cost",
        request_fingerprint="a" * 64,
        owner_token_hash="b" * 64,
        amount=1,
        remaining=2,
        max_usage=5,
        owned=True,
        replayed=False,
    )
    return UsageReservation(quota, before, after, True)


def _authenticate(_token):
    g.user_id = "transcript-cost-user"
    g.access_token = "valid-token"
    return {"valid": True, "error": None, "code": None}


def _patch_authenticated_usage(stack: ExitStack, reservation: UsageReservation):
    lease = MagicMock(lost=False, released=False)

    def release_lease():
        lease.released = True

    lease.release.side_effect = release_lease
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
    stack.enter_context(patch(
        "services.usage.usage_decorator.acquire_usage_request_lock",
        return_value=lease,
    ))
    stack.enter_context(patch(
        "services.usage.usage_decorator.UsageService.reserve_for_request",
        return_value=reservation,
    ))


def test_supadata_commits_immediately_before_http_request():
    from services.transcript.fallbacks.supadata import get_transcript_via_supadata

    events = []
    response = MagicMock(status_code=200)
    response.json.return_value = {"content": "유료 자막"}

    def request(*_args, **_kwargs):
        events.append("request")
        return response

    with patch(
        "services.transcript.fallbacks.supadata.requests.get",
        side_effect=request,
    ):
        result = get_transcript_via_supadata(
            "dQw4w9WgXcQ",
            "secret-key",
            on_cost_start=lambda: events.append("cost"),
        )

    assert result == "유료 자막"
    assert events == ["cost", "request"]


def test_supadata_callback_exception_prevents_request_and_propagates():
    from services.transcript.fallbacks.supadata import get_transcript_via_supadata

    class LeaseLost(RuntimeError):
        pass

    def reject_cost():
        raise LeaseLost("lease lost")

    with patch("services.transcript.fallbacks.supadata.requests.get") as request:
        with pytest.raises(LeaseLost, match="lease lost"):
            get_transcript_via_supadata(
                "dQw4w9WgXcQ",
                "secret-key",
                on_cost_start=reject_cost,
            )

    request.assert_not_called()


def test_supadata_without_key_is_free_and_does_not_commit():
    from services.transcript.fallbacks.supadata import get_transcript_via_supadata

    on_cost_start = MagicMock()
    assert get_transcript_via_supadata(
        "dQw4w9WgXcQ",
        "",
        on_cost_start=on_cost_start,
    ) is None
    on_cost_start.assert_not_called()


def _notebook_service_with_source():
    from services.notebooklm.notebooklm_service import NotebookLmService

    service = NotebookLmService.__new__(NotebookLmService)
    service._state_file_backed = False
    service._state = {
        "notebook_id": "notebook-1",
        "sources": {},
        "artifacts": {},
        "users": {},
    }
    return service


def test_notebooklm_commits_before_source_allocation():
    service = _notebook_service_with_source()
    events = []

    def run_nlm(args, **_kwargs):
        events.append(tuple(args[:2]))
        result = MagicMock(returncode=0, stderr="")
        if args[:2] == ["source", "list"]:
            result.stdout = '[{"id":"source-1","type":"youtube"}]'
        elif args[:2] == ["source", "get"]:
            result.stdout = '{"value":{"content":"NotebookLM 자막"}}'
        else:
            result.stdout = ""
        return result

    service._run_nlm = MagicMock(side_effect=run_nlm)
    result = service.extract_youtube_transcript(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        on_cost_start=lambda: events.append("cost"),
    )

    assert result == "NotebookLM 자막"
    assert events[0] == "cost"
    assert events[1] == ("source", "add")


def test_notebooklm_missing_notebook_is_free():
    service = _notebook_service_with_source()
    service._state["notebook_id"] = None
    on_cost_start = MagicMock()
    service._run_nlm = MagicMock()

    assert service.extract_youtube_transcript(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        on_cost_start=on_cost_start,
    ) is None
    on_cost_start.assert_not_called()
    service._run_nlm.assert_not_called()


def test_notebooklm_callback_exception_is_not_swallowed():
    service = _notebook_service_with_source()
    service._run_nlm = MagicMock()

    class LeaseLost(RuntimeError):
        pass

    def reject_cost():
        raise LeaseLost("lease lost")

    with pytest.raises(LeaseLost, match="lease lost"):
        service.extract_youtube_transcript(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            on_cost_start=reject_cost,
        )

    service._run_nlm.assert_not_called()


def test_parallel_watch_winner_still_commits_running_notebooklm_cost():
    """경쟁에서 진 NLM이 시작한 외부 할당량을 환불하지 않는다."""
    from services.core.content_service import _run_parallel_fallbacks

    release_nlm = threading.Event()
    on_cost_start = MagicMock()

    def nlm_worker(_video_id, callback, cost_decided):
        callback()
        assert cost_decided.is_set()
        release_nlm.wait(timeout=2)
        return None

    with (
        patch(
            "services.core.content_service._try_watch_page_fallback",
            return_value=("watch", "무비용 자막", 0.85, False),
        ),
        patch("services.core.content_service._try_ytdlp_fallback", return_value=None),
        patch(
            "services.core.content_service._try_nlm_fallback",
            side_effect=nlm_worker,
        ),
        patch("services.core.content_service._save_cache"),
    ):
        result = _run_parallel_fallbacks(
            "dQw4w9WgXcQ",
            time.time(),
            on_cost_start=on_cost_start,
        )
        release_nlm.set()

    assert result["source"] == "watch"
    on_cost_start.assert_called_once_with()


def test_parallel_callback_exception_wins_over_free_fallback_result():
    from services.core.content_service import _run_parallel_fallbacks

    class LeaseLost(RuntimeError):
        pass

    def reject_cost():
        raise LeaseLost("lease lost")

    def nlm_worker(_video_id, callback, _cost_decided):
        callback()
        return None

    with (
        patch(
            "services.core.content_service._try_watch_page_fallback",
            return_value=("watch", "무비용 자막", 0.85, False),
        ),
        patch("services.core.content_service._try_ytdlp_fallback", return_value=None),
        patch(
            "services.core.content_service._try_nlm_fallback",
            side_effect=nlm_worker,
        ),
    ):
        with pytest.raises(LeaseLost, match="lease lost"):
            _run_parallel_fallbacks(
                "dQw4w9WgXcQ",
                time.time(),
                on_cost_start=reject_cost,
            )


def test_delayed_losing_notebooklm_is_cancelled_before_late_cost_start():
    """비용 결정이 늦은 NLM은 무비용 성공 반환 후에 시작하지 않는다."""
    from services.core.content_service import _run_parallel_fallbacks

    allow_callback = threading.Event()
    worker_done = threading.Event()
    on_cost_start = MagicMock()

    def delayed_nlm(_video_id, callback, cost_decided):
        try:
            allow_callback.wait(timeout=2)
            callback()
        except RuntimeError:
            # 메인 스레드가 무비용 결과를 택한 후 보낸 내부
            # 취소 신호는 provider 호출 없이 worker만 종료한다.
            return None
        finally:
            cost_decided.set()
            worker_done.set()
        return None

    with (
        patch(
            "services.core.content_service._try_watch_page_fallback",
            return_value=("watch", "무비용 자막", 0.85, False),
        ),
        patch("services.core.content_service._try_ytdlp_fallback", return_value=None),
        patch(
            "services.core.content_service._try_nlm_fallback",
            side_effect=delayed_nlm,
        ),
        patch(
            "services.core.content_service.NLM_COST_DECISION_WAIT_SECONDS",
            0.01,
        ),
        patch("services.core.content_service._save_cache"),
    ):
        result = _run_parallel_fallbacks(
            "dQw4w9WgXcQ",
            time.time(),
            on_cost_start=on_cost_start,
        )
        allow_callback.set()
        assert worker_done.wait(timeout=2)

    assert result["source"] == "watch"
    on_cost_start.assert_not_called()


def test_all_free_transcript_failures_do_not_commit():
    from services.core.content_service import get_transcript

    on_cost_start = MagicMock()
    with (
        patch("services.core.content_service._load_cache", return_value=None),
        patch("services.core.content_service._build_ytt_api", return_value=MagicMock()),
        patch("services.core.content_service._fetch_transcript_with_api", return_value=None),
        patch("services.core.content_service._run_parallel_fallbacks", return_value=None) as parallel,
        patch.dict(
            "os.environ",
            {"WHISPER_ENABLED": "false", "SUPADATA_API_KEY": ""},
            clear=False,
        ),
    ):
        result = get_transcript(
            "dQw4w9WgXcQ",
            on_cost_start=on_cost_start,
        )

    assert "error" in result
    on_cost_start.assert_not_called()
    assert parallel.call_args.kwargs["on_cost_start"] is on_cost_start


def test_paid_transcript_then_short_summary_keeps_reservation():
    """Supadata/NLM 비용 후 짧은 요약 바이패스가 선예약을 환불하지 않는다."""
    client = create_app({"TESTING": True}).test_client()
    reservation = _usage_reservation()

    def paid_short_transcript(_video_id, _language, on_cost_start):
        on_cost_start()
        return ("짧은 자막", [], None, "짧은 자막", "supadata", [])

    with ExitStack() as stack:
        _patch_authenticated_usage(stack, reservation)
        stack.enter_context(patch(
            "routes.blog_routes._handle_cache_hit",
            return_value=None,
        ))
        title_lookup = stack.enter_context(patch(
            "routes.blog_routes.content_service.get_content_title",
            return_value="짧은 영상",
        ))
        stack.enter_context(patch(
            "routes.blog_routes._fetch_youtube_content",
            side_effect=paid_short_transcript,
        ))
        refund = stack.enter_context(patch(
            "services.usage.usage_decorator.UsageService.refund_reservation",
        ))
        quiet_refund = stack.enter_context(patch(
            "services.usage.usage_decorator.UsageService.refund_reservation_quietly",
        ))
        ai_call = stack.enter_context(patch(
            "routes.blog_routes.ai_service.create_content",
        ))

        response = client.post(
            "/generate",
            json={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "style": "summary",
                "model": "chatmock/gpt-5.4-mini",
            },
            headers=_HEADERS,
        )

    assert response.status_code == 200
    assert response.get_json()["bypass_reason"] == "short_content"
    assert callable(title_lookup.call_args.kwargs["on_cost_start"])
    refund.assert_not_called()
    quiet_refund.assert_not_called()
    ai_call.assert_not_called()


def test_all_transcript_failures_before_cost_refund_reservation():
    client = create_app({"TESTING": True}).test_client()
    reservation = _usage_reservation()

    with ExitStack() as stack:
        _patch_authenticated_usage(stack, reservation)
        stack.enter_context(patch(
            "routes.blog_routes._handle_cache_hit",
            return_value=None,
        ))
        stack.enter_context(patch(
            "routes.blog_routes.content_service.get_content_title",
            return_value="자막 없는 영상",
        ))
        fetch = stack.enter_context(patch(
            "routes.blog_routes._fetch_youtube_content",
            return_value=(None, [], "[자막 오류] 자막을 찾을 수 없습니다.", None, None, []),
        ))
        refund = stack.enter_context(patch(
            "services.usage.usage_decorator.UsageService.refund_reservation_quietly",
            return_value=reservation.usage_before,
        ))

        response = client.post(
            "/generate",
            json={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "style": "summary",
                "model": "chatmock/gpt-5.4-mini",
            },
            headers=_HEADERS,
        )

    assert response.status_code == 400
    assert callable(fetch.call_args.args[2])
    refund.assert_called_once_with("transcript-cost-user", reservation)
