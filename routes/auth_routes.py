"""
인증 관련 라우트
회원가입, 로그인, 로그아웃, 사용자 정보 조회
"""
from flask import Blueprint, request, jsonify, g
from services.supabase_service import (
    get_supabase, is_supabase_enabled, require_auth,
    save_api_keys, get_api_keys,
    get_histories, delete_history, update_history,
    save_custom_style, get_custom_styles, delete_custom_style
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
        error_msg = str(e)
        if 'already registered' in error_msg.lower():
            return _error_response('이미 등록된 이메일입니다.')
        return _error_response(f'회원가입 오류: {error_msg}')


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
    """API 키 마스킹 (보안)"""
    if not key or len(key) <= 12:
        return '****' if key else None
    return f'{key[:8]}...{key[-4:]}'


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
# 히스토리 관리
# =============================================

def _format_history(h):
    """DB 히스토리를 프론트엔드 형식으로 변환"""
    return {
        'id': h['report_id'],
        'url': h['url'],
        'title': h['title'],
        'style': h['style'],
        'content': h['content'],
        'html': h['html'],
        'mindmapMarkdown': h.get('mindmap_markdown'),
        'usage': h.get('usage'),
        'elapsed_time': h.get('elapsed_time'),
        'time': h['created_at'],
        'timestamp': h['created_at']
    }


@auth_bp.route('/api/user/histories', methods=['GET'])
@require_auth
def get_user_histories():
    """사용자 히스토리 조회"""
    histories = get_histories(g.user_id)
    return jsonify({'histories': [_format_history(h) for h in histories]})


@auth_bp.route('/api/user/histories/<report_id>', methods=['DELETE'])
@require_auth
def delete_user_history(report_id):
    """사용자 히스토리 삭제"""
    if delete_history(g.user_id, report_id):
        return _success_response()
    return _error_response('삭제에 실패했습니다.', 500)


@auth_bp.route('/api/user/histories/<report_id>', methods=['PATCH'])
@require_auth
def update_user_history(report_id):
    """사용자 히스토리 업데이트"""
    data = _get_json_data()
    updates = {}

    if 'mindmapMarkdown' in data:
        updates['mindmap_markdown'] = data['mindmapMarkdown']

    if update_history(g.user_id, report_id, updates):
        return _success_response()
    return _error_response('업데이트에 실패했습니다.', 500)


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
