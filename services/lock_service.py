"""콘텐츠 잠금 서비스 (F8-08)

TTL 기반 편집 잠금. 같은 콘텐츠를 여러 사용자가 동시에 편집하지 못하도록 방지.
잠금은 기본 300초(5분) TTL을 가지며, heartbeat로 갱신합니다.
"""
import time
import logging
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_TTL = 300  # 초

_locks: dict[str, dict] = {}   # item_id → lock_info
_mutex = Lock()


def _now() -> float:
    return time.time()


def acquire_lock(item_id: str, user_id: str, user_name: str = '', ttl: int = DEFAULT_TTL) -> dict:
    """콘텐츠 편집 잠금을 획득합니다.

    Returns:
        {'success': True, 'lock': {...}} — 획득 성공
        {'success': False, 'locked_by': ..., 'expires_at': ...} — 이미 잠김
    """
    with _mutex:
        existing = _locks.get(item_id)
        now = _now()

        # TTL 만료된 잠금은 자동 해제
        if existing and existing['expires_at'] < now:
            del _locks[item_id]
            existing = None

        if existing:
            # 본인 잠금이면 갱신 허용
            if existing['user_id'] == user_id:
                existing['expires_at'] = now + ttl
                return {'success': True, 'lock': existing}
            return {
                'success': False,
                'locked_by': existing.get('user_name', existing['user_id']),
                'expires_at': existing['expires_at'],
            }

        lock_info = {
            'item_id': item_id,
            'user_id': user_id,
            'user_name': user_name or user_id[:8],
            'acquired_at': now,
            'expires_at': now + ttl,
        }
        _locks[item_id] = lock_info
        logger.info('잠금 획득: %s by %s', item_id, user_id)
        return {'success': True, 'lock': lock_info}


def release_lock(item_id: str, user_id: str) -> bool:
    """편집 잠금을 해제합니다. 잠금 소유자만 해제 가능."""
    with _mutex:
        existing = _locks.get(item_id)
        if not existing:
            return True   # 이미 없음
        if existing['user_id'] != user_id:
            return False  # 다른 사용자의 잠금은 해제 불가
        del _locks[item_id]
        logger.info('잠금 해제: %s by %s', item_id, user_id)
        return True


def heartbeat(item_id: str, user_id: str, ttl: int = DEFAULT_TTL) -> bool:
    """잠금 TTL을 갱신합니다."""
    with _mutex:
        existing = _locks.get(item_id)
        if not existing or existing['user_id'] != user_id:
            return False
        existing['expires_at'] = _now() + ttl
        return True


def get_lock(item_id: str) -> Optional[dict]:
    """현재 잠금 상태를 반환합니다. 만료된 잠금은 None."""
    with _mutex:
        existing = _locks.get(item_id)
        if not existing:
            return None
        if existing['expires_at'] < _now():
            del _locks[item_id]
            return None
        return existing


def force_release(item_id: str) -> bool:
    """관리자용 강제 잠금 해제."""
    with _mutex:
        if item_id in _locks:
            del _locks[item_id]
            return True
        return False


def cleanup_expired() -> int:
    """만료된 잠금을 정리합니다. 제거된 수를 반환."""
    now = _now()
    with _mutex:
        expired = [k for k, v in _locks.items() if v['expires_at'] < now]
        for k in expired:
            del _locks[k]
    return len(expired)
