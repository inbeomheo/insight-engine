"""기타 사용자 영역 — 스타일 메모리, 스니펫, 활동 피드 라우트.

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
