"""콘텐츠 만료 자동 관리 서비스 (F8-09)

콘텐츠에 만료 날짜를 설정하고, 만료된 항목을 자동으로 아카이브/삭제합니다.
APScheduler를 통해 1시간마다 만료 체크를 실행합니다.
"""
import time
import logging
from threading import Lock
from typing import Optional
from services import content_library_service

logger = logging.getLogger(__name__)

_expiry_rules: dict[str, dict] = {}  # item_id → {expires_at, action}
_lock = Lock()


def _now() -> float:
    return time.time()


def set_expiry(
    item_id: str,
    expires_at: float,
    action: str = 'archive',
    notify_before_days: int = 3,
) -> dict:
    """콘텐츠에 만료 규칙을 설정합니다.

    Args:
        item_id: 콘텐츠 ID
        expires_at: Unix timestamp (만료 시각)
        action: 'archive' | 'delete' (만료 시 수행할 작업)
        notify_before_days: 만료 N일 전에 알림 플래그 설정
    Returns:
        설정된 만료 규칙 dict
    """
    rule = {
        'item_id': item_id,
        'expires_at': expires_at,
        'action': action,
        'notify_before_days': notify_before_days,
        'notified': False,
        'executed': False,
        'created_at': _now(),
    }
    with _lock:
        _expiry_rules[item_id] = rule
    logger.info('만료 규칙 설정: %s → %s at %s', item_id, action, expires_at)
    return rule


def remove_expiry(item_id: str) -> bool:
    """만료 규칙을 제거합니다."""
    with _lock:
        if item_id in _expiry_rules:
            del _expiry_rules[item_id]
            return True
        return False


def get_expiry(item_id: str) -> Optional[dict]:
    """특정 콘텐츠의 만료 규칙을 반환합니다."""
    with _lock:
        return _expiry_rules.get(item_id)


def list_expiring_soon(within_days: int = 7) -> list[dict]:
    """N일 이내 만료 예정 항목을 반환합니다."""
    cutoff = _now() + within_days * 86400
    with _lock:
        return [
            r for r in _expiry_rules.values()
            if not r['executed'] and r['expires_at'] <= cutoff
        ]


def process_expired() -> dict:
    """만료된 항목을 처리합니다. APScheduler에서 주기적으로 호출합니다.

    Returns:
        {'archived': N, 'deleted': N, 'notified': N}
    """
    now = _now()
    archived = deleted = notified = 0

    with _lock:
        rules = list(_expiry_rules.values())

    for rule in rules:
        if rule['executed']:
            continue

        item_id = rule['item_id']
        expires_at = rule['expires_at']

        # 만료 전 알림 체크
        notify_seconds = rule.get('notify_before_days', 3) * 86400
        if not rule['notified'] and (expires_at - now) <= notify_seconds:
            with _lock:
                _expiry_rules[item_id]['notified'] = True
            notified += 1
            logger.info('만료 알림 플래그 설정: %s', item_id)

        # 만료 처리
        if expires_at <= now:
            action = rule.get('action', 'archive')
            if action == 'delete':
                content_library_service.delete_item(item_id, soft=True)
                deleted += 1
                logger.info('만료 삭제: %s', item_id)
            else:
                content_library_service.update_item(item_id, is_archived=True, status='archived')
                archived += 1
                logger.info('만료 아카이브: %s', item_id)

            with _lock:
                _expiry_rules[item_id]['executed'] = True

    return {'archived': archived, 'deleted': deleted, 'notified': notified}


def get_all_rules() -> list[dict]:
    """모든 만료 규칙을 반환합니다."""
    with _lock:
        return list(_expiry_rules.values())
