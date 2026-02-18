"""
인증 관련 라우트
회원가입, 로그인, 로그아웃, 사용자 정보 조회
"""
from flask import Blueprint, request, jsonify, g
from services.supabase_service import (
    get_supabase, is_supabase_enabled, require_auth,
    save_api_keys, get_api_keys,
    save_custom_style, get_custom_styles, delete_custom_style,
    get_usage, is_admin, get_all_users_usage, reset_user_usage, get_usage_stats,
    get_all_contents, get_content_detail,
    get_histories, delete_history, update_history, toggle_favorite,
    delete_user_account,
    update_user_profile, update_user_password
)

auth_bp = Blueprint('auth', __name__)


def _get_json_data():
    """요청 JSON 데이터 안전하게 파싱"""
    return request.get_json(silent=True) or {}


def _check_supabase():
    """Supabase 활성화 확인, 비활성화시 에러 응답 반환"""
    if not is_supabase_enabled():
        return jsonify({'error': 'Supabase가 설정되지 않았습니다.'}), 400
    return None


def _success_response(data=None):
    """성공 응답 생성"""
    response = {'success': True}
    if data:
        response.update(data)
    return jsonify(response)


def _error_response(message, status_code=400):
    """에러 응답 생성"""
    return jsonify({'error': message}), status_code


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
        return _success_response({
            'message': '비밀번호 재설정 이메일을 발송했습니다. 이메일을 확인해주세요.'
        })
    except Exception as e:
        error_msg = str(e).lower()
        if 'not found' in error_msg:
            return _error_response('등록되지 않은 이메일입니다.')
        # 보안: 상세 에러 메시지는 로깅만 하고 일반 메시지 반환
        import logging
        logging.getLogger(__name__).error(f'비밀번호 재설정 오류: {e}')
        return _error_response('이메일 발송 중 오류가 발생했습니다.')


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
        # 현재 요청의 호스트에서 redirect URL 생성
        redirect_url = request.args.get('redirect_url', request.host_url.rstrip('/'))

        result = get_supabase().auth.sign_in_with_oauth({
            'provider': provider,
            'options': {
                'redirect_to': redirect_url
            }
        })

        return jsonify({'url': result.url})
    except Exception as e:
        return _error_response(f'OAuth 오류: {str(e)}')


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
        error_msg = str(e)
        return _error_response(f'OAuth 콜백 오류: {error_msg}', 401)


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
        error_msg = str(e)
        if 'invalid' in error_msg.lower():
            return _error_response('이메일 또는 비밀번호가 올바르지 않습니다.', 401)
        return _error_response(f'로그인 오류: {error_msg}', 401)


@auth_bp.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    """로그아웃"""
    try:
        get_supabase().auth.sign_out()
        return _success_response()
    except Exception as e:
        return _error_response(str(e))


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
        return _error_response(str(e), 401)


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
        return _error_response(str(e), 401)

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
    return _error_response(result.get('error', '즐겨찾기 변경에 실패했습니다.'), 500)


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
    return _error_response(result.get('error', '프로필 업데이트에 실패했습니다.'), 500)


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
    return _error_response(result.get('error', '비밀번호 변경에 실패했습니다.'), 500)


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
