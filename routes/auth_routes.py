"""
인증 관련 라우트
회원가입, 로그인, 로그아웃, 사용자 정보 조회
"""
import logging
import os
from urllib.parse import urlsplit

from flask import Blueprint, request, jsonify, g, make_response
from utils.responses import api_error, success_response, error_response, sanitize_error_for_client
from src.contexts.identity.interface.auth_decorators import require_auth
from src.shared.infrastructure.supabase_client import get_supabase, is_supabase_enabled
# Phase 5-e: supabase_service 다중 import를 도메인별 facade로 분리.
# 각 facade는 services/data/ 내부이므로 베이스라인에서 자연스럽게 제외.
from services.data.usage_admin_facade import is_admin
from services.data.workspace_service import workspace_service, content_approval_service

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

_REFRESH_COOKIE = 'ie_refresh_token'
_OAUTH_PKCE_COOKIE = 'ie_oauth_pkce'
_COOKIE_AUTH_HEADER = 'cookie'
_TOKEN_AUTH_HEADER = 'token'


class _AuthFlowStorage:
    """요청 간 PKCE verifier만 쿠키로 전달하는 최소 Supabase storage."""

    def __init__(self, code_verifier=None):
        self._values = {}
        self._fallback_code_verifier = code_verifier

    def get_item(self, key):
        if key in self._values:
            return self._values[key]
        if key.endswith('-code-verifier'):
            return self._fallback_code_verifier
        return None

    def set_item(self, key, value):
        self._values[key] = value

    def remove_item(self, key):
        self._values.pop(key, None)

    def code_verifier(self):
        return next(
            (
                value
                for key, value in self._values.items()
                if key.endswith('-code-verifier')
            ),
            self._fallback_code_verifier,
        )


def _cookie_secure():
    return request.is_secure or os.getenv('FLASK_ENV', '').lower() == 'production'


def _set_refresh_cookie(response, refresh_token_value):
    if refresh_token_value:
        response.set_cookie(
            _REFRESH_COOKIE,
            refresh_token_value,
            max_age=30 * 24 * 60 * 60,
            httponly=True,
            secure=_cookie_secure(),
            samesite='Lax',
            path='/api/auth',
        )
    return response


def _clear_auth_cookies(response):
    response.delete_cookie(
        _REFRESH_COOKIE,
        path='/api/auth',
        secure=_cookie_secure(),
        httponly=True,
        samesite='Lax',
    )
    response.delete_cookie(
        _OAUTH_PKCE_COOKIE,
        path='/api/auth/oauth/callback',
        secure=_cookie_secure(),
        httponly=True,
        samesite='Lax',
    )
    return response


def _session_payload(session, *, expose_refresh_token=False):
    payload = {
        'access_token': session.access_token,
        'expires_at': session.expires_at,
    }
    if expose_refresh_token:
        payload['refresh_token'] = session.refresh_token
    return payload


def _uses_cookie_auth_transport():
    return request.headers.get('X-Auth-Transport', '').lower() == _COOKIE_AUTH_HEADER


def _uses_token_auth_transport():
    """Refresh token 본문 노출은 명시적인 비브라우저 클라이언트만 허용."""
    return request.headers.get('X-Auth-Transport', '').lower() == _TOKEN_AUTH_HEADER


def _get_json_data():
    """요청 JSON 데이터 안전하게 파싱"""
    return request.get_json(silent=True) or {}


def _check_supabase():
    """Supabase 활성화 확인, 비활성화시 에러 응답 반환"""
    if not is_supabase_enabled():
        return api_error('Supabase가 설정되지 않았습니다.', 400)
    return None


_success_response = success_response
_error_response = error_response


def _sanitize_service_error(message, fallback_message):
    """서비스 오류를 사용자 노출용 메시지로 정리합니다."""
    sanitized = sanitize_error_for_client(str(message or ''))
    if sanitized.startswith('[서버 오류]'):
        return fallback_message
    return sanitized


def _safe_service_error_response(message, fallback_message, status_code=400):
    return _error_response(_sanitize_service_error(message, fallback_message), status_code)


def _exception_error_response(log_context, error, fallback_message, status_code=500):
    logger.error('%s: %s', log_context, error, exc_info=True)
    return _error_response(fallback_message, status_code)


def _validate_email_password(data):
    """이메일/비밀번호 검증 공통 함수"""
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return None, None, _error_response('이메일과 비밀번호를 입력해주세요.')
    return email, password, None


def _url_origin(value):
    """Return a normalized HTTP(S) origin tuple, or ``None`` when invalid."""
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in {'http', 'https'}:
            return None
        if not parsed.hostname or parsed.username or parsed.password:
            return None
        port = parsed.port
        if port is None:
            port = 443 if parsed.scheme.lower() == 'https' else 80
        return parsed.scheme.lower(), parsed.hostname.lower(), port
    except (TypeError, ValueError):
        return None


