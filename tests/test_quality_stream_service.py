"""진행 이벤트, 본문 비노출, 연결 종료 뒤 추가 호출 방지."""
from threading import Event
from unittest.mock import Mock

from flask import Flask
import pytest

from services.core import ai_service, quality_stream_service
from test_content_quality_service import response, EVIDENCE, DRAFT, APPROVED, SOURCE, MODEL


def test_progress_precedes_only_verified_result(monkeypatch):
    provider = Mock(side_effect=[response(x) for x in [EVIDENCE, DRAFT, APPROVED]])
    monkeypatch.setattr(ai_service, '_get_completion', lambda: provider)
    with Flask(__name__).app_context():
        stream = quality_stream_service.stream_verified(SOURCE, '요약', MODEL, {}, {}, 'summary',
                                                        on_cost_start=lambda: None)
        events = []
        while True:
            try:
                events.append(next(stream))
            except StopIteration as stopped:
                assert stopped.value[0] == DRAFT
                assert stopped.value[1]['total_tokens'] == 45
                break
    assert [event['stage'] for event in events] == ['evidence', 'writing', 'reviewing']
    assert all(event['type'] == 'status' and 'content' not in event for event in events)


def test_close_while_provider_pending_prevents_followup_calls(monkeypatch):
    entered, release, finished = Event(), Event(), Event()

    def completion(**kwargs):
        entered.set()
        assert release.wait(2)
        return response(EVIDENCE)

    provider = Mock(side_effect=completion)
    monkeypatch.setattr(ai_service, '_get_completion', lambda: provider)
    original = quality_stream_service.generate_verified

    def wrapped(*args, **kwargs):
        try:
            return original(*args, **kwargs)
        finally:
            finished.set()

    monkeypatch.setattr(quality_stream_service, 'generate_verified', wrapped)
    with Flask(__name__).app_context():
        stream = quality_stream_service.stream_verified(SOURCE, '요약', MODEL, {}, {}, 'summary',
                                                        on_cost_start=lambda: None)
        try:
            assert next(stream)['stage'] == 'evidence'
            assert entered.wait(2)
            stream.close()
        finally:
            release.set()
        assert finished.wait(2)
    assert provider.call_count == 1


def test_worker_failure_propagates(monkeypatch):
    provider = Mock(side_effect=RuntimeError('test failure'))
    monkeypatch.setattr(ai_service, '_get_completion', lambda: provider)
    with Flask(__name__).app_context():
        with pytest.raises(RuntimeError, match='test failure'):
            list(quality_stream_service.stream_verified(SOURCE, '요약', MODEL, {}, {}, 'summary',
                                                       on_cost_start=lambda: None))
