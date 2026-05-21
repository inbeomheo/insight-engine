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


# 사용자 설정(API 키/커스텀 스타일/사용량) 라우트는 routes/auth/user_settings.py로 분리됨.
# 테스트가 import하는 _mask_api_key 헬퍼는 호환성 위해 여기서 re-export.
from routes.auth.user_settings import _mask_api_key  # noqa: E402,F401


# 관리자 권한 헬퍼 (admin 라우트는 routes/auth/admin.py로 분리됨,
# 본 헬퍼는 다른 라우트에서도 재사용되므로 여기 유지)
def _require_admin():
    """관리자 권한 확인."""
    if not is_admin(g.user_id):
        return _error_response('관리자 권한이 필요합니다.', 403)
    return None


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
            .select('created_at,style,elapsed_time,success,content') \
            .gte('created_at', week_ago) \
            .execute()

        items = histories.data or []
        total = len(items)
        success_count = sum(1 for i in items if i.get('success', True))

        # 스타일 분포 + 콘텐츠 길이 집계
        style_dist = {}
        total_time = 0
        total_content_length = 0
        content_count = 0
        for item in items:
            s = item.get('style', 'unknown')
            style_dist[s] = style_dist.get(s, 0) + 1
            total_time += float(item.get('elapsed_time', 0) or 0)
            content = item.get('content') or ''
            if content:
                total_content_length += len(content)
                content_count += 1

        avg_time = round(total_time / total, 2) if total > 0 else 0
        avg_content_length = round(total_content_length / content_count) if content_count > 0 else 0

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

        # 가장 많이 사용된 스타일 상위 3개
        top_styles = sorted(style_dist.items(), key=lambda x: x[1], reverse=True)[:3]
        top_styles = [{'style': s, 'count': c} for s, c in top_styles]

        # 가장 생성이 많은 시간대 (0~23시)
        hour_dist = {}
        for item in items:
            created = item.get('created_at', '')
            if created and len(created) >= 13:
                try:
                    hour = int(created[11:13])
                    hour_dist[hour] = hour_dist.get(hour, 0) + 1
                except (ValueError, IndexError):
                    pass
        busiest_hour = max(hour_dist, key=hour_dist.get) if hour_dist else None

        # 최근 5개 생성 기록 (제목 + 스타일)
        sorted_items = sorted(items, key=lambda x: x.get('created_at', ''), reverse=True)
        recent_generations = []
        for item in sorted_items[:5]:
            title = (item.get('content') or '')[:80].split('\n')[0].strip()
            if not title:
                title = '(제목 없음)'
            recent_generations.append({
                'title': title,
                'style': item.get('style', 'unknown'),
                'created_at': item.get('created_at', ''),
            })

        # 프로바이더별 활성 상태 집계 (서버 설정 기반)
        from config import PROVIDER_API_KEYS
        provider_distribution = {}
        _provider_labels = {
            'gemini': 'Gemini', 'deepseek': 'DeepSeek', 'zhipuai': 'Zhipu AI',
            'ollama': 'Ollama', 'openai': 'OpenAI', 'anthropic': 'Anthropic',
            'openrouter': 'OpenRouter', 'chatmock': 'ChatMock',
        }
        for prov, key in PROVIDER_API_KEYS.items():
            if key and key not in ('', 'dummy', 'http://localhost:11434'):
                provider_distribution[_provider_labels.get(prov, prov)] = 'active'
            elif prov == 'ollama' and key:
                provider_distribution[_provider_labels.get(prov, prov)] = 'local'

        return jsonify({
            'period': '7d',
            'total_generations': total,
            'success_rate': round(success_count / total * 100, 1) if total > 0 else 0,
            'avg_time': avg_time,
            'avg_content_length': avg_content_length,
            'style_distribution': style_dist,
            'top_styles': top_styles,
            'daily_usage': daily_usage,
            'recent_generations': recent_generations,
            'busiest_hour': busiest_hour,
            'provider_distribution': provider_distribution,
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

    from utils.responses import clamp_query_int
    user_id = request.args.get('user_id')
    action = request.args.get('action')
    limit = clamp_query_int(request.args.get('limit'), default=50, max_val=200)
    offset = clamp_query_int(request.args.get('offset'), default=0, min_val=0, max_val=100000)

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

    from utils.responses import clamp_query_int
    limit = clamp_query_int(request.args.get('limit'), default=50, max_val=200)
    offset = clamp_query_int(request.args.get('offset'), default=0, min_val=0, max_val=100000)

    items = activity_feed_service.get_feed(workspace_id, limit=limit, offset=offset)
    return jsonify({'items': items})


# =============================================
# 사용량 알림 API (F4-09)
# =============================================

@auth_bp.route('/api/user/usage-alerts', methods=['GET'])
@require_auth
def get_usage_alerts():
    """현재 사용자의 사용량 알림 목록"""
    from services.usage.usage_alert_service import usage_alert_service
    alerts = usage_alert_service.get_alerts(g.user_id)
    return jsonify({'alerts': alerts})


@auth_bp.route('/api/user/usage-alerts/check', methods=['POST'])
@require_auth
def check_usage_alerts():
    """사용량 체크 후 임계치 알림 생성"""
    from services.usage.usage_alert_service import usage_alert_service

    data = _get_json_data()
    used = data.get('used')
    total = data.get('total')
    if used is None or total is None:
        return _error_response('used와 total 값이 필요합니다.')

    try:
        used = int(used)
        total = int(total)
    except (ValueError, TypeError):
        return _error_response('used와 total은 정수여야 합니다.')

    new_alerts = usage_alert_service.check_usage(g.user_id, used, total)
    return jsonify({'new_alerts': new_alerts})


@auth_bp.route('/api/user/usage-alerts/reset', methods=['POST'])
@require_auth
def reset_usage_alerts():
    """사용량 알림 초기화 (월간 리셋)"""
    from services.usage.usage_alert_service import usage_alert_service
    usage_alert_service.reset_alerts(g.user_id)
    return _success_response({'message': '사용량 알림이 초기화되었습니다.'})


# =============================================
# SSO (SAML/OIDC) API (F4-24)
# =============================================

@auth_bp.route('/api/sso/<workspace_id>/config', methods=['POST'])
@require_auth
def sso_configure(workspace_id):
    """SSO 프로바이더 설정"""
    from services.auth.sso_service import sso_service
    data = _get_json_data()
    provider = data.get('provider', '')
    config = data.get('config', {})
    if not provider:
        return _error_response('provider는 필수입니다.')
    result = sso_service.configure_sso(workspace_id, provider, config)
    if 'error' in result:
        return _error_response(result['error'])
    return jsonify(result)


@auth_bp.route('/api/sso/<workspace_id>/config', methods=['GET'])
@require_auth
def sso_get_config(workspace_id):
    """SSO 설정 조회"""
    from services.auth.sso_service import sso_service
    config = sso_service.get_config(workspace_id)
    if not config:
        return jsonify({'enabled': False})
    return jsonify(config)


@auth_bp.route('/api/sso/<workspace_id>/login', methods=['POST'])
def sso_login(workspace_id):
    """SSO 로그인 시작 (리다이렉트 URL 반환)"""
    from services.auth.sso_service import sso_service
    result = sso_service.initiate_login(workspace_id)
    if 'error' in result:
        return _error_response(result['error'])
    return jsonify(result)


@auth_bp.route('/api/sso/<workspace_id>/callback', methods=['POST'])
def sso_callback(workspace_id):
    """SSO 콜백 검증 + 세션 생성"""
    from services.auth.sso_service import sso_service
    data = _get_json_data()
    result = sso_service.validate_callback(workspace_id, data)
    if 'error' in result:
        return _error_response(result['error'])
    return jsonify(result)


@auth_bp.route('/api/sso/<workspace_id>/disable', methods=['POST'])
@require_auth
def sso_disable(workspace_id):
    """SSO 비활성화"""
    from services.auth.sso_service import sso_service
    result = sso_service.disable_sso(workspace_id)
    if 'error' in result:
        return _error_response(result['error'])
    return jsonify(result)

# ============================================================
# 분리된 auth 서브 라우트 — 부수효과 import
# - routes/auth/admin.py: 관리자 라우트 (6개)
# ============================================================
from routes import auth as _auth_subroutes  # noqa: E402,F401
