"""기타 사용자 영역 — 스타일 메모리, 스니펫, 감사 로그, 활동 피드,
사용량 알림, SSO 라우트.

auth_routes.py에서 분리됨. namespace 경유 호출 패턴 유지.
"""
from flask import g, jsonify, request

from routes import auth_routes as _ar
from routes.auth_routes import auth_bp
from services.data.supabase_service import require_auth


# ── 스타일 메모리 ───────────────────────────────────────


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
    data = _ar._get_json_data()
    ok = save_user_preferences(g.user_id, data)
    if ok:
        return _ar._success_response()
    # Supabase 비활성화 시에도 성공으로 처리 (로컬 모드 graceful)
    return _ar._success_response()


@auth_bp.route('/api/user/style-memory/reset', methods=['POST'])
@require_auth
def reset_style_memory():
    """사용자 스타일 메모리 초기화"""
    from services.data.style_memory_service import reset_profile
    reset_profile(g.user_id)
    return _ar._success_response({'message': '스타일 메모리가 초기화되었습니다.'})


# ── 스니펫 라이브러리 ────────────────────────────────────


@auth_bp.route('/api/user/snippets', methods=['GET'])
@require_auth
def get_snippets():
    """사용자 스니펫 목록을 반환합니다."""
    snippets = _ar.get_user_snippets(g.user_id)
    return jsonify({'snippets': snippets})


@auth_bp.route('/api/user/snippets', methods=['POST'])
@require_auth
def create_snippet_route():
    """새 스니펫을 생성합니다."""
    data = _ar._get_json_data()
    if not data.get('content'):
        return _ar._error_response('스니펫 내용이 필요합니다.')
    try:
        result = _ar.create_snippet(g.user_id, data)
        if isinstance(result, dict) and result.get('error'):
            return _ar._safe_service_error_response(
                result['error'],
                '[서버 오류] 스니펫 저장에 실패했습니다.',
                500
            )
        return jsonify(result), 201
    except Exception as e:
        return _ar._exception_error_response(
            '스니펫 저장 오류',
            e,
            '[서버 오류] 스니펫 저장 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/user/snippets/<snippet_id>', methods=['DELETE'])
@require_auth
def delete_snippet_route(snippet_id):
    """스니펫을 삭제합니다."""
    success = _ar.delete_snippet(g.user_id, snippet_id)
    if not success:
        return _ar._error_response('삭제 실패', 500)
    return jsonify({'ok': True})


# ── 감사 로그 (F4-25) ────────────────────────────────────


@auth_bp.route('/api/admin/audit-logs', methods=['GET'])
@require_auth
def get_audit_logs():
    """감사 로그 조회 (관리자 전용)"""
    from services.data.audit_log_service import audit_log_service

    if not _ar.is_admin(g.user_id):
        return _ar._error_response('관리자 권한이 필요합니다.', 403)

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


# ── 활동 피드 (F5-24) ────────────────────────────────────


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


# ── 사용량 알림 (F4-09) ──────────────────────────────────


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

    data = _ar._get_json_data()
    used = data.get('used')
    total = data.get('total')
    if used is None or total is None:
        return _ar._error_response('used와 total 값이 필요합니다.')

    try:
        used = int(used)
        total = int(total)
    except (ValueError, TypeError):
        return _ar._error_response('used와 total은 정수여야 합니다.')

    new_alerts = usage_alert_service.check_usage(g.user_id, used, total)
    return jsonify({'new_alerts': new_alerts})


@auth_bp.route('/api/user/usage-alerts/reset', methods=['POST'])
@require_auth
def reset_usage_alerts():
    """사용량 알림 초기화 (월간 리셋)"""
    from services.usage.usage_alert_service import usage_alert_service
    usage_alert_service.reset_alerts(g.user_id)
    return _ar._success_response({'message': '사용량 알림이 초기화되었습니다.'})


# ── SSO (SAML/OIDC) (F4-24) ──────────────────────────────


@auth_bp.route('/api/sso/<workspace_id>/config', methods=['POST'])
@require_auth
def sso_configure(workspace_id):
    """SSO 프로바이더 설정"""
    from services.auth.sso_service import sso_service
    data = _ar._get_json_data()
    provider = data.get('provider', '')
    config = data.get('config', {})
    if not provider:
        return _ar._error_response('provider는 필수입니다.')
    result = sso_service.configure_sso(workspace_id, provider, config)
    if 'error' in result:
        return _ar._error_response(result['error'])
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
        return _ar._error_response(result['error'])
    return jsonify(result)


@auth_bp.route('/api/sso/<workspace_id>/callback', methods=['POST'])
def sso_callback(workspace_id):
    """SSO 콜백 검증 + 세션 생성"""
    from services.auth.sso_service import sso_service
    data = _ar._get_json_data()
    result = sso_service.validate_callback(workspace_id, data)
    if 'error' in result:
        return _ar._error_response(result['error'])
    return jsonify(result)


@auth_bp.route('/api/sso/<workspace_id>/disable', methods=['POST'])
@require_auth
def sso_disable(workspace_id):
    """SSO 비활성화"""
    from services.auth.sso_service import sso_service
    result = sso_service.disable_sso(workspace_id)
    if 'error' in result:
        return _ar._error_response(result['error'])
    return jsonify(result)
