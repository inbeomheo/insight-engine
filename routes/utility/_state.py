"""utility 패키지 공용 상태/카운터.

이 모듈은 routes/utility_routes.py와 routes/utility/*.py 사이의
순환 import를 제거하기 위해 추출된 단방향 의존성 모듈이다.

의존 방향:
    utility/_state.py        (공용 상태 — 최하위)
            ↑
    utility/{operations, external, ...}.py  (상태 import)
            ↑
    utility_routes.py        (얇은 진입점 + 패키지 import 부수효과)

테스트 호환성을 위해 utility_routes.py가 이 모듈의 심볼들을 그대로 re-export 하므로
`from routes.utility_routes import _CLIENT_TRACKER` 등 기존 호출은 그대로 동작한다.
"""
import threading
import time
from collections import OrderedDict
from contextlib import contextmanager
from typing import Optional

from services.usage.usage_lock import UsageLockUnavailable


# ============================================================
# 클라이언트 트래커 (heartbeat 기반)
# ============================================================
_CLIENT_TRACKER: "OrderedDict[str, float]" = OrderedDict()
_CLIENT_TRACKER_LOCK = threading.Lock()
_CLIENT_TRACKER_TTL: int = 300
_CLIENT_TRACKER_MAX_ITEMS: int = 2_000

# 재생목록/채널 조회 결과 캐시 (5분 TTL)
_PLAYLIST_CACHE: "OrderedDict[str, dict]" = OrderedDict()
_PLAYLIST_CACHE_LOCK = threading.Lock()
_PLAYLIST_CACHE_TTL: int = 300  # 초
_PLAYLIST_CACHE_MAX_ITEMS: int = 256
_PLAYLIST_FLIGHT_LOCKS: dict[str, tuple[threading.Lock, int]] = {}
_PLAYLIST_FLIGHT_LOCKS_GUARD = threading.Lock()


class PlaylistCacheUnavailable(RuntimeError):
    """A configured cross-process cache/lock cannot be used safely."""


class PlaylistLoadError(ValueError):
    """The upstream provider returned a valid, non-cacheable error."""


# ============================================================
# 현재 처리 중인 요청 수 (active_requests 카운터)
# ============================================================
_active_requests_counter: int = 0
_active_requests_lock = threading.Lock()


# ============================================================
# 서버 시작 후 총 요청 수 / 에러 응답 수
# ============================================================
_total_request_count: int = 0
_total_request_count_lock = threading.Lock()

_total_error_count: int = 0
_total_error_count_lock = threading.Lock()


def increment_request_count():
    """총 요청 수 1 증가."""
    global _total_request_count
    with _total_request_count_lock:
        _total_request_count += 1


def increment_error_count():
    """에러 응답 수 1 증가."""
    global _total_error_count
    with _total_error_count_lock:
        _total_error_count += 1


def get_request_count() -> int:
    """서버 시작 후 총 요청 수 반환."""
    return _total_request_count


def get_error_count() -> int:
    """서버 시작 후 에러 응답 수 반환."""
    return _total_error_count


def get_error_rate() -> float:
    """에러율 반환 (0.0~1.0). 요청이 없으면 0.0."""
    total = _total_request_count
    if total == 0:
        return 0.0
    return round(_total_error_count / total, 4)


def increment_active_requests():
    """활성 요청 수 증가."""
    global _active_requests_counter
    with _active_requests_lock:
        _active_requests_counter += 1


def decrement_active_requests():
    """활성 요청 수 감소."""
    global _active_requests_counter
    with _active_requests_lock:
        _active_requests_counter = max(0, _active_requests_counter - 1)


def get_active_requests() -> int:
    """현재 활성 요청 수 반환."""
    return _active_requests_counter


def _cleanup_stale_clients(now: Optional[float] = None):
    """5분 이상 heartbeat 없는 클라이언트 정리."""
    current = time.time() if now is None else now
    with _CLIENT_TRACKER_LOCK:
        stale = [
            cid
            for cid, ts in _CLIENT_TRACKER.items()
            if current - ts > _CLIENT_TRACKER_TTL
        ]
        for cid in stale:
            _CLIENT_TRACKER.pop(cid, None)


def record_client_heartbeat(client_id: str, now: Optional[float] = None) -> None:
    """Record one client without allowing the public tracker to grow unbounded."""
    current = time.time() if now is None else now
    with _CLIENT_TRACKER_LOCK:
        stale = [
            cid
            for cid, ts in _CLIENT_TRACKER.items()
            if current - ts > _CLIENT_TRACKER_TTL
        ]
        for cid in stale:
            _CLIENT_TRACKER.pop(cid, None)

        _CLIENT_TRACKER[client_id] = current
        _CLIENT_TRACKER.move_to_end(client_id)
        while len(_CLIENT_TRACKER) > _CLIENT_TRACKER_MAX_ITEMS:
            _CLIENT_TRACKER.popitem(last=False)


