"""비용이 큰 사용량 제한 요청을 사용자별로 직렬화하는 잠금.

Redis가 설정된 운영 환경에서는 프로세스 간 분산 잠금을 사용한다. Redis가
설정되지 않은 개발/테스트 환경에서만 프로세스 내부 잠금으로 폴백한다.
두 잠금 모두 비차단 방식이므로 이미 실행 중인 같은 사용자의 요청을 기다리지
않고 즉시 거부할 수 있다.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import os
import threading
import time
from weakref import WeakValueDictionary

from services.core.logging_config import ServiceLogger


logger = ServiceLogger('UsageLock')

# 현재 가장 긴 배치 경로(600초)보다 길고, 프로세스 비정상 종료 시 잠금이
# 영구히 남지 않을 정도의 유한한 임대 시간이다.
_REDIS_LOCK_TIMEOUT_SECONDS = 900
# 요청이 임대 시간보다 길어져도 잠금이 사라지지 않도록 TTL의 1/3마다
# 현재 토큰 소유자인지 확인하며 전체 임대 시간으로 갱신한다.
_REDIS_LOCK_RENEW_INTERVAL_SECONDS = _REDIS_LOCK_TIMEOUT_SECONDS / 3
# 응답 종료 훅의 즉시 재시도가 모두 실패해도 Redis의 원래 토큰을 보존한 채
# 짧게만 정리한다. 각 Redis 명령의 1초 소켓 타임아웃까지 포함해도 유한하다.
_RELEASE_RETRY_TIMEOUT_SECONDS = 5.0
_RELEASE_RETRY_INTERVAL_SECONDS = 0.1
_RELEASE_RETRY_MAX_ATTEMPTS = 8
_RELEASE_RETRY_MAX_WORKERS = 8
_ACCOUNTING_FAILURE_TTL_SECONDS = 30
_ACCOUNTING_FAILURE_KEY = 'insight-engine:usage-accounting-unavailable'

_process_locks: WeakValueDictionary[str, threading.Lock] = (
    WeakValueDictionary()
)
_process_locks_guard = threading.Lock()
_redis_clients: dict[str, object] = {}
_redis_clients_guard = threading.Lock()
_accounting_failure_guard = threading.Lock()
_accounting_failure_until = 0.0
_release_retry_slots = threading.BoundedSemaphore(_RELEASE_RETRY_MAX_WORKERS)


class UsageLockBusy(RuntimeError):
    """같은 사용자의 비용 요청이 이미 실행 중임."""


class UsageLockUnavailable(RuntimeError):
    """설정된 Redis 잠금을 안전하게 획득할 수 없음."""


class UsageRequestLease:
    """획득한 사용량 잠금을 관리하는 명시적 임대 객체.

    스트리밍 응답은 라우트에서 잠금을 획득하고 응답 generator가 끝날 때
    해제해야 하므로 context manager보다 수명이 길다. ``release``는 응답 종료
    훅과 generator ``finally`` 양쪽에서 호출해도 안전하도록 멱등이다.

    Redis 임대는 ``renew_callback``을 통해 주기적으로 갱신한다. 갱신이
    실패하면 더 이상 독점적 소유를 보장할 수 없으므로 ``lost``로 명시적으로
    표시한다. 해제 실패는 성공으로 오인하지 않고, 후속 종료 훅이 다시
    시도할 수 있는 상태로 남긴다. 해제가 요청된 뒤에는 갱신을
    재시작하지 않아 후속 훅이 없어도 Redis TTL이 마지막 복구수단으로 남는다.
    """

    def __init__(
        self,
        release_callback,
        *,
        renew_callback=None,
        renew_interval_seconds: float | None = None,
    ):
        self._release_callback = release_callback
        self._renew_callback = renew_callback
        self._renew_interval_seconds = (
            renew_interval_seconds
            if renew_interval_seconds is not None
            else _REDIS_LOCK_RENEW_INTERVAL_SECONDS
        )
        self._released = False
        self._lost = False
        self._lost_reason: Exception | None = None
        self._release_guard = threading.Lock()
        self._state_guard = threading.Lock()
        self._renew_stop: threading.Event | None = None
        self._renew_thread: threading.Thread | None = None
        self._release_retry_stop: threading.Event | None = None
        self._release_retry_thread: threading.Thread | None = None

        if renew_callback is not None:
            self._start_renewal()

    @property
    def released(self) -> bool:
        """해제 콜백이 성공해 임대가 정상적으로 종료되었는지 반환한다."""
        with self._state_guard:
            return self._released

    @property
    def lost(self) -> bool:
        """갱신/토큰 검증 실패로 임대 소유를 상실했는지 반환한다."""
        with self._state_guard:
            return self._lost

    @property
    def lost_reason(self) -> Exception | None:
        """임대 소유권 상실을 확정한 예외를 반환한다."""
        with self._state_guard:
            return self._lost_reason

    @property
    def release_retry_active(self) -> bool:
        """제한시간 백그라운드 해제 재시도가 현재 실행 중인지 반환한다."""
        with self._state_guard:
            thread = self._release_retry_thread
            return thread is not None and thread.is_alive()

    def _start_renewal(self) -> None:
        if self._renew_callback is None:
            return

        with self._state_guard:
            if self._released or self._lost:
                return
            if self._renew_thread is not None and self._renew_thread.is_alive():
                return

            stop_event = threading.Event()
            renew_thread = threading.Thread(
                target=self._renew_loop,
                args=(stop_event,),
                name='usage-lock-renewal',
                daemon=True,
            )
            self._renew_stop = stop_event
            self._renew_thread = renew_thread

        try:
            renew_thread.start()
        except Exception:
            with self._state_guard:
                if self._renew_stop is stop_event:
                    self._renew_stop = None
                if self._renew_thread is renew_thread:
                    self._renew_thread = None
            raise

    def _stop_renewal(self) -> None:
        with self._state_guard:
            stop_event = self._renew_stop
            renew_thread = self._renew_thread

        if stop_event is not None:
            stop_event.set()
        if (
            renew_thread is not None
            and renew_thread is not threading.current_thread()
        ):
            # 연장 명령과 해제 명령이 동시에 같은 토큰을 조작하지
            # 않도록 현재 갱신을 끝까지 기다린다. Redis 소켓 타임아웃은 1초다.
            renew_thread.join()

        with self._state_guard:
            if self._renew_stop is stop_event:
                self._renew_stop = None
            if self._renew_thread is renew_thread:
                self._renew_thread = None

    def _mark_lost(self, reason: Exception) -> None:
        with self._state_guard:
            if self._released or self._lost:
                return
            self._lost = True
            self._lost_reason = reason
            stop_event = self._renew_stop
            release_retry_stop = self._release_retry_stop

        if stop_event is not None:
            stop_event.set()
        if release_retry_stop is not None:
            release_retry_stop.set()
        logger.error(f'사용량 잠금 임대 소유권 상실: {reason}')

    def _renew_once(self) -> bool:
        """토큰 검증형 TTL 갱신을 1회 수행한다."""
        try:
            renewed = self._renew_callback()
        except Exception as exc:
            self._mark_lost(exc)
            return False

        if not renewed:
            self._mark_lost(
                RuntimeError('잠금 갱신이 토큰 소유권을 확인하지 못했습니다.')
            )
            return False
        return True

    def _renew_loop(self, stop_event: threading.Event) -> None:
        while not stop_event.wait(self._renew_interval_seconds):
            with self._state_guard:
                if self._released or self._lost or self._renew_stop is not stop_event:
                    return
            if not self._renew_once():
                return

    def schedule_release_retry(
        self,
        *,
        timeout_seconds: float = _RELEASE_RETRY_TIMEOUT_SECONDS,
        retry_interval_seconds: float = _RELEASE_RETRY_INTERVAL_SECONDS,
        max_attempts: int = _RELEASE_RETRY_MAX_ATTEMPTS,
    ) -> bool:
        """한 번만 실행되는 유한한 백그라운드 해제 재시도를 예약한다.

        실제 Redis 삭제는 계속 redis-py의 토큰 비교 Lua 스크립트를 거친다.
        따라서 임대가 만료돼 다른 소유자가 같은 키를 획득하면
        ``LockNotOwnedError``로 종료되고 새 소유자의 키를 지우지 않는다.
        """
        if timeout_seconds <= 0 or retry_interval_seconds <= 0:
            raise ValueError('해제 재시도 제한시간과 간격은 양수여야 합니다.')
        if not isinstance(max_attempts, int) or isinstance(max_attempts, bool):
            raise ValueError('해제 재시도 횟수는 양의 정수여야 합니다.')
        if max_attempts <= 0:
            raise ValueError('해제 재시도 횟수는 양의 정수여야 합니다.')

        with self._state_guard:
            if self._released or self._lost:
                return False
            current = self._release_retry_thread
            if current is not None and current.is_alive():
                return False

            # Redis 장애 중 서로 다른 사용자 요청이 동시에 끝나도 정리용
            # daemon 스레드가 무제한 늘어나지 않는다. 슬롯이 없으면 유한 TTL이
            # 대신 정리하며 현재 응답은 지연시키지 않는다.
            if not _release_retry_slots.acquire(blocking=False):
                logger.error(
                    '사용량 잠금 백그라운드 해제 슬롯이 가득 찼습니다. '
                    'Redis TTL 만료를 기다립니다.'
                )
                return False

            stop_event = threading.Event()
            retry_thread = threading.Thread(
                target=self._release_retry_loop,
                args=(
                    stop_event,
                    float(timeout_seconds),
                    float(retry_interval_seconds),
                    max_attempts,
                ),
                name='usage-lock-release-retry',
                daemon=True,
            )
            self._release_retry_stop = stop_event
            self._release_retry_thread = retry_thread

        try:
            retry_thread.start()
        except Exception:
            _release_retry_slots.release()
            with self._state_guard:
                if self._release_retry_stop is stop_event:
                    self._release_retry_stop = None
                if self._release_retry_thread is retry_thread:
                    self._release_retry_thread = None
            raise
        return True

    def _release_retry_loop(
        self,
        stop_event: threading.Event,
        timeout_seconds: float,
        retry_interval_seconds: float,
        max_attempts: int,
    ) -> None:
        deadline = time.monotonic() + timeout_seconds
        attempts = 0
        try:
            while attempts < max_attempts and time.monotonic() < deadline:
                self.release()
                attempts += 1
                with self._state_guard:
                    if self._released or self._lost:
                        return
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return
                if stop_event.wait(min(retry_interval_seconds, remaining)):
                    return
            logger.error(
                '사용량 잠금 백그라운드 해제가 제한시간 내 완료되지 않았습니다. '
                'Redis TTL 만료를 기다립니다.'
            )
        finally:
            with self._state_guard:
                if self._release_retry_stop is stop_event:
                    self._release_retry_stop = None
                if self._release_retry_thread is threading.current_thread():
                    self._release_retry_thread = None
            _release_retry_slots.release()

    def release(self) -> None:
        with self._release_guard:
            with self._state_guard:
                if self._released:
                    return
                already_lost = self._lost

            if already_lost:
                self._stop_renewal()
                return

            self._stop_renewal()
            with self._state_guard:
                if self._lost:
                    return

            try:
                self._release_callback()
            except Exception as exc:
                # 소유권 오류는 재시도로 복구할 수 없다. 연결 오류는 성공으로
                # 오인하지 않고 다른 종료 훅이 다시 시도할 수 있게 남긴다.
                if _is_redis_lock_not_owned_error(exc):
                    self._mark_lost(exc)
                else:
                    logger.error(f'사용량 잠금 해제 실패(재시도 가능): {exc}')
                return

            with self._state_guard:
                self._released = True
                release_retry_stop = self._release_retry_stop
            if release_retry_stop is not None:
                release_retry_stop.set()


def _is_redis_lock_not_owned_error(exc: Exception) -> bool:
    """redis 선택 설치를 깨지 않으며 토큰 소유권 예외를 구분한다."""
    try:
        from redis.exceptions import LockNotOwnedError
    except ImportError:
        return type(exc).__name__ == 'LockNotOwnedError'
    return isinstance(exc, LockNotOwnedError)


def _redis_lock_token(lock):
    """thread_local=False Redis Lock에 저장된 현재 토큰을 반환한다."""
    local = getattr(lock, 'local', None)
    if local is None:
        return None
    return getattr(local, 'token', None)


def _release_redis_lock(lock) -> None:
    """토큰 검증형 Redis 해제를 수행하고 일시 오류 시 재시도를 보존한다.

    redis-py ``Lock.release``는 Redis 명령을 보내기 전 로컬 토큰을
    비운다. 응답을 받기 전 연결이 끊기면 같은 임대 객체로는 다시
    해제할 수 없으므로, 해제 실패 시에만 기존 토큰을 복원한다. 재시도도
    Redis Lua 스크립트의 토큰 비교를 거치므로 다른 소유자의 키를 삭제할 수 없다.
    """
    local = getattr(lock, 'local', None)
    token = _redis_lock_token(lock)
    try:
        lock.release()
    except Exception:
        if local is not None and token is not None:
            try:
                if getattr(local, 'token', None) is None:
                    local.token = token
            except Exception:
                # 소유권은 재시도 시 Redis에서 다시 검증된다. 비표준
                # Lock 구현의 local 속성이 쓰기 불가라면 원래 예외를 유지한다.
                pass
        raise


def _get_redis_url() -> str:
    """프레임워크 컨텍스트에 의존하지 않고 환경의 Redis URL을 반환한다."""
    return os.getenv('REDIS_URL', '').strip()


def _get_redis_client(redis_url: str):
    """URL별 Redis 연결 풀을 재사용한다(실제 연결은 첫 명령에서 확인)."""
    with _redis_clients_guard:
        client = _redis_clients.get(redis_url)
        if client is not None:
            return client

        try:
            from redis import Redis
        except ImportError as exc:
            raise UsageLockUnavailable('Redis 클라이언트를 불러올 수 없습니다.') from exc

        client = Redis.from_url(
            redis_url,
            socket_connect_timeout=1,
            socket_timeout=1,
            health_check_interval=30,
        )
        _redis_clients[redis_url] = client
        return client


def _lock_name(user_id: str) -> str:
    """Redis 키에 사용자 식별자를 그대로 노출하지 않는다."""
    digest = hashlib.sha256(user_id.encode('utf-8')).hexdigest()
    return f'insight-engine:usage-request:{digest}'


def _get_process_lock(user_id: str) -> threading.Lock:
    """사용자별 프로세스 잠금을 경쟁 없이 생성한다."""
    with _process_locks_guard:
        lock = _process_locks.get(user_id)
        if lock is None:
            lock = threading.Lock()
            _process_locks[user_id] = lock
        return lock


def _process_accounting_failure_active() -> bool:
    with _accounting_failure_guard:
        return time.monotonic() < _accounting_failure_until


def mark_usage_accounting_unavailable() -> None:
    """차감 장애를 짧게 회로 차단해 후속 비용 요청이 반복 실행되지 않게 한다."""
    global _accounting_failure_until
    with _accounting_failure_guard:
        _accounting_failure_until = max(
            _accounting_failure_until,
            time.monotonic() + _ACCOUNTING_FAILURE_TTL_SECONDS,
        )

    redis_url = _get_redis_url()
    if not redis_url:
        return
    try:
        _get_redis_client(redis_url).set(
            _ACCOUNTING_FAILURE_KEY,
            '1',
            ex=_ACCOUNTING_FAILURE_TTL_SECONDS,
        )
    except Exception as exc:
        # 현재 요청은 이미 503으로 실패한다. 로컬 회로 차단은 유지하고 Redis
        # 마커 기록 실패만 로그로 남긴다.
        logger.error(f'사용량 차감 장애 마커 기록 실패: {exc}')


def acquire_usage_request_lock(user_id: str) -> UsageRequestLease:
    """사용자별 잠금을 비차단 획득하고 명시적 임대를 반환한다.

    Redis가 명시적으로 설정된 경우에는 어떤 연결/명령 오류에도 로컬 잠금으로
    폴백하지 않는다. 여러 프로세스가 동시에 비용을 발생시키는 상황을 막기 위해
    호출자가 503으로 fail-closed 처리할 수 있도록 예외를 올린다.
    """
    if _process_accounting_failure_active():
        raise UsageLockUnavailable('사용량 차감 회로가 일시적으로 차단되었습니다.')

    redis_url = _get_redis_url()
    if redis_url:
        try:
            client = _get_redis_client(redis_url)
            if client.get(_ACCOUNTING_FAILURE_KEY):
                raise UsageLockUnavailable(
                    '사용량 차감 회로가 일시적으로 차단되었습니다.'
                )
            lock = client.lock(
                _lock_name(user_id),
                timeout=_REDIS_LOCK_TIMEOUT_SECONDS,
                blocking=False,
                # 스트리밍 라우트는 요청 스레드에서 획득하고 응답 generator가
                # 다른 스레드에서 닫힐 수 있으므로 토큰을 thread-local에 두지 않는다.
                thread_local=False,
            )
            acquired = lock.acquire(blocking=False)
        except UsageLockUnavailable:
            raise
        except Exception as exc:
            raise UsageLockUnavailable('Redis 잠금 연결에 실패했습니다.') from exc

        if not acquired:
            raise UsageLockBusy
        try:
            return UsageRequestLease(
                lambda: _release_redis_lock(lock),
                renew_callback=lambda: lock.extend(
                    _REDIS_LOCK_TIMEOUT_SECONDS,
                    replace_ttl=True,
                ),
                renew_interval_seconds=_REDIS_LOCK_RENEW_INTERVAL_SECONDS,
            )
        except Exception as exc:
            try:
                _release_redis_lock(lock)
            except Exception as release_exc:
                logger.error(
                    f'갱신기 시작 실패 후 Redis 잠금 해제 실패: {release_exc}'
                )
            raise UsageLockUnavailable(
                'Redis 잠금 갱신기를 시작할 수 없습니다.'
            ) from exc

    lock = _get_process_lock(user_id)
    if not lock.acquire(blocking=False):
        raise UsageLockBusy
    return UsageRequestLease(lock.release)


@contextmanager
def usage_request_lock(user_id: str):
    """사용자별 잠금을 비차단 획득하고 context 종료 시 해제한다."""
    lease = acquire_usage_request_lock(user_id)

    try:
        yield
    finally:
        lease.release()


__all__ = [
    'UsageLockBusy',
    'UsageLockUnavailable',
    'UsageRequestLease',
    'acquire_usage_request_lock',
    'mark_usage_accounting_unavailable',
    'usage_request_lock',
]
