"""콘텐츠 댓글 서비스 (F8-16)

콘텐츠 항목에 댓글/답글을 달 수 있는 기능.
멘션(@user), 해결(resolve) 상태 추적을 지원합니다.
"""
import uuid
import time
import re
import logging
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)

_comments: dict[str, dict] = {}
_lock = Lock()


def _now() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def _extract_mentions(text: str) -> list[str]:
    """텍스트에서 @멘션 사용자명을 추출합니다."""
    return re.findall(r'@(\w+)', text)


def add_comment(
    item_id: str,
    user_id: str,
    user_name: str,
    text: str,
    parent_id: str = '',
    selection: str = '',
) -> dict:
    """댓글을 추가합니다.

    Args:
        item_id: 콘텐츠 ID
        user_id: 댓글 작성자 ID
        user_name: 작성자 이름
        text: 댓글 본문
        parent_id: 답글인 경우 부모 댓글 ID
        selection: 선택된 텍스트 범위 (인라인 댓글용)
    """
    comment_id = str(uuid.uuid4())
    comment = {
        'id': comment_id,
        'item_id': item_id,
        'user_id': user_id,
        'user_name': user_name,
        'text': text,
        'parent_id': parent_id,
        'selection': selection,
        'mentions': _extract_mentions(text),
        'is_resolved': False,
        'reactions': {},
        'is_deleted': False,
        'created_at': _now(),
        'updated_at': _now(),
    }
    with _lock:
        _comments[comment_id] = comment
    logger.info('댓글 추가: %s on %s', comment_id[:8], item_id[:8])
    return comment


def get_comment(comment_id: str) -> Optional[dict]:
    """댓글을 조회합니다."""
    with _lock:
        c = _comments.get(comment_id)
    if not c or c.get('is_deleted'):
        return None
    return c


def update_comment(comment_id: str, user_id: str, text: str) -> Optional[dict]:
    """댓글 내용을 수정합니다 (작성자만 가능)."""
    with _lock:
        c = _comments.get(comment_id)
        if not c or c.get('is_deleted'):
            return None
        if c['user_id'] != user_id:
            return None
        c['text'] = text
        c['mentions'] = _extract_mentions(text)
        c['updated_at'] = _now()
    return c


def delete_comment(comment_id: str, user_id: str) -> bool:
    """댓글을 삭제합니다 (소프트 삭제)."""
    with _lock:
        c = _comments.get(comment_id)
        if not c:
            return False
        if c['user_id'] != user_id:
            return False
        c['is_deleted'] = True
        c['updated_at'] = _now()
    return True


def resolve_comment(comment_id: str, user_id: str) -> Optional[dict]:
    """댓글을 해결 처리합니다."""
    with _lock:
        c = _comments.get(comment_id)
        if not c:
            return None
        c['is_resolved'] = True
        c['resolved_by'] = user_id
        c['resolved_at'] = _now()
        c['updated_at'] = _now()
    return c


def add_reaction(comment_id: str, user_id: str, emoji: str) -> Optional[dict]:
    """댓글에 이모지 반응을 추가/토글합니다."""
    with _lock:
        c = _comments.get(comment_id)
        if not c:
            return None
        reactions = c.setdefault('reactions', {})
        users = reactions.setdefault(emoji, [])
        if user_id in users:
            users.remove(user_id)
        else:
            users.append(user_id)
    return c


def list_comments(
    item_id: str,
    include_resolved: bool = True,
    parent_id: str | None = None,
) -> list[dict]:
    """콘텐츠의 댓글 목록을 반환합니다.

    Args:
        include_resolved: False면 미해결 댓글만
        parent_id: None이면 최상위 댓글만, 특정 값이면 해당 댓글의 답글만
    """
    with _lock:
        items = [c for c in _comments.values()
                 if c['item_id'] == item_id and not c.get('is_deleted')]

    if not include_resolved:
        items = [c for c in items if not c.get('is_resolved')]
    if parent_id is not None:
        items = [c for c in items if c.get('parent_id', '') == parent_id]

    items.sort(key=lambda c: c['created_at'])
    return items


def get_mentions(user_id: str) -> list[dict]:
    """사용자가 멘션된 댓글 목록을 반환합니다."""
    with _lock:
        return [
            c for c in _comments.values()
            if user_id in c.get('mentions', []) and not c.get('is_deleted')
        ]
