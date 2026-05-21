"""관리자 라우트 — auth_routes.py에서 분리.

테스트 patch 호환성: 모든 supabase 함수는 routes.auth_routes 모듈의
namespace를 통해 호출해 `@patch('routes.auth_routes.is_admin')` 등이 그대로
작동하도록 한다.
"""
from flask import g, jsonify, request

from routes import auth_routes as _ar  # patch 호환을 위해 namespace 접근
from routes.auth_routes import auth_bp
from services.data.supabase_service import require_auth


# 관리자 권한 헬퍼는 routes/auth_routes.py에 단일 정의됨.
# `@patch('routes.auth_routes.is_admin')`이 정상 작동하도록 namespace를 통해 호출.
_require_admin = _ar._require_admin


@auth_bp.route('/api/admin/check', methods=['GET'])
@require_auth
def check_admin():
    """현재 사용자가 관리자인지 확인"""
    return jsonify({'is_admin': _ar.is_admin(g.user_id)})


@auth_bp.route('/api/admin/users', methods=['GET'])
@require_auth
def get_admin_users():
    """모든 사용자의 사용량 조회 (관리자 전용)"""
    error = _require_admin()
    if error:
        return error

    users = _ar.get_all_users_usage()
    return jsonify({'users': users})


@auth_bp.route('/api/admin/users/<user_id>/reset', methods=['POST'])
@require_auth
def admin_reset_user(user_id):
    """특정 사용자 사용량 리셋 (관리자 전용)"""
    error = _require_admin()
    if error:
        return error

    if _ar.reset_user_usage(user_id):
        return _ar._success_response({'message': f'사용자 {user_id}의 사용량이 리셋되었습니다.'})
    return _ar._error_response('리셋에 실패했습니다.', 500)


@auth_bp.route('/api/admin/stats', methods=['GET'])
@require_auth
def get_admin_stats():
    """사용량 통계 조회 (관리자 전용)"""
    error = _require_admin()
    if error:
        return error

    stats = _ar.get_usage_stats()
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

    result = _ar.get_all_contents(page, per_page, user_id)
    return jsonify(result)


@auth_bp.route('/api/admin/contents/<report_id>', methods=['GET'])
@require_auth
def get_admin_content_detail(report_id):
    """특정 콘텐츠 상세 조회 (관리자 전용)"""
    error = _require_admin()
    if error:
        return error

    content = _ar.get_content_detail(report_id)
    if not content:
        return _ar._error_response('콘텐츠를 찾을 수 없습니다.', 404)
    return jsonify(content)
