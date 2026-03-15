"""
인증 관련 라우트
회원가입, 로그인, 로그아웃, 사용자 정보 조회
"""
import logging
import os

from flask import Blueprint, request, jsonify, g
from utils.responses import success_response, error_response, sanitize_error_for_client
from services.data.supabase_service import (
    get_supabase, is_supabase_enabled, require_auth,
    save_api_keys, get_api_keys,
    save_custom_style, get_custom_styles, delete_custom_style,
    get_usage, is_admin, get_all_users_usage, reset_user_usage, get_usage_stats,
    get_all_contents, get_content_detail,
    get_histories, delete_history, update_history, toggle_favorite,
    delete_user_account,
    update_user_profile, update_user_password,
    get_user_snippets, create_snippet, delete_snippet
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

# =============================================
# API 키 관리
# =============================================

def _mask_api_key(key):
    """API 키 마스킹 (보안 강화)

    기존: 8자 + 4자 = 12자 노출
    변경: 4자 + 2자 = 6자 노출
    """
    if not key:
        return None
    if len(key) <= 8:
        return '****'
    return f'{key[:4]}...{key[-2:]}'


@auth_bp.route('/api/user/keys', methods=['GET'])
@require_auth
def get_user_keys():
    """사용자 API 키 조회"""
    keys = get_api_keys(g.user_id)
    masked_keys = {
        k: _mask_api_key(v) if k != 'selectedProvider' else v
        for k, v in keys.items()
    }
    return jsonify({'keys': masked_keys, 'selectedProvider': keys.get('selectedProvider')})


@auth_bp.route('/api/user/keys', methods=['POST'])
@require_auth
def save_user_keys():
    """사용자 API 키 저장"""
    if save_api_keys(g.user_id, _get_json_data()):
        return _success_response()
    return _error_response('API 키 저장에 실패했습니다.', 500)


# =============================================
# 커스텀 스타일 관리
# =============================================

@auth_bp.route('/api/user/styles', methods=['GET'])
@require_auth
def get_user_styles():
    """사용자 커스텀 스타일 조회"""
    return jsonify({'styles': get_custom_styles(g.user_id)})


@auth_bp.route('/api/user/styles', methods=['POST'])
@require_auth
def save_user_style():
    """사용자 커스텀 스타일 저장"""
    if save_custom_style(g.user_id, _get_json_data()):
        return _success_response()
    return _error_response('스타일 저장에 실패했습니다.', 500)


@auth_bp.route('/api/user/styles/<style_id>', methods=['DELETE'])
@require_auth
def delete_user_style(style_id):
    """사용자 커스텀 스타일 삭제"""
    if delete_custom_style(g.user_id, style_id):
        return _success_response()
    return _error_response('삭제에 실패했습니다.', 500)


# =============================================
# 사용량 조회
# =============================================

@auth_bp.route('/api/user/usage', methods=['GET'])
@require_auth
def get_user_usage():
    """사용자 사용량 조회 (남은 횟수, 최대 횟수)"""
    usage = get_usage(g.user_id)
    # 관리자 여부 추가
    usage['is_admin'] = is_admin(g.user_id)
    return jsonify(usage)


# =============================================
# 히스토리 조회 API
# =============================================

@auth_bp.route('/api/user/history', methods=['GET'])
@require_auth
def get_user_history():
    """사용자 히스토리 조회 (클라우드 동기화, 페이지네이션 지원)

    - 일반 사용자: 본인 히스토리만
    - 관리자: 모든 사용자 히스토리

    Query Parameters:
        page: 페이지 번호 (기본값: 1)
        per_page: 페이지당 항목 수 (기본값: 20)
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    data = get_histories(g.user_id, page, per_page)
    histories = data.get('histories', [])

    # 프론트엔드 포맷에 맞게 변환
    result = []
    for h in histories:
        result.append({
            'id': h.get('report_id'),
            'url': h.get('url'),
            'title': h.get('title'),
            'style': h.get('style'),
            'html': h.get('html'),
            'content': h.get('content'),
            'prompt': h.get('prompt'),
            'usage': h.get('usage'),
            'elapsed_time': h.get('elapsed_time'),
            'is_favorite': h.get('is_favorite', False),
            'keywords': h.get('keywords', []),
            'createdAt': h.get('created_at'),
            'timestamp': h.get('created_at')
        })

    return jsonify({
        'histories': result,
        'total': data.get('total', 0),
        'page': data.get('page', 1),
        'per_page': data.get('per_page', 20),
        'total_pages': data.get('total_pages', 0),
        'has_more': data.get('has_more', False),
        'is_admin': is_admin(g.user_id)
    })


@auth_bp.route('/api/user/history/<report_id>', methods=['DELETE'])
@require_auth
def delete_user_history(report_id):
    """사용자 히스토리 삭제 (클라우드)

    RLS + user_id 매칭으로 본인 데이터만 삭제 가능.
    """
    if not report_id:
        return _error_response('report_id가 필요합니다.')

    if delete_history(g.user_id, report_id):
        return _success_response()
    return _error_response('삭제에 실패했습니다.', 500)


@auth_bp.route('/api/user/history/<report_id>/favorite', methods=['POST'])
@require_auth
def toggle_history_favorite(report_id):
    """히스토리 즐겨찾기 토글"""
    if not report_id:
        return _error_response('report_id가 필요합니다.')

    result = toggle_favorite(g.user_id, report_id)
    if result.get('success'):
        return jsonify({'is_favorite': result['is_favorite']})
    return _safe_service_error_response(
        result.get('error'),
        '[서버 오류] 즐겨찾기 변경에 실패했습니다.',
        500
    )


@auth_bp.route('/api/user/history/<report_id>', methods=['PUT'])
@require_auth
def update_user_history(report_id):
    """히스토리 콘텐츠 업데이트 (인라인 편집용)"""
    if not report_id:
        return _error_response('report_id가 필요합니다.')

    data = _get_json_data()
    allowed_fields = {'content', 'html', 'title'}
    updates = {k: v for k, v in data.items() if k in allowed_fields}

    if not updates:
        return _error_response('업데이트할 필드가 없습니다.')

    if update_history(g.user_id, report_id, updates):
        return _success_response()
    return _error_response('업데이트에 실패했습니다.', 500)


@auth_bp.route('/api/user/profile', methods=['PUT'])
@require_auth
def update_profile():
    """프로필(닉네임) 업데이트"""
    data = _get_json_data()
    display_name = data.get('display_name', '').strip()
    if not display_name:
        return _error_response('닉네임을 입력해주세요.')
    if len(display_name) > 50:
        return _error_response('닉네임은 50자 이내로 입력해주세요.')

    result = update_user_profile(g.user_id, display_name)
    if result['success']:
        return _success_response({'user': result.get('user')})
    return _safe_service_error_response(
        result.get('error'),
        '[서버 오류] 프로필 업데이트에 실패했습니다.',
        500
    )


@auth_bp.route('/api/user/password', methods=['PUT'])
@require_auth
def change_password():
    """비밀번호 변경"""
    data = _get_json_data()
    new_password = data.get('new_password', '')
    if len(new_password) < 6:
        return _error_response('비밀번호는 6자 이상이어야 합니다.')

    result = update_user_password(g.user_id, new_password)
    if result['success']:
        return _success_response()
    return _safe_service_error_response(
        result.get('error'),
        '[서버 오류] 비밀번호 변경에 실패했습니다.',
        500
    )


@auth_bp.route('/api/user/account', methods=['DELETE'])
@require_auth
def delete_account():
    """사용자 계정 완전 삭제

    auth.users 삭제 → CASCADE로 모든 사용자 데이터 자동 정리.
    """
    if delete_user_account(g.user_id):
        return _success_response({'message': '계정이 삭제되었습니다.'})
    return _error_response('계정 삭제에 실패했습니다.', 500)


# =============================================
# 관리자 API
# =============================================

def _require_admin():
    """관리자 권한 확인"""
    if not is_admin(g.user_id):
        return _error_response('관리자 권한이 필요합니다.', 403)
    return None


@auth_bp.route('/api/admin/check', methods=['GET'])
@require_auth
def check_admin():
    """현재 사용자가 관리자인지 확인"""
    return jsonify({'is_admin': is_admin(g.user_id)})


@auth_bp.route('/api/admin/users', methods=['GET'])
@require_auth
def get_admin_users():
    """모든 사용자의 사용량 조회 (관리자 전용)"""
    error = _require_admin()
    if error:
        return error

    users = get_all_users_usage()
    return jsonify({'users': users})


@auth_bp.route('/api/admin/users/<user_id>/reset', methods=['POST'])
@require_auth
def admin_reset_user(user_id):
    """특정 사용자 사용량 리셋 (관리자 전용)"""
    error = _require_admin()
    if error:
        return error

    if reset_user_usage(user_id):
        return _success_response({'message': f'사용자 {user_id}의 사용량이 리셋되었습니다.'})
    return _error_response('리셋에 실패했습니다.', 500)


@auth_bp.route('/api/admin/stats', methods=['GET'])
@require_auth
def get_admin_stats():
    """사용량 통계 조회 (관리자 전용)"""
    error = _require_admin()
    if error:
        return error

    stats = get_usage_stats()
    return jsonify(stats)


@auth_bp.route('/api/admin/contents', methods=['GET'])
@require_auth
def get_admin_contents():
    """모든 사용자의 생성 콘텐츠 조회 (관리자 전용)

    Query Parameters:
        page: 페이지 번호 (기본값: 1)
        per_page: 페이지당 항목 수 (기본값: 20)
        user_id: 특정 사용자 필터 (선택)
    """
    error = _require_admin()
    if error:
        return error

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    user_id = request.args.get('user_id', None, type=str)

    result = get_all_contents(page, per_page, user_id)
    return jsonify(result)


@auth_bp.route('/api/admin/contents/<report_id>', methods=['GET'])
@require_auth
def get_admin_content_detail(report_id):
    """특정 콘텐츠 상세 조회 (관리자 전용)"""
    error = _require_admin()
    if error:
        return error

    content = get_content_detail(report_id)
    if not content:
        return _error_response('콘텐츠를 찾을 수 없습니다.', 404)
    return jsonify(content)


# =============================================
# 워크스페이스 API
# =============================================

@auth_bp.route('/api/workspaces', methods=['POST'])
@require_auth
def create_workspace():
    """워크스페이스 생성"""
    error = _check_supabase()
    if error:
        return error

    name = _get_json_data().get('name', '').strip()
    if not name:
        return _error_response('워크스페이스 이름을 입력해주세요.')

    try:
        result = workspace_service.create_workspace(name, g.user_id)
        if isinstance(result, dict) and 'error' in result:
            return _safe_service_error_response(
                result['error'],
                '[서버 오류] 워크스페이스 생성에 실패했습니다.',
                500
            )
        return jsonify(result), 201
    except Exception as e:
        return _exception_error_response(
            '워크스페이스 생성 오류',
            e,
            '[서버 오류] 워크스페이스 생성 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/workspaces', methods=['GET'])
@require_auth
def list_workspaces():
    """사용자 워크스페이스 목록"""
    error = _check_supabase()
    if error:
        return jsonify({'workspaces': []})

    try:
        workspaces = workspace_service.list_workspaces(g.user_id)
        return jsonify({'workspaces': workspaces})
    except Exception as e:
        return _exception_error_response(
            '워크스페이스 목록 조회 오류',
            e,
            '[서버 오류] 워크스페이스 목록 조회 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/workspaces/<workspace_id>/members', methods=['GET'])
@require_auth
def get_workspace_members(workspace_id):
    """워크스페이스 멤버 목록"""
    error = _check_supabase()
    if error:
        return error

    try:
        # IDOR 방지: 요청자가 해당 워크스페이스 멤버인지 확인
        if not workspace_service.is_member(workspace_id, g.user_id):
            return _error_response('워크스페이스에 접근할 수 없습니다.', 403)

        members = workspace_service.get_members(workspace_id)
        return jsonify({'members': members})
    except Exception as e:
        return _exception_error_response(
            '워크스페이스 멤버 조회 오류',
            e,
            '[서버 오류] 워크스페이스 멤버 조회 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/workspaces/<workspace_id>/invite', methods=['POST'])
@require_auth
def invite_workspace_member(workspace_id):
    """워크스페이스 멤버 초대 (이메일로)"""
    error = _check_supabase()
    if error:
        return error

    data = _get_json_data()
    user_email = data.get('user_email', '').strip()
    role = data.get('role', 'editor')

    if not user_email:
        return _error_response('이메일을 입력해주세요.')

    try:
        # owner 권한 확인
        ws = workspace_service.get_workspace(workspace_id)
        if not ws or ws.get('owner_id') != g.user_id:
            return _error_response('워크스페이스 소유자만 초대할 수 있습니다.', 403)

        # 이메일로 사용자 ID 조회
        target_user_id = workspace_service.find_user_by_email(user_email)
        if not target_user_id:
            return _error_response(f'등록되지 않은 이메일입니다: {user_email}', 404)

        result = workspace_service.invite_member(workspace_id, target_user_id, role)
        if isinstance(result, dict) and 'error' in result:
            return _safe_service_error_response(
                result['error'],
                '[서버 오류] 워크스페이스 초대 처리에 실패했습니다.'
            )
        return _success_response({'member': result})
    except Exception as e:
        return _exception_error_response(
            '워크스페이스 초대 오류',
            e,
            '[서버 오류] 워크스페이스 초대 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/workspaces/<workspace_id>/members/<user_id>', methods=['DELETE'])
@require_auth
def remove_workspace_member(workspace_id, user_id):
    """워크스페이스 멤버 제거"""
    error = _check_supabase()
    if error:
        return error

    try:
        # owner 권한 확인
        ws = workspace_service.get_workspace(workspace_id)
        if not ws or ws.get('owner_id') != g.user_id:
            return _error_response('워크스페이스 소유자만 멤버를 제거할 수 있습니다.', 403)

        if workspace_service.remove_member(workspace_id, user_id):
            return _success_response()
        return _error_response('멤버 제거에 실패했습니다.', 500)
    except Exception as e:
        return _exception_error_response(
            '워크스페이스 멤버 제거 오류',
            e,
            '[서버 오류] 멤버 제거 중 문제가 발생했습니다.'
        )


# =============================================
# 스타일 메모리 API
# =============================================

@auth_bp.route('/api/user/style-memory', methods=['GET'])
@require_auth
def get_style_memory():
    """사용자 스타일 메모리 프로필 조회"""
    from services.data.style_memory_service import get_profile
    profile = get_profile(g.user_id)
    return jsonify({'profile': profile})


@auth_bp.route('/api/user/style-memory', methods=['PUT'])
@require_auth
def update_style_memory():
    """사용자 스타일 메모리 선호도 저장

    Body: {avoid_keywords?, custom_instructions?, style_memory_enabled?}
    """
    from services.data.style_memory_service import save_user_preferences
    data = _get_json_data()
    ok = save_user_preferences(g.user_id, data)
    if ok:
        return _success_response()
    # Supabase 비활성화 시에도 성공으로 처리 (로컬 모드 graceful)
    return _success_response()


@auth_bp.route('/api/user/style-memory/reset', methods=['POST'])
@require_auth
def reset_style_memory():
    """사용자 스타일 메모리 초기화"""
    from services.data.style_memory_service import reset_profile
    reset_profile(g.user_id)
    return _success_response({'message': '스타일 메모리가 초기화되었습니다.'})


# =============================================
# 스니펫 라이브러리 API
# =============================================

@auth_bp.route('/api/user/snippets', methods=['GET'])
@require_auth
def get_snippets():
    """사용자 스니펫 목록을 반환합니다."""
    snippets = get_user_snippets(g.user_id)
    return jsonify({'snippets': snippets})


@auth_bp.route('/api/user/snippets', methods=['POST'])
@require_auth
def create_snippet_route():
    """새 스니펫을 생성합니다."""
    data = _get_json_data()
    if not data.get('content'):
        return _error_response('스니펫 내용이 필요합니다.')
    try:
        result = create_snippet(g.user_id, data)
        if isinstance(result, dict) and result.get('error'):
            return _safe_service_error_response(
                result['error'],
                '[서버 오류] 스니펫 저장에 실패했습니다.',
                500
            )
        return jsonify(result), 201
    except Exception as e:
        return _exception_error_response(
            '스니펫 저장 오류',
            e,
            '[서버 오류] 스니펫 저장 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/user/snippets/<snippet_id>', methods=['DELETE'])
@require_auth
def delete_snippet_route(snippet_id):
    """스니펫을 삭제합니다."""
    success = delete_snippet(g.user_id, snippet_id)
    if not success:
        return _error_response('삭제 실패', 500)
    return jsonify({'ok': True})


@auth_bp.route('/api/workspaces/<workspace_id>', methods=['DELETE'])
@require_auth
def delete_workspace(workspace_id):
    """워크스페이스 삭제 (owner만)"""
    error = _check_supabase()
    if error:
        return error

    try:
        if workspace_service.delete_workspace(workspace_id, g.user_id):
            return _success_response()
        return _error_response('삭제에 실패했습니다. 소유자만 삭제할 수 있습니다.', 403)
    except Exception as e:
        return _exception_error_response(
            '워크스페이스 삭제 오류',
            e,
            '[서버 오류] 워크스페이스 삭제 중 문제가 발생했습니다.'
        )


# =============================================
# 채널 모니터링 API
# =============================================

@auth_bp.route('/api/admin/dashboard', methods=['GET'])
@require_auth
def admin_dashboard():
    """운영 대시보드 집계 데이터를 반환합니다."""
    error = _require_admin()
    if error:
        return error

    if not is_supabase_enabled():
        return jsonify({'error': 'Supabase 미연결'}), 503

    supabase = get_supabase()
    if not supabase:
        return jsonify({'error': 'Supabase 연결 실패'}), 503

    try:
        from datetime import datetime, timedelta, timezone
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

        # 히스토리 통계
        histories = supabase.table('ie_histories') \
            .select('created_at,style,elapsed_time,success') \
            .gte('created_at', week_ago) \
            .execute()

        items = histories.data or []
        total = len(items)
        success_count = sum(1 for i in items if i.get('success', True))

        # 스타일 분포
        style_dist = {}
        total_time = 0
        for item in items:
            s = item.get('style', 'unknown')
            style_dist[s] = style_dist.get(s, 0) + 1
            total_time += float(item.get('elapsed_time', 0) or 0)

        avg_time = round(total_time / total, 2) if total > 0 else 0

        # 사용량 통계
        usage_data = supabase.table('ie_usage') \
            .select('date,used_count') \
            .gte('date', week_ago[:10]) \
            .order('date', desc=True) \
            .execute()

        daily_usage = [
            {'date': u['date'], 'count': u.get('used_count', 0)}
            for u in (usage_data.data or [])
        ]

        return jsonify({
            'period': '7d',
            'total_generations': total,
            'success_rate': round(success_count / total * 100, 1) if total > 0 else 0,
            'avg_time': avg_time,
            'style_distribution': style_dist,
            'daily_usage': daily_usage,
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Dashboard data failed: {e}")
        return jsonify({'error': '데이터 조회 실패'}), 500


@auth_bp.route('/api/channel-monitors', methods=['GET'])
@require_auth
def get_channel_monitors():
    """사용자 채널 모니터 목록 조회"""
    error = _check_supabase()
    if error:
        return error

    try:
        client = get_supabase()
        result = client.table('ie_channel_monitors') \
            .select('*') \
            .eq('user_id', g.user_id) \
            .order('created_at', desc=True) \
            .execute()
        return jsonify({'monitors': result.data or []})
    except Exception as e:
        return _exception_error_response(
            '모니터 조회 오류',
            e,
            '[서버 오류] 모니터 조회 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/channel-monitors', methods=['POST'])
@require_auth
def create_channel_monitor():
    """채널 모니터 등록"""
    error = _check_supabase()
    if error:
        return error

    data = _get_json_data()
    channel_id = data.get('channel_id', '').strip()
    if not channel_id:
        return _error_response('채널 ID가 필요합니다.')

    try:
        client = get_supabase()
        row = {
            'user_id': g.user_id,
            'channel_id': channel_id,
            'channel_title': data.get('channel_title', ''),
            'style_id': data.get('style_id', 'blog_seo'),
            'modifiers': data.get('modifiers', {
                'length': 'medium',
                'writing_style': 'conversational',
                'language': 'ko',
            }),
            'interval_minutes': data.get('interval_minutes', 30),
            'is_active': True,
        }
        result = client.table('ie_channel_monitors').insert(row).execute()
        return jsonify(result.data[0] if result.data else {}), 201
    except Exception as e:
        return _exception_error_response(
            '모니터 등록 오류',
            e,
            '[서버 오류] 모니터 등록 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/channel-monitors/<monitor_id>', methods=['DELETE'])
@require_auth
def delete_channel_monitor(monitor_id):
    """채널 모니터 삭제"""
    error = _check_supabase()
    if error:
        return error

    try:
        client = get_supabase()
        client.table('ie_channel_monitors') \
            .delete() \
            .eq('id', monitor_id) \
            .eq('user_id', g.user_id) \
            .execute()
        return _success_response()
    except Exception as e:
        return _exception_error_response(
            '모니터 삭제 오류',
            e,
            '[서버 오류] 모니터 삭제 중 문제가 발생했습니다.'
        )


# =============================================
# 워크스페이스 콘텐츠 승인 API
# =============================================

@auth_bp.route('/api/workspace/<workspace_id>/contents', methods=['POST'])
@require_auth
def add_workspace_content(workspace_id):
    """워크스페이스에 콘텐츠 추가 (draft 상태)"""
    error = _check_supabase()
    if error:
        return error

    data = _get_json_data()
    content_id = data.get('content_id', '').strip()
    title = data.get('title', '').strip()

    if not content_id or not title:
        return _error_response('content_id와 title이 필요합니다.')

    try:
        result = content_approval_service.add_content(workspace_id, g.user_id, content_id, title)
        if isinstance(result, dict) and 'error' in result:
            return _safe_service_error_response(
                result['error'],
                '[서버 오류] 콘텐츠 추가에 실패했습니다.'
            )
        return jsonify(result), 201
    except Exception as e:
        return _exception_error_response(
            '워크스페이스 콘텐츠 추가 오류',
            e,
            '[서버 오류] 콘텐츠 추가 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/workspace/<workspace_id>/contents', methods=['GET'])
@require_auth
def get_workspace_contents(workspace_id):
    """워크스페이스 콘텐츠 목록 (상태 필터 선택)"""
    error = _check_supabase()
    if error:
        return error

    try:
        # 멤버 확인
        if not workspace_service.is_member(workspace_id, g.user_id):
            return _error_response('워크스페이스에 접근할 수 없습니다.', 403)

        status = request.args.get('status', None, type=str)
        contents = content_approval_service.get_workspace_contents(workspace_id, status)
        return jsonify({'contents': contents})
    except Exception as e:
        return _exception_error_response(
            '워크스페이스 콘텐츠 조회 오류',
            e,
            '[서버 오류] 워크스페이스 콘텐츠 조회 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/workspace/contents/<content_id>/submit-review', methods=['POST'])
@require_auth
def submit_content_review(content_id):
    """draft → review 상태 전환"""
    error = _check_supabase()
    if error:
        return error

    try:
        result = content_approval_service.submit_for_review(content_id, g.user_id)
        if isinstance(result, dict) and 'error' in result:
            return _safe_service_error_response(
                result['error'],
                '[서버 오류] 검토 요청에 실패했습니다.'
            )
        return jsonify(result)
    except Exception as e:
        return _exception_error_response(
            '콘텐츠 검토 요청 오류',
            e,
            '[서버 오류] 검토 요청 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/workspace/contents/<content_id>/approve', methods=['POST'])
@require_auth
def approve_content(content_id):
    """review → approved 상태 전환 (owner만)"""
    error = _check_supabase()
    if error:
        return error

    try:
        result = content_approval_service.approve_content(content_id, g.user_id)
        if isinstance(result, dict) and 'error' in result:
            return _safe_service_error_response(
                result['error'],
                '[서버 오류] 승인 처리에 실패했습니다.'
            )
        return jsonify(result)
    except Exception as e:
        return _exception_error_response(
            '콘텐츠 승인 오류',
            e,
            '[서버 오류] 승인 처리 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/workspace/contents/<content_id>/reject', methods=['POST'])
@require_auth
def reject_content(content_id):
    """review → rejected 상태 전환 (owner만)"""
    error = _check_supabase()
    if error:
        return error

    data = _get_json_data()
    reason = data.get('reason', '').strip()
    if not reason:
        return _error_response('반려 사유를 입력해주세요.')

    try:
        result = content_approval_service.reject_content(content_id, g.user_id, reason)
        if isinstance(result, dict) and 'error' in result:
            return _safe_service_error_response(
                result['error'],
                '[서버 오류] 반려 처리에 실패했습니다.'
            )
        return jsonify(result)
    except Exception as e:
        return _exception_error_response(
            '콘텐츠 반려 오류',
            e,
            '[서버 오류] 반려 처리 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/workspace/contents/<content_id>/publish', methods=['POST'])
@require_auth
def publish_content(content_id):
    """approved → published 상태 전환 (owner만)"""
    error = _check_supabase()
    if error:
        return error

    try:
        result = content_approval_service.publish_content(content_id, g.user_id)
        if isinstance(result, dict) and 'error' in result:
            return _safe_service_error_response(
                result['error'],
                '[서버 오류] 게시 처리에 실패했습니다.'
            )
        return jsonify(result)
    except Exception as e:
        return _exception_error_response(
            '콘텐츠 게시 오류',
            e,
            '[서버 오류] 게시 처리 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/workspace/contents/<content_id>/revert-draft', methods=['POST'])
@require_auth
def revert_content_to_draft(content_id):
    """approved/rejected → draft 상태 전환 (editor 이상)"""
    error = _check_supabase()
    if error:
        return error

    try:
        result = content_approval_service.revert_to_draft(content_id, g.user_id)
        if isinstance(result, dict) and 'error' in result:
            return _safe_service_error_response(
                result['error'],
                '[서버 오류] 초안 복구에 실패했습니다.'
            )
        return jsonify(result)
    except Exception as e:
        return _exception_error_response(
            '콘텐츠 초안 복구 오류',
            e,
            '[서버 오류] 초안 복구 중 문제가 발생했습니다.'
        )


# =============================================
# 감사 로그 API (F4-25)
# =============================================

@auth_bp.route('/api/admin/audit-logs', methods=['GET'])
@require_auth
def get_audit_logs():
    """감사 로그 조회 (관리자 전용)"""
    from services.data.audit_log_service import audit_log_service
    from services.data.supabase_service import is_admin

    if not is_admin(g.user_id):
        return _error_response('관리자 권한이 필요합니다.', 403)

    user_id = request.args.get('user_id')
    action = request.args.get('action')
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))

    logs = audit_log_service.query(
        user_id=user_id,
        action=action,
        limit=limit,
        offset=offset,
    )
    return jsonify({'logs': logs})


# =============================================
# 활동 피드 API (F5-24)
# =============================================

@auth_bp.route('/api/workspaces/<workspace_id>/activity', methods=['GET'])
@require_auth
def get_workspace_activity(workspace_id):
    """워크스페이스 활동 피드 조회"""
    from services.data.activity_feed_service import activity_feed_service

    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))

    items = activity_feed_service.get_feed(workspace_id, limit=limit, offset=offset)
    return jsonify({'items': items})
