"""콘텐츠 공유 링크 서비스 (F8-15)

공개 공유 링크 생성, 만료 관리, 접근 카운트 추적.
"""
import uuid
import time
import secrets
import logging
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)

_shares: dict[str, dict] = {}   # token → ShareLink
_lock = Lock()


def _now() -> float:
    return time.time()


def create_share_link(
    item_id: str,
    user_id: str = '',
    expires_in_hours: int = 72,
    password: str = '',
    allow_download: bool = False,
) -> dict:
    """공유 링크를 생성합니다.

    Returns:
        {'token': ..., 'url_path': ..., 'expires_at': ..., ...}
    """
    token = secrets.token_urlsafe(24)
    share = {
        'token': token,
        'item_id': item_id,
        'user_id': user_id,
        'password_hash': _hash_password(password) if password else None,
        'allow_download': allow_download,
        'view_count': 0,
        'created_at': _now(),
        'expires_at': _now() + expires_in_hours * 3600 if expires_in_hours > 0 else None,
        'is_revoked': False,
    }
    with _lock:
        _shares[token] = share
    logger.info('공유 링크 생성: %s → %s', item_id, token[:8])
    return share


def get_share(token: str) -> Optional[dict]:
    """토큰으로 공유 링크를 조회합니다. 만료/취소된 링크는 None."""
    with _lock:
        share = _shares.get(token)
    if not share:
        return None
    if share.get('is_revoked'):
        return None
    if share.get('expires_at') and share['expires_at'] < _now():
        return None
    return share


def verify_and_access(token: str, password: str = '') -> dict:
    """공유 링크에 접근합니다. 비밀번호 검증 후 조회수를 증가시킵니다.

    Returns:
        {'success': True, 'item_id': ...} 또는 {'success': False, 'reason': ...}
    """
    share = get_share(token)
    if not share:
        return {'success': False, 'reason': '링크가 유효하지 않거나 만료되었습니다.'}

    if share.get('password_hash'):
        if not _verify_password(password, share['password_hash']):
            return {'success': False, 'reason': '비밀번호가 올바르지 않습니다.'}

    with _lock:
        _shares[token]['view_count'] = _shares[token].get('view_count', 0) + 1

    return {'success': True, 'item_id': share['item_id'], 'allow_download': share['allow_download']}


def revoke_share(token: str, user_id: str = '') -> bool:
    """공유 링크를 취소합니다."""
    with _lock:
        share = _shares.get(token)
        if not share:
            return False
        if user_id and share.get('user_id') != user_id:
            return False
        share['is_revoked'] = True
    return True


def list_shares(item_id: str = '', user_id: str = '') -> list[dict]:
    """공유 링크 목록을 반환합니다."""
    with _lock:
        shares = list(_shares.values())
    if item_id:
        shares = [s for s in shares if s['item_id'] == item_id]
    if user_id:
        shares = [s for s in shares if s['user_id'] == user_id]
    return shares


def _hash_password(password: str) -> str:
    """간단한 비밀번호 해시 (실 운영 시 bcrypt 등으로 교체 필요)."""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()


def _verify_password(password: str, hashed: str) -> bool:
    return _hash_password(password) == hashed
