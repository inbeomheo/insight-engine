"""Identity & Access 인증 데코레이터.

Issue #17 (소PR B-1) — `services/data/supabase_service.py`의 인증 데코레이터를
도메인 인터페이스 계층으로 이전. 외부 호출자(routes 다수)는 단계적으로 본 모듈을
직접 import하도록 전환되며, 기존 import는 supabase_service의 shim re-export로 호환된다.

제공:
- `require_auth(f)` — Bearer 토큰 검증 + `g.user_id` 주입. 실패 시 401.
- `_extract_bearer_token()` — Authorization 헤더 파싱
- `_validate_token(token)` — Supabase auth.get_user 호출 + 결과 분류

미포함 (소PR B-2 예정):
- `g.auth` (UserAccount Aggregate) 주입 미들웨어 — 별도 PR에서 활성화
"""
from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import g, jsonify, request

from services.core.logging_config import supabase_logger as logger
from src.shared.infrastructure.supabase_client import (
    get_supabase,
    is_supabase_enabled,
)


def _extract_bearer_token() -> str | None:
    """Authorization 헤더에서 Bearer 토큰 추출."""
    auth_header = request.headers.get('Authorization', '')
    return auth_header[7:] if auth_header.startswith('Bearer ') else None


def _validate_token(token: str) -> dict:
    """토큰 검증 + g 객체에 사용자 정보 설정.

    Returns:
        {'valid': bool, 'error': str|None, 'code': str|None}.
        성공 시 g.user_id / g.user_email / g.access_token 채워짐.
    """
    try:
        supabase = get_supabase()
        user = supabase.auth.get_user(token)
        g.user_id = user.user.id
        g.user_email = user.user.email
        g.access_token = token
        logger.info(
            f"토큰 검증 성공: user_id={user.user.id[:8]}..., email={user.user.email}"
        )
        return {'valid': True, 'error': None, 'code': None}
    except Exception as e:
        error_str = str(e).lower()

        if 'expired' in error_str or 'token has expired' in error_str:
            logger.debug("토큰 만료")
            return {
                'valid': False,
                'error': '인증 토큰이 만료되었습니다.',
                'code': 'TOKEN_EXPIRED',
            }

        if 'invalid' in error_str or 'malformed' in error_str:
            logger.debug("무효 토큰")
            return {
                'valid': False,
                'error': '유효하지 않은 토큰입니다.',
                'code': 'TOKEN_INVALID',
            }

        logger.warning(f"토큰 검증 실패: {e}")
        return {
            'valid': False,
            'error': '인증에 실패했습니다.',
            'code': 'AUTH_FAILED',
        }


def require_auth(f: Callable) -> Callable:
    """JWT 토큰 검증 데코레이터.

    Supabase가 비활성화된 개발 환경에서는 `g.user_id = None`으로 진입 허용.
    활성 환경에서는 Bearer 토큰 누락 시 401, 검증 실패 시 401.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_supabase_enabled():
            g.user_id = None
            return f(*args, **kwargs)

        token = _extract_bearer_token()
        if not token:
            return jsonify(
                {'error': '인증이 필요합니다.', 'code': 'AUTH_REQUIRED'}
            ), 401

        result = _validate_token(token)
        if not result['valid']:
            return jsonify(
                {'error': result['error'], 'code': result['code']}
            ), 401

        return f(*args, **kwargs)
    return decorated


__all__ = [
    "require_auth",
    "_extract_bearer_token",
    "_validate_token",
]
