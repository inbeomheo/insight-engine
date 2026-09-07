"""사용량 잠금 Redis 임대 안전성 회귀 테스트."""
from __future__ import annotations

from pathlib import Path
import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from services.usage import usage_lock


class _SteppedEvent:
    """실제 시간을 기다리지 않고 갱신 루프를 한 단계씩 진행한다."""

    def __init__(self, wait_results):
        self._wait_results = iter(wait_results)
        self.wait_timeouts = []
        self.was_set = False

    def wait(self, timeout):
        self.wait_timeouts.append(timeout)
        if self.was_set:
            return True
        return next(self._wait_results)

    def set(self):
        self.was_set = True


class _InlineThread:
    """생성자에서 갱신 루프를 동기적으로 실행하는 테스트 스레드."""

    def __init__(self, *, target, args, **_kwargs):
        self._target = target
        self._args = args
        self._alive = False

    def start(self):
        self._alive = True
        try:
            self._target(*self._args)
        finally:
            self._alive = False

    def is_alive(self):
        return self._alive

    def join(self):
        return None


class _DormantThread:
    """임대의 1회 갱신을 메인 테스트 스레드에서 직접 실행하게 한다."""

    def __init__(self, **_kwargs):
        self._alive = False

    def start(self):
        return None

    def is_alive(self):
        return self._alive

    def join(self):
        return None


class _TokenCheckingLock:
    def __init__(self):
        self.local = SimpleNamespace(token=b'owner-a')
        self.redis_token = b'owner-a'
        self.extend_calls = []
        self.release_calls = 0

    def acquire(self, *, blocking):
        assert blocking is False
        return True

    def extend(self, additional_time, *, replace_ttl):
        self.extend_calls.append((additional_time, replace_ttl))
        return self.local.token == self.redis_token

    def release(self):
        self.release_calls += 1
        token = self.local.token
        self.local.token = None
        if token != self.redis_token:
            raise RuntimeError('다른 토큰 소유자입니다.')
        self.redis_token = None


class _TransientReleaseLock:
    def __init__(self):
        self.local = SimpleNamespace(token=b'owner-token')
        self.redis_token = b'owner-token'
        self.release_calls = 0

    def release(self):
        self.release_calls += 1
        token = self.local.token
        # redis-py는 서버 해제 명령 전에 로컬 토큰을 먼저 비운다.
        self.local.token = None
        if self.release_calls == 1:
            raise OSError('임시 Redis 연결 오류')
        if token != self.redis_token:
            raise AssertionError('재시도에 원래 토큰이 복원되어야 합니다.')
        self.redis_token = None


class _TwoFailureReleaseLock:
    def __init__(self):
        self.local = SimpleNamespace(token=b'owner-token')
        self.redis_token = b'owner-token'
        self.release_calls = 0
        self.finished = threading.Event()

    def release(self):
        self.release_calls += 1
        token = self.local.token
        self.local.token = None
        if self.release_calls <= 2:
            raise OSError('임시 Redis 연결 오류')
        if token != self.redis_token:
            raise AssertionError('백그라운드 재시도에도 원래 토큰이 필요합니다.')
        self.redis_token = None
        self.finished.set()


def test_periodic_renewal_runs_until_release_without_wall_clock_wait():
    """임대 갱신은 설정 주기마다 반복되고 해제되면 멈춘다."""
    stop_event = _SteppedEvent([False, False, True])
    renew = MagicMock(return_value=True)
    release = MagicMock()

    with (
        patch.object(usage_lock.threading, 'Event', return_value=stop_event),
        patch.object(usage_lock.threading, 'Thread', _InlineThread),
    ):
        lease = usage_lock.UsageRequestLease(
            release,
            renew_callback=renew,
            renew_interval_seconds=2.5,
        )
        lease.release()
        lease.release()

    assert renew.call_count == 2
    assert stop_event.wait_timeouts == [2.5, 2.5, 2.5]
    release.assert_called_once_with()
    assert lease.released is True
    assert lease.lost is False


def test_token_change_marks_lease_lost_and_never_releases_new_owner(monkeypatch):
    """갱신이 토큰 소유권 상실을 확인하면 다른 소유자를 해제하지 않는다."""
    redis_lock = _TokenCheckingLock()
    redis_client = MagicMock()
    redis_client.get.return_value = None
    redis_client.lock.return_value = redis_lock
    monkeypatch.setenv('REDIS_URL', 'redis://locks:6379/0')
    monkeypatch.setattr(usage_lock, '_accounting_failure_until', 0.0)

    with (
        patch.object(usage_lock, '_get_redis_client', return_value=redis_client),
        patch.object(usage_lock.threading, 'Thread', _DormantThread),
    ):
        lease = usage_lock.acquire_usage_request_lock('token-owner-test')
        redis_lock.redis_token = b'owner-b'

        assert lease._renew_once() is False
        lease.release()

    assert lease.lost is True
    assert lease.released is False
    assert lease.lost_reason is not None
    assert redis_lock.extend_calls == [
        (usage_lock._REDIS_LOCK_TIMEOUT_SECONDS, True)
    ]
    assert redis_lock.release_calls == 0
    assert redis_lock.redis_token == b'owner-b'


