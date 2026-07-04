"""알림 센터 서비스 (F5-13)

앱 내 알림(생성 완료, 예약 발행, 팀 활동 등)을 관리합니다.
인메모리 저장소 기반.
"""
import uuid
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 인메모리 저장소: {user_id: [notification, ...]}
_notifications: dict[str, list[dict]] = {}

MAX_NOTIFICATIONS_PER_USER = 100

# 알림 타입
NOTIFICATION_TYPES = {
    'generation_complete': '콘텐츠 생성 완료',
    'workspace_invite': '워크스페이스 초대',
    'content_approved': '콘텐츠 승인',
    'content_rejected': '콘텐츠 반려',
    'usage_warning': '사용량 경고',
    'system': '시스템 알림',
}


def create_notification(user_id: str, type: str, title: str,
                        message: str, link: Optional[str] = None,
                        metadata: Optional[dict] = None) -> dict:
    """알림을 생성합니다."""
    if user_id not in _notifications:
        _notifications[user_id] = []

    notification = {
        'id': str(uuid.uuid4()),
        'type': type,
        'title': title,
        'message': message,
        'link': link,
        'metadata': metadata or {},
        'read': False,
        'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }

    _notifications[user_id].insert(0, notification)

    # 최대 수 초과 시 오래된 것 제거
    if len(_notifications[user_id]) > MAX_NOTIFICATIONS_PER_USER:
        _notifications[user_id] = _notifications[user_id][:MAX_NOTIFICATIONS_PER_USER]

    logger.info("알림 생성: user=%s, type=%s", user_id, type)
    return notification


def list_notifications(user_id: str, unread_only: bool = False,
                       limit: int = 20, offset: int = 0) -> dict:
    """사용자의 알림 목록을 반환합니다."""
    items = _notifications.get(user_id, [])
    if unread_only:
        items = [n for n in items if not n['read']]

    total = len(items)
    unread_count = sum(1 for n in _notifications.get(user_id, []) if not n['read'])

    return {
        'notifications': items[offset:offset + limit],
        'total': total,
        'unread_count': unread_count,
    }


def mark_read(user_id: str, notification_id: str) -> bool:
    """알림을 읽음으로 표시합니다."""
    for n in _notifications.get(user_id, []):
        if n['id'] == notification_id:
            n['read'] = True
            return True
    return False


def mark_all_read(user_id: str) -> int:
    """모든 알림을 읽음으로 표시합니다. 변경된 수를 반환."""
    count = 0
    for n in _notifications.get(user_id, []):
        if not n['read']:
            n['read'] = True
            count += 1
    return count


def delete_notification(user_id: str, notification_id: str) -> bool:
    """알림을 삭제합니다."""
    items = _notifications.get(user_id, [])
    for i, n in enumerate(items):
        if n['id'] == notification_id:
            items.pop(i)
            return True
    return False


def get_unread_count(user_id: str) -> int:
    """읽지 않은 알림 수를 반환합니다."""
    return sum(1 for n in _notifications.get(user_id, []) if not n['read'])