def get_playlist_cache(cache_key: str, now: Optional[float] = None) -> Optional[dict]:
    """Return a copy of a live cache entry and purge expired entries."""
    current = time.time() if now is None else now
    with _PLAYLIST_CACHE_LOCK:
        expired = [
            key
            for key, value in _PLAYLIST_CACHE.items()
            if current - float(value.get('ts', 0)) >= _PLAYLIST_CACHE_TTL
        ]
        for key in expired:
            _PLAYLIST_CACHE.pop(key, None)

        cached = _PLAYLIST_CACHE.get(cache_key)
        if cached is None:
            return None
        _PLAYLIST_CACHE.move_to_end(cache_key)
        return dict(cached.get('data') or {})


def set_playlist_cache(cache_key: str, data: dict, now: Optional[float] = None) -> None:
    """Store a bounded playlist/channel response cache entry."""
    current = time.time() if now is None else now
    with _PLAYLIST_CACHE_LOCK:
        expired = [
            key
            for key, value in _PLAYLIST_CACHE.items()
            if current - float(value.get('ts', 0)) >= _PLAYLIST_CACHE_TTL
        ]
        for key in expired:
            _PLAYLIST_CACHE.pop(key, None)

        _PLAYLIST_CACHE[cache_key] = {'data': dict(data), 'ts': current}
        _PLAYLIST_CACHE.move_to_end(cache_key)
        while len(_PLAYLIST_CACHE) > _PLAYLIST_CACHE_MAX_ITEMS:
            _PLAYLIST_CACHE.popitem(last=False)


@contextmanager
def _local_playlist_flight(cache_key: str):
    with _PLAYLIST_FLIGHT_LOCKS_GUARD:
        lock, refs = _PLAYLIST_FLIGHT_LOCKS.get(
            cache_key,
            (threading.Lock(), 0),
        )
        _PLAYLIST_FLIGHT_LOCKS[cache_key] = (lock, refs + 1)
    try:
        with lock:
            yield
    finally:
        with _PLAYLIST_FLIGHT_LOCKS_GUARD:
            current = _PLAYLIST_FLIGHT_LOCKS.get(cache_key)
            if current is None or current[0] is not lock:
                return
            if current[1] <= 1:
                _PLAYLIST_FLIGHT_LOCKS.pop(cache_key, None)
            else:
                _PLAYLIST_FLIGHT_LOCKS[cache_key] = (lock, current[1] - 1)


def _redis_playlist_client():
    import os

    redis_url = (os.getenv('REDIS_URL') or '').strip()
    if not redis_url:
        return None
    try:
        import redis
        return redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=3,
        )
    except Exception as exc:
        raise PlaylistCacheUnavailable('재생목록 캐시를 초기화할 수 없습니다.') from exc


def _redis_cache_key(cache_key: str) -> str:
    import hashlib

    digest = hashlib.sha256(cache_key.encode('utf-8')).hexdigest()
    return f'insight-engine:playlist-cache:{digest}'


def get_or_load_playlist_cache(cache_key: str, loader) -> tuple[dict, bool]:
    """Singleflight one external lookup locally and across Redis-backed workers."""
    cached = get_playlist_cache(cache_key)
    if cached is not None:
        return cached, True

    redis_client = _redis_playlist_client()
    if redis_client is None:
        with _local_playlist_flight(cache_key):
            cached = get_playlist_cache(cache_key)
            if cached is not None:
                return cached, True
            result = loader()
            set_playlist_cache(cache_key, result)
            return dict(result), False

    import json

    redis_key = _redis_cache_key(cache_key)
    lock = redis_client.lock(
        redis_key + ':lock',
        timeout=60,
        blocking_timeout=10,
        thread_local=False,
    )
    try:
        raw = redis_client.get(redis_key)
        if raw:
            cached = json.loads(raw)
            if isinstance(cached, dict):
                set_playlist_cache(cache_key, cached)
                return cached, True

        if not lock.acquire(blocking=True):
            raise PlaylistCacheUnavailable('재생목록 조회가 이미 처리 중입니다.')
        try:
            # Another worker may have filled Redis while this one waited.
            raw = redis_client.get(redis_key)
            if raw:
                cached = json.loads(raw)
                if isinstance(cached, dict):
                    set_playlist_cache(cache_key, cached)
                    return cached, True
            result = loader()
            redis_client.setex(
                redis_key,
                _PLAYLIST_CACHE_TTL,
                json.dumps(result, ensure_ascii=False, separators=(',', ':')),
            )
            set_playlist_cache(cache_key, result)
            return dict(result), False
        finally:
            try:
                lock.release()
            except Exception:
                pass
    except PlaylistCacheUnavailable:
        raise
    except PlaylistLoadError:
        raise
    except UsageLockUnavailable:
        raise
    except Exception as exc:
        # A configured Redis dependency failing must not fan out into multiple
        # expensive YouTube calls across gunicorn workers.
        raise PlaylistCacheUnavailable('재생목록 캐시를 사용할 수 없습니다.') from exc