def _safe_oauth_redirect(candidate, allowed_origins, default_redirect):
    """Allow paths only when the candidate's exact origin is configured."""
    candidate_origin = _url_origin(candidate)
    allowed = {_url_origin(origin) for origin in allowed_origins}
    if candidate_origin is not None and candidate_origin in allowed:
        return candidate
    return default_redirect


@auth_bp.route('/api/auth/signup', methods=['POST'])
def signup():
    """회원가입"""
    error = _check_supabase()
    if error:
        return error

    email, password, validation_error = _validate_email_password(_get_json_data())
    if validation_error:
        return validation_error

    if len(password) < 6:
        return _error_response('비밀번호는 최소 6자 이상이어야 합니다.')

    try:
        result = get_supabase(fresh=True).auth.sign_up(
            {'email': email, 'password': password}
        )

        if result.user:
            return _success_response({
                'message': '회원가입이 완료되었습니다. 이메일을 확인해주세요.',
                'user': {'id': result.user.id, 'email': result.user.email}
            })
        return _error_response('회원가입에 실패했습니다.')

    except Exception as e:
        error_msg = str(e).lower()
        if 'already registered' in error_msg:
            # 계정 열거 방지: 신규/기존 이메일에 동일한 성공 응답을 사용한다.
            return _success_response({
                'message': '회원가입이 완료되었습니다. 이메일을 확인해주세요.'
            })
        if 'rate limit' in error_msg:
            return _error_response('요청이 너무 많습니다. 잠시 후 다시 시도해주세요.')
        if 'invalid' in error_msg and 'email' in error_msg:
            return _error_response('유효하지 않은 이메일입니다. 실제 이메일 주소(예: gmail.com, naver.com)를 입력해주세요.')
        # 보안: 상세 에러 메시지는 로깅만 하고 일반 메시지 반환
        import logging
        logging.getLogger(__name__).error(f'회원가입 오류: {e}')
        return _error_response('회원가입 처리 중 오류가 발생했습니다.')


@auth_bp.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    """비밀번호 재설정 이메일 발송"""
    error = _check_supabase()
    if error:
        return error

    email = _get_json_data().get('email')
    if not email:
        return _error_response('이메일을 입력해주세요.')

    try:
        get_supabase(fresh=True).auth.reset_password_email(email)
    except Exception as e:
        # 보안: 상세 에러 메시지는 로깅만 (계정 열거 방지 — 성공/실패 동일 응답)
        import logging
        logging.getLogger(__name__).error(f'비밀번호 재설정 오류: {e}')

    # 계정 열거 방지: 등록 여부와 무관하게 동일 메시지 반환
    return _success_response({
        'message': '이메일을 확인해주세요. 등록된 이메일이라면 재설정 링크가 발송됩니다.'
    })


@auth_bp.route('/api/auth/oauth/<provider>', methods=['GET'])
def oauth_login(provider):
    """OAuth 로그인 URL 생성"""
    error = _check_supabase()
    if error:
        return error

    supported_providers = ['google', 'github', 'kakao']
    if provider not in supported_providers:
        return _error_response(f'지원하지 않는 OAuth 제공자: {provider}')

    try:
        # CORS 허용 목록 기반 리디렉트 URL 검증 (Host 헤더 조작 방지)
        allowed_origins = os.getenv(
            'CORS_ORIGINS',
            'http://localhost:3000,http://localhost:5001',
        ).split(',')
        allowed_origins = [
            origin.strip().rstrip('/')
            for origin in allowed_origins
            if _url_origin(origin.strip()) is not None
        ]
        default_redirect = allowed_origins[0] if allowed_origins else 'http://localhost:3000'
        requested_redirect = request.args.get('redirect_url', default_redirect)
        redirect_url = _safe_oauth_redirect(
            requested_redirect,
            allowed_origins,
            default_redirect,
        )

        flow_storage = _AuthFlowStorage()
        result = get_supabase(
            fresh=True,
            auth_storage=flow_storage,
        ).auth.sign_in_with_oauth({
            'provider': provider,
            'options': {
                'redirect_to': redirect_url
            }
        })

        verifier = flow_storage.code_verifier()
        if not verifier:
            logger.error('OAuth PKCE verifier가 생성되지 않았습니다.')
            return _error_response('OAuth 로그인 처리 중 오류가 발생했습니다.')
        response = jsonify({'url': result.url})
        response.set_cookie(
            _OAUTH_PKCE_COOKIE,
            verifier,
            max_age=10 * 60,
            httponly=True,
            secure=_cookie_secure(),
            samesite='Lax',
            path='/api/auth/oauth/callback',
        )
        return response
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f'OAuth 로그인 오류: {e}')
        return _error_response('OAuth 로그인 처리 중 오류가 발생했습니다.')


