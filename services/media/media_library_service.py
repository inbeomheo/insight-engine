"""미디어 라이브러리 서비스 (F8-10)

이미지, 동영상, 오디오 등 미디어 파일의 메타데이터를 관리합니다.
실제 파일 저장은 Firebase Storage 등 외부 서비스를 사용하며,
이 서비스는 메타데이터 인덱스 역할을 합니다.
"""
import uuid
import time
import logging
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)

ALLOWED_TYPES = {'image', 'video', 'audio', 'document', 'other'}

_media: dict[str, dict] = {}
_lock = Lock()


def _now() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def register_media(
    name: str,
    url: str,
    media_type: str = 'image',
    size_bytes: int = 0,
    mime_type: str = '',
    user_id: str = '',
    workspace_id: str = '',
    tags: list[str] | None = None,
    meta: dict | None = None,
) -> dict:
    """미디어 항목을 등록합니다."""
    if media_type not in ALLOWED_TYPES:
        media_type = 'other'

    media_id = str(uuid.uuid4())
    item = {
        'id': media_id,
        'name': name,
        'url': url,
        'media_type': media_type,
        'size_bytes': size_bytes,
        'mime_type': mime_type,
        'user_id': user_id,
        'workspace_id': workspace_id,
        'tags': tags or [],
        'meta': meta or {},
        'is_deleted': False,
        'created_at': _now(),
        'updated_at': _now(),
    }
    with _lock:
        _media[media_id] = item
    logger.info('미디어 등록: %s (%s)', media_id, name)
    return item


def get_media(media_id: str) -> Optional[dict]:
    """미디어 항목을 조회합니다."""
    with _lock:
        item = _media.get(media_id)
    if not item or item.get('is_deleted'):
        return None
    return item


def list_media(
    workspace_id: str = '',
    user_id: str = '',
    media_type: str = '',
    tags: list[str] | None = None,
    query: str = '',
    page: int = 1,
    per_page: int = 30,
) -> dict:
    """미디어 목록을 조회합니다."""
    with _lock:
        items = [i for i in _media.values() if not i.get('is_deleted')]

    if workspace_id:
        items = [i for i in items if i.get('workspace_id') == workspace_id]
    if user_id:
        items = [i for i in items if i.get('user_id') == user_id]
    if media_type:
        items = [i for i in items if i.get('media_type') == media_type]
    if tags:
        items = [i for i in items if all(t in i.get('tags', []) for t in tags)]
    if query:
        q = query.lower()
        items = [i for i in items if q in i.get('name', '').lower()]

    items.sort(key=lambda i: i.get('created_at', ''), reverse=True)
    total = len(items)
    start = (page - 1) * per_page
    return {
        'items': items[start:start + per_page],
        'total': total,
        'page': page,
        'per_page': per_page,
    }


def delete_media(media_id: str, soft: bool = True) -> bool:
    """미디어 항목을 삭제합니다."""
    with _lock:
        item = _media.get(media_id)
        if not item:
            return False
        if soft:
            item['is_deleted'] = True
            item['updated_at'] = _now()
        else:
            del _media[media_id]
    return True


def update_media(media_id: str, **kwargs) -> Optional[dict]:
    """미디어 항목을 업데이트합니다."""
    allowed = {'name', 'tags', 'meta'}
    with _lock:
        item = _media.get(media_id)
        if not item:
            return None
        for k, v in kwargs.items():
            if k in allowed:
                item[k] = v
        item['updated_at'] = _now()
    return item


def get_storage_stats(workspace_id: str = '') -> dict:
    """스토리지 사용량 통계를 반환합니다."""
    with _lock:
        items = [i for i in _media.values() if not i.get('is_deleted')]
    if workspace_id:
        items = [i for i in items if i.get('workspace_id') == workspace_id]

    total_size = sum(i.get('size_bytes', 0) for i in items)
    by_type: dict[str, int] = {}
    for item in items:
        t = item.get('media_type', 'other')
        by_type[t] = by_type.get(t, 0) + 1

    return {'total_items': len(items), 'total_size_bytes': total_size, 'by_type': by_type}
