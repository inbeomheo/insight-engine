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
import os
import threading
import time
from typing import Dict


# ============================================================
# 클라이언트 트래커 (heartbeat 기반)
# ============================================================
_CLIENT_TRACKER: Dict[str, float] = {}

# 재생목록/채널 조회 결과 캐시 (5분 TTL)
_PLAYLIST_CACHE: Dict[str, dict] = {}
_PLAYLIST_CACHE_TTL: int = 300  # 초


# ============================================================
# 현재 처리 중인 요청 수 (active_requests 카운터)
# ============================================================
_active_requests_counter: int = 0
_active_requests_lock = threading.Lock()


# ============================================================
# 서버 시작 후 총 요청 수 / 에러 응답 수
# Redis가 있으면 워커 공유 카운터, 없으면 프로세스 메모리 폴백
# ============================================================
_total_request_count: int = 0
_total_request_count_lock = threading.Lock()

_total_error_count: int = 0
_total_error_count_lock = threading.Lock()

_REDIS_REQUESTS_KEY = "ie:metrics:requests"
_REDIS_ERRORS_KEY = "ie:metrics:errors"
_redis_client = None
_redis_disabled = False


def _get_redis():
    global _redis_client, _redis_disabled
    if _redis_disabled:
        return None
    if _redis_client is not None:
        return _redis_client
    url = (os.getenv("REDIS_URL") or "").strip()
    if not url or url.startswith("memory"):
        _redis_disabled = True
        return None
    try:
        import redis
        client = redis.Redis.from_url(
            url,
            socket_connect_timeout=0.4,
            socket_timeout=0.4,
            decode_responses=True,
        )
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception:
        _redis_disabled = True
        return None


def _redis_incr(key: str) -> int | None:
    client = _get_redis()
    if client is None:
        return None
    try:
        return int(client.incr(key))
    except Exception:
        return None


def _redis_get(key: str) -> int | None:
    client = _get_redis()
    if client is None:
        return None
    try:
        raw = client.get(key)
        return int(raw or 0)
    except Exception:
        return None


def increment_request_count():
    """총 요청 수 1 증가."""
    global _total_request_count
    redis_value = _redis_incr(_REDIS_REQUESTS_KEY)
    if redis_value is not None:
        return
    with _total_request_count_lock:
        _total_request_count += 1


def increment_error_count():
    """에러 응답 수 1 증가."""
    global _total_error_count
    redis_value = _redis_incr(_REDIS_ERRORS_KEY)
    if redis_value is not None:
        return
    with _total_error_count_lock:
        _total_error_count += 1


def get_request_count() -> int:
    """서버 시작 후 총 요청 수 반환."""
    redis_value = _redis_get(_REDIS_REQUESTS_KEY)
    if redis_value is not None:
        return redis_value
    return _total_request_count


def get_error_count() -> int:
    """서버 시작 후 에러 응답 수 반환."""
    redis_value = _redis_get(_REDIS_ERRORS_KEY)
    if redis_value is not None:
        return redis_value
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


def _cleanup_stale_clients():
    """5분 이상 heartbeat 없는 클라이언트 정리."""
    now = time.time()
    stale = [cid for cid, ts in _CLIENT_TRACKER.items() if now - ts > 300]
    for cid in stale:
        del _CLIENT_TRACKER[cid]
