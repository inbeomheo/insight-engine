"""콘텐츠 아카이브 서비스 (F8-07)

보관 처리, 복구, 아카이브 목록 조회 기능 제공.
content_library_service와 연동하여 status를 관리합니다.
"""
import time
import logging
from threading import Lock
from typing import Optional
from services import content_library_service

logger = logging.getLogger(__name__)

_archive_log: list[dict] = []
_lock = Lock()


def _now() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def archive_item(item_id: str, user_id: str = '', reason: str = '') -> Optional[dict]:
    """콘텐츠를 아카이브 상태로 전환합니다."""
    item = content_library_service.update_item(
        item_id,
        is_archived=True,
        status='archived',
    )
    if not item:
        return None

    with _lock:
        _archive_log.append({
            'item_id': item_id,
            'action': 'archive',
            'user_id': user_id,
            'reason': reason,
            'at': _now(),
        })

    logger.info('아카이브 처리: %s (by %s)', item_id, user_id)
    return item


def restore_item(item_id: str, user_id: str = '') -> Optional[dict]:
    """아카이브된 콘텐츠를 draft 상태로 복구합니다."""
    item = content_library_service.update_item(
        item_id,
        is_archived=False,
        status='draft',
    )
    if not item:
        return None

    with _lock:
        _archive_log.append({
            'item_id': item_id,
            'action': 'restore',
            'user_id': user_id,
            'at': _now(),
        })

    logger.info('아카이브 복구: %s (by %s)', item_id, user_id)
    return item


def list_archived(workspace_id: str = '', user_id: str = '', page: int = 1, per_page: int = 20) -> dict:
    """아카이브된 항목 목록을 반환합니다."""
    return content_library_service.search_items(
        is_archived=True,
        workspace_id=workspace_id,
        user_id=user_id,
        page=page,
        per_page=per_page,
    )


def get_archive_log(item_id: str = '') -> list[dict]:
    """아카이브 작업 로그를 반환합니다."""
    with _lock:
        if item_id:
            return [e for e in _archive_log if e['item_id'] == item_id]
        return list(_archive_log)