@auth_bp.route('/api/auth/oauth/callback', methods=['POST'])
def oauth_callback():
    """OAuth 인증 코드를 세션으로 교환"""
    error = _check_supabase()
    if error:
        return error

    code = _get_json_data().get('code')
    if not code:
        return _error_response('인증 코드가 필요합니다.')

    try:
        code_verifier = request.cookies.get(_OAUTH_PKCE_COOKIE)
        if not code_verifier:
            return _error_response('OAuth 인증 세션이 만료되었습니다.', 401)
        flow_storage = _AuthFlowStorage(code_verifier)
        # Supabase에서 코드를 세션으로 교환
        result = get_supabase(
            fresh=True,
            auth_storage=flow_storage,
        ).auth.exchange_code_for_session(
            {'auth_code': code}
        )

        if result.user and result.session:
            response = _success_response({
                'user': {'id': result.user.id, 'email': result.user.email},
                'session': _session_payload(
                    result.session,
                    expose_refresh_token=_uses_token_auth_transport(),
                ),
            })
            _set_refresh_cookie(response, result.session.refresh_token)
            response.delete_cookie(
                _OAUTH_PKCE_COOKIE,
                path='/api/auth/oauth/callback',
                secure=_cookie_secure(),
                httponly=True,
                samesite='Lax',
            )
            return response
        return _error_response('세션 생성에 실패했습니다.', 401)

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f'OAuth 콜백 오류: {e}')
        return _error_response('OAuth 인증 처리 중 오류가 발생했습니다.', 401)


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    """로그인"""
    error = _check_supabase()
    if error:
        return error

    email, password, validation_error = _validate_email_password(_get_json_data())
    if validation_error:
        return validation_error

    try:
        result = get_supabase(fresh=True).auth.sign_in_with_password(
            {'email': email, 'password': password}
        )

        if result.user and result.session:
            response = _success_response({
                'user': {'id': result.user.id, 'email': result.user.email},
                'session': _session_payload(
                    result.session,
                    expose_refresh_token=_uses_token_auth_transport(),
                ),
            })
            return _set_refresh_cookie(response, result.session.refresh_token)
        return _error_response('로그인에 실패했습니다.', 401)

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f'로그인 오류: {e}')
        return _error_response('이메일 또는 비밀번호가 올바르지 않습니다.', 401)


@auth_bp.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    """로그아웃"""
    try:
        # 요청별 클라이언트에는 로컬 세션이 없다. 검증된 현재 JWT를 명시해
        # 해당 사용자의 refresh token만 서버에서 폐기한다. 프로세스 전역
        # auth 세션에 의존하면 동시 요청에서 다른 사용자를 로그아웃시킬 수 있다.
        get_supabase(fresh=True).auth.admin.sign_out(g.access_token, 'global')
        response = _success_response()
    except Exception as e:
        response = _exception_error_response(
            '로그아웃 오류',
            e,
            '[인증 실패] 로그아웃 처리에 실패했습니다.',
            400
        )
    return _clear_auth_cookies(make_response(response))


@auth_bp.route('/api/auth/refresh', methods=['POST'])
def refresh_token():
    """토큰 갱신"""
    error = _check_supabase()
    if error:
        return error

    refresh_token_value = (
        _get_json_data().get('refresh_token')
        or request.cookies.get(_REFRESH_COOKIE)
    )
    if not refresh_token_value:
        return _error_response('Refresh token이 필요합니다.')

    try:
        result = get_supabase(fresh=True).auth.refresh_session(refresh_token_value)

        if result.session and result.user:
            cookie_transport = (
                _uses_cookie_auth_transport()
                or bool(request.cookies.get(_REFRESH_COOKIE))
            )
            response = _success_response({
                'user': {
                    'id': result.user.id,
                    'email': result.user.email,
                },
                'session': _session_payload(
                    result.session,
                    expose_refresh_token=(
                        _uses_token_auth_transport() and not cookie_transport
                    ),
                ),
            })
            return _set_refresh_cookie(response, result.session.refresh_token)
        return _clear_auth_cookies(
            make_response(_error_response('토큰 갱신에 실패했습니다.', 401))
        )

    except Exception as e:
        response = _exception_error_response(
            '토큰 갱신 오류',
            e,
            '[인증 실패] 토큰 갱신에 실패했습니다. 다시 로그인해주세요.',
            401
        )
        return _clear_auth_cookies(make_response(response))


# 관리자 권한 헬퍼 — 단일 정의 (channel_monitoring.py에서 사용).
# is_admin은 namespace 호출이므로 `@patch('routes.auth_routes.is_admin')` 그대로 동작.
def _require_admin():
    """관리자 권한 확인."""
    if not is_admin(g.user_id):
        return _error_response('관리자 권한이 필요합니다.', 403)
    return None


# ============================================================
# 분리된 auth 서브 라우트 — 부수효과 import
# - routes/auth/workspace.py, channel_monitoring.py, misc.py
# ============================================================
from routes import auth as _auth_subroutes  # noqa: E402,F401