def test_transient_redis_release_failure_restores_token_and_is_retryable():
    """해제 연결 오류를 성공으로 오인하지 않고 같은 토큰으로 재시도한다."""
    redis_lock = _TransientReleaseLock()
    thread_factory = MagicMock(side_effect=lambda **kwargs: _DormantThread(**kwargs))
    with patch.object(usage_lock.threading, 'Thread', thread_factory):
        lease = usage_lock.UsageRequestLease(
            lambda: usage_lock._release_redis_lock(redis_lock),
            renew_callback=MagicMock(return_value=True),
        )

        lease.release()

        assert lease.released is False
        assert lease.lost is False
        assert redis_lock.local.token == b'owner-token'
        assert redis_lock.redis_token == b'owner-token'

        lease.release()
        lease.release()

    assert lease.released is True
    assert redis_lock.release_calls == 2
    assert redis_lock.redis_token is None
    # 해제를 요청한 뒤에 갱신기를 재시작하면 후속 훅이 없을 때
    # 잠금이 영구히 연장될 수 있다.
    assert thread_factory.call_count == 1


def test_two_immediate_release_failures_recover_in_bounded_background_retry():
    """종료 훅 두 번이 실패해도 원 토큰으로 짧게 백그라운드 정리한다."""
    from services.usage.usage_decorator import _release_usage_lease

    redis_lock = _TwoFailureReleaseLock()
    lease = usage_lock.UsageRequestLease(
        lambda: usage_lock._release_redis_lock(redis_lock),
    )

    _release_usage_lease(lease)

    assert redis_lock.finished.wait(timeout=1)
    deadline = time.monotonic() + 1
    while lease.release_retry_active and time.monotonic() < deadline:
        time.sleep(0.01)

    assert lease.released is True
    assert lease.lost is False
    assert lease.release_retry_active is False
    assert redis_lock.release_calls == 3
    assert redis_lock.redis_token is None
    assert not any(
        thread.name == 'usage-lock-release-retry' and thread.is_alive()
        for thread in threading.enumerate()
    )


def test_background_release_never_deletes_replacement_owner_token():
    """TTL 만료 뒤 새 소유자가 생기면 토큰 검증 실패로 정리를 중단한다."""
    from services.usage.usage_decorator import _release_usage_lease

    try:
        from redis.exceptions import LockNotOwnedError
    except ImportError:  # pragma: no cover - redis 선택 의존성 미설치 환경
        class LockNotOwnedError(RuntimeError):
            pass

    class ReplacementOwnerLock(_TwoFailureReleaseLock):
        def release(self):
            self.release_calls += 1
            token = self.local.token
            self.local.token = None
            if self.release_calls <= 2:
                raise OSError('임시 Redis 연결 오류')
            assert token == b'owner-token'
            self.redis_token = b'new-owner-token'
            self.finished.set()
            raise LockNotOwnedError('lock is no longer owned')

    redis_lock = ReplacementOwnerLock()
    lease = usage_lock.UsageRequestLease(
        lambda: usage_lock._release_redis_lock(redis_lock),
    )

    _release_usage_lease(lease)

    assert redis_lock.finished.wait(timeout=1)
    deadline = time.monotonic() + 1
    while lease.release_retry_active and time.monotonic() < deadline:
        time.sleep(0.01)

    assert lease.lost is True
    assert lease.released is False
    assert lease.release_retry_active is False
    assert redis_lock.redis_token == b'new-owner-token'
    assert redis_lock.release_calls == 3


def test_local_fallback_remains_non_blocking_and_release_is_idempotent(monkeypatch):
    """Redis 미설정 환경은 동일 사용자를 직렬화하고 해제 후 재획득한다."""
    monkeypatch.delenv('REDIS_URL', raising=False)
    monkeypatch.setattr(usage_lock, '_accounting_failure_until', 0.0)
    user_id = 'local-fallback-lease-safety-test'
    first = usage_lock.acquire_usage_request_lock(user_id)

    with pytest.raises(usage_lock.UsageLockBusy):
        usage_lock.acquire_usage_request_lock(user_id)

    first.release()
    first.release()
    assert first.released is True

    second = usage_lock.acquire_usage_request_lock(user_id)
    second.release()
    assert second.released is True


def test_compose_redis_policies_do_not_evict_lock_keys():
    """개발/배포 Redis 모두 잠금과 회계 키를 축출하지 않는다."""
    project_root = Path(__file__).resolve().parents[1]

    for compose_name in ('docker-compose.yml', 'docker-compose.deploy.yml'):
        compose = (project_root / compose_name).read_text(encoding='utf-8')
        assert '--maxmemory-policy noeviction' in compose
        assert '--maxmemory-policy allkeys-lru' not in compose
