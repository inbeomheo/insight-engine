"""실시간 협업 편집 서비스 (F5-02)

WebSocket 기반 간단한 문서 동기화 서비스.
Flask-SocketIO 없이 폴링 기반으로 구현 (간소화).
"""
import uuid
import time
import logging
from typing import Optional
from threading import Lock

logger = logging.getLogger(__name__)

# 활성 세션: {session_id: SessionData}
_sessions: dict[str, dict] = {}
_lock = Lock()


def create_session(content_id: str, user_id: str, user_name: str = '') -> dict:
    """협업 세션을 생성하거나 기존 세션에 참가합니다."""
    with _lock:
        # 이미 해당 콘텐츠의 세션이 있는지 확인
        session = None
        for s in _sessions.values():
            if s['content_id'] == content_id:
                session = s
                break

        if not session:
            session_id = str(uuid.uuid4())
            session = {
                'id': session_id,
                'content_id': content_id,
                'participants': {},
                'content': '',
                'version': 0,
                'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            }
            _sessions[session_id] = session

        # 참가자 추가
        session['participants'][user_id] = {
            'user_id': user_id,
            'name': user_name or user_id[:8],
            'cursor_position': 0,
            'last_seen': time.time(),
            'color': _assign_color(len(session['participants'])),
        }

        return {
            'session_id': session['id'],
            'content': session['content'],
            'version': session['version'],
            'participants': list(session['participants'].values()),
        }


def update_content(session_id: str, user_id: str, content: str,
                   cursor_position: int = 0) -> Optional[dict]:
    """콘텐츠를 업데이트합니다."""
    with _lock:
        session = _sessions.get(session_id)
        if not session:
            return None

        session['content'] = content
        session['version'] += 1

        if user_id in session['participants']:
            session['participants'][user_id]['cursor_position'] = cursor_position
            session['participants'][user_id]['last_seen'] = time.time()

        return {
            'version': session['version'],
            'participants': list(session['participants'].values()),
        }


def get_session(session_id: str) -> Optional[dict]:
    """세션 상태를 폴링합니다."""
    session = _sessions.get(session_id)
    if not session:
        return None

    # 30초 이상 비활성 참가자 제거
    now = time.time()
    with _lock:
        inactive = [uid for uid, p in session['participants'].items()
                    if now - p['last_seen'] > 30]
        for uid in inactive:
            del session['participants'][uid]

    return {
        'session_id': session['id'],
        'content': session['content'],
        'version': session['version'],
        'participants': list(session['participants'].values()),
    }


def heartbeat(session_id: str, user_id: str, cursor_position: int = 0) -> bool:
    """참가자 활성 상태를 갱신합니다."""
    session = _sessions.get(session_id)
    if not session or user_id not in session.get('participants', {}):
        return False

    session['participants'][user_id]['last_seen'] = time.time()
    session['participants'][user_id]['cursor_position'] = cursor_position
    return True


def leave_session(session_id: str, user_id: str) -> bool:
    """세션에서 나갑니다."""
    with _lock:
        session = _sessions.get(session_id)
        if not session:
            return False
        session['participants'].pop(user_id, None)
        # 참가자 없으면 세션 삭제
        if not session['participants']:
            del _sessions[session_id]
        return True


# 참가자 색상 팔레트
_COLORS = ['#6366f1', '#ec4899', '#10b981', '#f59e0b', '#8b5cf6',
           '#ef4444', '#06b6d4', '#84cc16']


def _assign_color(index: int) -> str:
    return _COLORS[index % len(_COLORS)]
