"""콘텐츠 라이브러리 서비스 (F8-01)

콘텐츠 저장, 검색, 필터, CRUD를 담당하는 인메모리 기반 라이브러리 서비스.
"""
import uuid
import time
import logging
from typing import Optional
from threading import Lock

logger = logging.getLogger(__name__)

_items: dict[str, dict] = {}
_lock = Lock()


def _now() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def create_item(
    title: str,
    content: str,
    style: str = '',
    tags: list[str] | None = None,
    url: str = '',
    user_id: str = '',
    workspace_id: str = '',
    folder_id: str = '',
    meta: dict | None = None,
) -> dict:
    """콘텐츠 라이브러리에 새 항목을 추가합니다."""
    item_id = str(uuid.uuid4())
    item = {
        'id': item_id,
        'title': title,
        'content': content,
        'style': style,
        'tags': tags or [],
        'url': url,
        'user_id': user_id,
        'workspace_id': workspace_id,
        'folder_id': folder_id,
        'meta': meta or {},
        'status': 'draft',       # draft | review | approved | published | archived
        'is_pinned': False,
        'is_locked': False,
        'is_archived': False,
        'is_deleted': False,
        'view_count': 0,
        'created_at': _now(),
        'updated_at': _now(),
    }
    with _lock:
        _items[item_id] = item
    logger.info('라이브러리 항목 생성: %s', item_id)
    return item


def get_item(item_id: str) -> Optional[dict]:
    """항목 ID로 단일 항목을 조회합니다."""
    with _lock:
        item = _items.get(item_id)
    if not item:
        return None
    # 삭제된 항목은 반환하지 않음 (휴지통은 trash_service에서 관리)
    if item.get('is_deleted'):
        return None
    return item


def update_item(item_id: str, **kwargs) -> Optional[dict]:
    """항목의 필드를 업데이트합니다."""
    allowed = {
        'title', 'content', 'style', 'tags', 'url', 'folder_id',
        'meta', 'status', 'is_pinned', 'is_locked', 'is_archived',
    }
    with _lock:
        item = _items.get(item_id)
        if not item or item.get('is_deleted'):
            return None
        for key, val in kwargs.items():
            if key in allowed:
                item[key] = val
        item['updated_at'] = _now()
    return item


def delete_item(item_id: str, soft: bool = True) -> bool:
    """항목을 삭제합니다. soft=True면 논리 삭제(휴지통), False면 완전 삭제."""
    with _lock:
        item = _items.get(item_id)
        if not item:
            return False
        if soft:
            item['is_deleted'] = True
            item['deleted_at'] = _now()
            item['updated_at'] = _now()
        else:
            del _items[item_id]
    return True


def search_items(
    query: str = '',
    style: str = '',
    tags: list[str] | None = None,
    status: str = '',
    workspace_id: str = '',
    user_id: str = '',
    folder_id: str = '',
    is_pinned: Optional[bool] = None,
    is_archived: Optional[bool] = None,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = 'created_at',
    sort_desc: bool = True,
) -> dict:
    """조건에 맞는 라이브러리 항목을 검색·필터합니다."""
    with _lock:
        items = [i for i in _items.values() if not i.get('is_deleted')]

    # 필터 적용
    if workspace_id:
        items = [i for i in items if i.get('workspace_id') == workspace_id]
    if user_id:
        items = [i for i in items if i.get('user_id') == user_id]
    if folder_id:
        items = [i for i in items if i.get('folder_id') == folder_id]
    if style:
        items = [i for i in items if i.get('style') == style]
    if status:
        items = [i for i in items if i.get('status') == status]
    if is_pinned is not None:
        items = [i for i in items if i.get('is_pinned') == is_pinned]
    if is_archived is not None:
        items = [i for i in items if i.get('is_archived') == is_archived]
    if tags:
        items = [i for i in items if all(t in i.get('tags', []) for t in tags)]
    if query:
        q = query.lower()
        items = [
            i for i in items
            if q in i.get('title', '').lower() or q in i.get('content', '').lower()
        ]

    # 정렬
    reverse = sort_desc
    items.sort(key=lambda i: i.get(sort_by, ''), reverse=reverse)

    # 페이지네이션
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page
    return {
        'items': items[start:end],
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': max(1, -(-total // per_page)),
    }


def increment_view(item_id: str) -> None:
    """조회수를 1 증가시킵니다."""
    with _lock:
        item = _items.get(item_id)
        if item:
            item['view_count'] = item.get('view_count', 0) + 1


def get_all_items_raw() -> list[dict]:
    """전체 항목을 반환합니다 (내보내기/마이그레이션 용도)."""
    with _lock:
        return list(_items.values())


def clear_all() -> None:
    """모든 항목을 메모리에서 제거합니다 (테스트 전용)."""
    with _lock:
        _items.clear()
