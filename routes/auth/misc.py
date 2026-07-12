"""기타 사용자 영역 — 스타일 메모리, 활동 피드 라우트.

auth_routes.py에서 분리됨. namespace 경유 호출 패턴 유지.
"""
from flask import g, jsonify, request

from routes import auth_routes as _ar
from routes.auth_routes import auth_bp
from src.contexts.identity.interface.auth_decorators import require_auth


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
