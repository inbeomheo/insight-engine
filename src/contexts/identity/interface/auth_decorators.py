"""Identity & Access 인증 데코레이터.

Issue #17 (소PR B-1) — `services/data/supabase_service.py`의 인증 데코레이터를
도메인 인터페이스 계층으로 이전. 외부 호출자(routes 다수)는 단계적으로 본 모듈을
직접 import하도록 전환되며, 기존 import는 supabase_service의 shim re-export로 호환된다.

Issue #17 (소PR B-2) — `g.auth` (UserAccount Aggregate) 인터페이스 추가.
모든 요청에 `g.auth` 슬롯이 보장되며, `require_auth` 검증 성공 시 UserAccount로 채워진다.
비인증/검증 실패 요청은 `g.auth = None` 유지.

제공:
- `require_auth(f)` — Bearer 토큰 검증 + `g.user_id`/`g.auth` 주입. 실패 시 401.
- `inject_auth_context()` — Flask `before_request` 미들웨어. `g.auth = None` 초기화.
- `_extract_bearer_token()` — Authorization 헤더 파싱
- `_validate_token(token)` — Supabase auth.get_user 호출 + 결과 분류
- `_populate_auth_account()` — `g.user_id` → UserAccount Aggregate 조회 후 `g.auth` 채움
"""
from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import g, jsonify, request

from services.core.logging_config import supabase_logger as logger
from src.contexts.identity.interface.auth_policy import (
    is_auth_bypass_allowed,
    is_production_env,
    trusted_proxy_user,
)
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


def _populate_auth_account() -> None:
    """`g.user_id` → UserAccount Aggregate 조회 후 `g.auth` 채움.

    Repository 조회 실패는 graceful degradation (경고 로그 + `g.auth = None` 유지).
    조회는 Supabase 왕복 5~6회를 유발하므로 요청마다 eager 실행하지 않고,
    `get_auth_account()`가 실제 필요 시점에 호출한다.
    """
    user_id = g.get('user_id')
    if not user_id:
        return
    try:
        from src.contexts.identity.domain.value_objects import AccountId
        from src.contexts.identity.infrastructure.supabase_account_repository import (
            SupabaseAccountRepository,
        )
        repo = SupabaseAccountRepository()
        g.auth = repo.find_by_id(AccountId(user_id))
    except Exception as e:
        logger.warning(
            f"UserAccount Aggregate 조회 실패 (user_id={user_id[:8]}...): {e}"
        )


def get_auth_account():
    """UserAccount Aggregate를 지연 조회해 반환한다 (요청 스코프 메모이즈).

    `require_auth`가 매 요청 eager 조회하던 것을 실제 사용 시점으로 미룬
    접근자. 첫 호출 시 `_populate_auth_account()`로 채우고 이후엔 g.auth 재사용.
    """
    if g.get('auth') is None and g.get('user_id'):
        _populate_auth_account()
    return g.get('auth')


def inject_auth_context() -> None:
    """Flask `before_request` 미들웨어 — `g.auth` 슬롯 초기화.

    모든 요청에 `g.auth` attribute가 보장됨 (`None` 또는 UserAccount).
    실제 채움은 `require_auth`가 인증 통과 후 `_populate_auth_account()`로 수행.
    """
    g.auth = None


def require_auth(f: Callable) -> Callable:
    """JWT 토큰 검증 데코레이터.

    Supabase가 없으면 production은 503으로 닫는다(fail-closed).
    개발/테스트 우회는 AUTH_BYPASS=true일 때만 허용하며 production에서는 무시한다.
    활성 환경에서는 Bearer 토큰 누락/검증 실패 시 401.
    UserAccount Aggregate가 필요한 라우트는 `get_auth_account()`로 지연 조회.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        proxy_user = trusted_proxy_user(request.headers)
        if proxy_user:
            g.user_id = proxy_user
            g.user_email = None
            g.access_token = None
            g.auth_via = 'trusted_proxy'
            return f(*args, **kwargs)

        if not is_supabase_enabled():
            if is_production_env():
                return jsonify({
                    'error': '인증 서비스를 사용할 수 없습니다.',
                    'code': 'AUTH_UNAVAILABLE',
                }), 503
            if not is_auth_bypass_allowed():
                return jsonify({
                    'error': '인증이 필요합니다.',
                    'code': 'AUTH_REQUIRED',
                }), 401
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

        # g.auth는 get_auth_account()로 지연 조회 (eager 조회 시 요청당
        # Supabase 왕복 5~6회가 낭비됐음 — 현재 g.auth 소비 라우트 없음)
        return f(*args, **kwargs)
    return decorated


__all__ = [
    "require_auth",
    "inject_auth_context",
    "get_auth_account",
    "_extract_bearer_token",
    "_validate_token",
    "_populate_auth_account",
]
