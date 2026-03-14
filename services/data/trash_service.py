"""휴지통 서비스 (F8-24, Soft Delete)

논리 삭제된 항목을 관리하고, 복구 및 영구 삭제 기능을 제공합니다.
30일 이후 자동 영구 삭제(APScheduler와 연동).
"""
import time
import logging
from threading import Lock
from typing import Optional
from services.data import content_library_service

logger = logging.getLogger(__name__)

RETENTION_DAYS = 30  # 휴지통 보관 기간

_lock = Lock()


def _now() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def move_to_trash(item_id: str, user_id: str = '') -> bool:
    """항목을 휴지통으로 이동합니다 (소프트 삭제)."""
    success = content_library_service.delete_item(item_id, soft=True)
    if success:
        logger.info('휴지통 이동: %s (by %s)', item_id, user_id)
    return success


def restore_from_trash(item_id: str, user_id: str = '') -> Optional[dict]:
    """휴지통에서 항목을 복구합니다."""
    # 내부적으로 is_deleted 플래그를 제거
    from services.data.content_library_service import _items, _lock as _items_lock
    with _items_lock:
        item = _items.get(item_id)
        if not item or not item.get('is_deleted'):
            return None
        item['is_deleted'] = False
        item.pop('deleted_at', None)
        item['updated_at'] = _now()

    logger.info('휴지통 복구: %s (by %s)', item_id, user_id)
    return item


def permanently_delete(item_id: str, user_id: str = '') -> bool:
    """항목을 영구적으로 삭제합니다."""
    success = content_library_service.delete_item(item_id, soft=False)
    if success:
        logger.info('영구 삭제: %s (by %s)', item_id, user_id)
    return success


def list_trash(workspace_id: str = '', user_id: str = '', page: int = 1, per_page: int = 20) -> dict:
    """휴지통 항목 목록을 반환합니다."""
    from services.data.content_library_service import _items, _lock as _items_lock
    with _items_lock:
        items = [i for i in _items.values() if i.get('is_deleted')]

    if workspace_id:
        items = [i for i in items if i.get('workspace_id') == workspace_id]
    if user_id:
        items = [i for i in items if i.get('user_id') == user_id]

    items.sort(key=lambda i: i.get('deleted_at', ''), reverse=True)
    total = len(items)
    start = (page - 1) * per_page
    return {
        'items': items[start:start + per_page],
        'total': total,
        'page': page,
        'per_page': per_page,
    }


def empty_trash(workspace_id: str = '', user_id: str = '') -> int:
    """휴지통을 비웁니다 (영구 삭제). 삭제된 항목 수를 반환합니다."""
    result = list_trash(workspace_id=workspace_id, user_id=user_id, per_page=10000)
    count = 0
    for item in result['items']:
        if permanently_delete(item['id']):
            count += 1
    logger.info('휴지통 비우기: %d 항목 영구 삭제', count)
    return count


def purge_expired(retention_days: int = RETENTION_DAYS) -> int:
    """보관 기간이 지난 항목을 자동 영구 삭제합니다. APScheduler에서 호출."""
    import time as _time
    cutoff_ts = _time.time() - retention_days * 86400

    from services.data.content_library_service import _items, _lock as _items_lock
    with _items_lock:
        expired_ids = []
        for item_id, item in _items.items():
            if not item.get('is_deleted'):
                continue
            deleted_at_str = item.get('deleted_at', '')
            if not deleted_at_str:
                continue
            try:
                deleted_ts = _time.mktime(_time.strptime(deleted_at_str, '%Y-%m-%dT%H:%M:%SZ'))
                if deleted_ts < cutoff_ts:
                    expired_ids.append(item_id)
            except ValueError:
                pass

    count = 0
    for item_id in expired_ids:
        if permanently_delete(item_id, user_id='system'):
            count += 1

    if count:
        logger.info('만료 휴지통 자동 정리: %d 항목', count)
    return count
