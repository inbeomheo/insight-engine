"""
인증 관련 라우트
회원가입, 로그인, 로그아웃, 사용자 정보 조회
"""
import logging
import os

from flask import Blueprint, request, jsonify, g
from utils.responses import success_response, error_response, sanitize_error_for_client
from src.contexts.identity.interface.auth_decorators import require_auth
from src.shared.infrastructure.supabase_client import get_supabase, is_supabase_enabled
from src.contexts.content_library import (
    list_history_entries as get_histories,
    delete_history_entry as delete_history,
    update_history_entry as update_history,
    toggle_favorite,
)
# Phase 5-e: supabase_service 다중 import를 도메인별 facade로 분리.
# 각 facade는 services/data/ 내부이므로 베이스라인에서 자연스럽게 제외.
from services.data.api_key_storage_facade import save_api_keys, get_api_keys
from services.data.custom_style_facade import (
    save_custom_style, get_custom_styles, delete_custom_style,
)
from services.data.usage_admin_facade import (
    get_usage, is_admin, get_all_users_usage, reset_user_usage, get_usage_stats,
)
from services.data.content_admin_facade import get_all_contents, get_content_detail
from services.data.account_admin_facade import (
    delete_user_account, update_user_profile, update_user_password,
)
from services.data.snippet_facade import (
    get_user_snippets, create_snippet, delete_snippet,
)
from services.data.workspace_service import workspace_service, content_approval_service

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)


def _get_json_data():
    """요청 JSON 데이터 안전하게 파싱"""
    return request.get_json(silent=True) or {}


def _check_supabase():
    """Supabase 활성화 확인, 비활성화시 에러 응답 반환"""
    if not is_supabase_enabled():
        return jsonify({'error': 'Supabase가 설정되지 않았습니다.'}), 400
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


@auth_bp.route('/api/auth/status', methods=['GET'])
def auth_status():
    """Supabase 활성화 상태 확인"""
    return jsonify({'enabled': is_supabase_enabled()})


@auth_bp.route('/api/auth/config', methods=['GET'])
def auth_config():
    """프론트엔드용 Supabase 설정 반환 (JS SDK 초기화용)"""
    import os
    return jsonify({
        'enabled': is_supabase_enabled(),
        'url': os.getenv('SUPABASE_URL'),
        'anonKey': os.getenv('SUPABASE_ANON_KEY')
    })


def _validate_email_password(data):
    """이메일/비밀번호 검증 공통 함수"""
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return None, None, _error_response('이메일과 비밀번호를 입력해주세요.')
    return email, password, None


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
        result = get_supabase().auth.sign_up({'email': email, 'password': password})

        if result.user:
            return _success_response({
                'message': '회원가입이 완료되었습니다. 이메일을 확인해주세요.',
                'user': {'id': result.user.id, 'email': result.user.email}
            })
        return _error_response('회원가입에 실패했습니다.')

    except Exception as e:
        error_msg = str(e).lower()
        if 'already registered' in error_msg:
            return _error_response('이미 등록된 이메일입니다.')
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
        get_supabase().auth.reset_password_email(email)
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
        allowed_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5001').split(',')
        allowed_origins = [o.strip().rstrip('/') for o in allowed_origins]
        default_redirect = allowed_origins[0] if allowed_origins else 'http://localhost:3000'
        redirect_url = request.args.get('redirect_url', default_redirect)
        if not any(redirect_url.startswith(origin) for origin in allowed_origins):
            redirect_url = default_redirect

        result = get_supabase().auth.sign_in_with_oauth({
            'provider': provider,
            'options': {
                'redirect_to': redirect_url
            }
        })

        return jsonify({'url': result.url})
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
        # Supabase에서 코드를 세션으로 교환
        result = get_supabase().auth.exchange_code_for_session({'auth_code': code})

        if result.user and result.session:
            return _success_response({
                'user': {'id': result.user.id, 'email': result.user.email},
                'session': {
                    'access_token': result.session.access_token,
                    'refresh_token': result.session.refresh_token,
                    'expires_at': result.session.expires_at
                }
            })
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
        result = get_supabase().auth.sign_in_with_password({'email': email, 'password': password})

        if result.user and result.session:
            return _success_response({
                'user': {'id': result.user.id, 'email': result.user.email},
                'session': {
                    'access_token': result.session.access_token,
                    'refresh_token': result.session.refresh_token,
                    'expires_at': result.session.expires_at
                }
            })
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
        get_supabase().auth.sign_out()
        return _success_response()
    except Exception as e:
        return _exception_error_response(
            '로그아웃 오류',
            e,
            '[인증 실패] 로그아웃 처리에 실패했습니다.',
            400
        )


@auth_bp.route('/api/auth/refresh', methods=['POST'])
def refresh_token():
    """토큰 갱신"""
    error = _check_supabase()
    if error:
        return error

    refresh_token_value = _get_json_data().get('refresh_token')
    if not refresh_token_value:
        return _error_response('Refresh token이 필요합니다.')

    try:
        result = get_supabase().auth.refresh_session(refresh_token_value)

        if result.session:
            return _success_response({
                'session': {
                    'access_token': result.session.access_token,
                    'refresh_token': result.session.refresh_token,
                    'expires_at': result.session.expires_at
                }
            })
        return _error_response('토큰 갱신에 실패했습니다.', 401)

    except Exception as e:
        return _exception_error_response(
            '토큰 갱신 오류',
            e,
            '[인증 실패] 토큰 갱신에 실패했습니다. 다시 로그인해주세요.',
            401
        )


@auth_bp.route('/api/auth/me', methods=['GET'])
@require_auth
def get_current_user():
    """현재 사용자 정보 조회"""
    try:
        user = get_supabase().auth.get_user(g.access_token)
        return jsonify({
            'user': {
                'id': user.user.id,
                'email': user.user.email,
                'created_at': user.user.created_at
            }
        })
    except Exception as e:
        return _exception_error_response(
            '사용자 정보 조회 오류',
            e,
            '[인증 실패] 사용자 정보를 확인할 수 없습니다. 다시 로그인해주세요.',
            401
        )


# 관리자 권한 헬퍼 — 단일 정의 (admin.py와 channel_monitoring.py에서 공유).
# is_admin은 namespace 호출이므로 `@patch('routes.auth_routes.is_admin')` 그대로 동작.
# 서브패키지 import 전에 미리 정의해 admin.py가 `_ar._require_admin`을 안전하게 참조 가능.
def _require_admin():
    """관리자 권한 확인."""
    if not is_admin(g.user_id):
        return _error_response('관리자 권한이 필요합니다.', 403)
    return None


# 사용자 설정(API 키/커스텀 스타일/사용량) 라우트는 routes/auth/user_settings.py로 분리됨.
# 테스트가 import하는 _mask_api_key 헬퍼는 호환성 위해 여기서 re-export.
# (이 import가 routes.auth 패키지 __init__을 트리거해 admin/channel_monitoring 등을 로드)
from routes.auth.user_settings import _mask_api_key  # noqa: E402,F401


# ============================================================
# 분리된 auth 서브 라우트 — 부수효과 import (이미 위 import로 로드되었음)
# - routes/auth/admin.py: 관리자 라우트 (6개)
# ============================================================
from routes import auth as _auth_subroutes  # noqa: E402,F401
from routes.auth.channel_monitoring import admin_dashboard  # noqa: E402,F401
