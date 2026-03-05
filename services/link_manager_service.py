"""콘텐츠 링크 관리 서비스 (F8-12)

콘텐츠 간 내부 링크, 외부 URL 참조, 역링크(backlink)를 관리합니다.
"""
import uuid
import time
import logging
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)

_links: dict[str, dict] = {}         # link_id → LinkRecord
_lock = Lock()


def _now() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def add_link(
    source_id: str,
    target: str,
    link_type: str = 'internal',
    label: str = '',
    user_id: str = '',
) -> dict:
    """링크를 추가합니다.

    Args:
        source_id: 링크 출처 콘텐츠 ID
        target: 링크 대상 (콘텐츠 ID 또는 외부 URL)
        link_type: 'internal' | 'external'
        label: 앵커 텍스트 또는 설명
        user_id: 생성 사용자
    """
    link_id = str(uuid.uuid4())
    link = {
        'id': link_id,
        'source_id': source_id,
        'target': target,
        'link_type': link_type,
        'label': label,
        'user_id': user_id,
        'is_broken': False,
        'last_checked': None,
        'created_at': _now(),
    }
    with _lock:
        _links[link_id] = link
    return link


def remove_link(link_id: str) -> bool:
    """링크를 삭제합니다."""
    with _lock:
        if link_id in _links:
            del _links[link_id]
            return True
        return False


def get_links_from(source_id: str) -> list[dict]:
    """특정 콘텐츠에서 나가는 링크 목록을 반환합니다."""
    with _lock:
        return [l for l in _links.values() if l['source_id'] == source_id]


def get_backlinks(target_id: str) -> list[dict]:
    """특정 콘텐츠를 가리키는 역링크(backlink) 목록을 반환합니다."""
    with _lock:
        return [l for l in _links.values() if l['target'] == target_id and l['link_type'] == 'internal']


def mark_broken(link_id: str, broken: bool = True) -> Optional[dict]:
    """링크의 깨짐 상태를 업데이트합니다."""
    with _lock:
        link = _links.get(link_id)
        if not link:
            return None
        link['is_broken'] = broken
        link['last_checked'] = _now()
    return link


def get_broken_links(source_id: str = '') -> list[dict]:
    """깨진 링크 목록을 반환합니다."""
    with _lock:
        broken = [l for l in _links.values() if l.get('is_broken')]
    if source_id:
        broken = [l for l in broken if l['source_id'] == source_id]
    return broken


def get_link(link_id: str) -> Optional[dict]:
    """링크 정보를 조회합니다."""
    with _lock:
        return _links.get(link_id)
