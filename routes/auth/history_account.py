"""히스토리 + 계정/프로필 관리 라우트.

auth_routes.py에서 분리됨. supabase 함수는 `routes.auth_routes` namespace를
경유해 호출해 patch 호환성을 유지한다 (`_ar.get_histories(...)` 형식).
"""
from flask import g, jsonify, request

from routes import auth_routes as _ar
from routes.auth_routes import auth_bp
from src.contexts.identity.interface.auth_decorators import require_auth


# ── 히스토리 ────────────────────────────────────────────


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

    data = _ar.get_histories(g.user_id, page, per_page)
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
        'is_admin': _ar.is_admin(g.user_id)
    })


@auth_bp.route('/api/user/history/<report_id>', methods=['DELETE'])
@require_auth
def delete_user_history(report_id):
    """사용자 히스토리 삭제 (클라우드)

    RLS + user_id 매칭으로 본인 데이터만 삭제 가능.
    """
    if not report_id:
        return _ar._error_response('report_id가 필요합니다.')

    if _ar.delete_history(g.user_id, report_id):
        return _ar._success_response()
    return _ar._error_response('삭제에 실패했습니다.', 500)


@auth_bp.route('/api/user/history/<report_id>/favorite', methods=['POST'])
@require_auth
def toggle_history_favorite(report_id):
    """히스토리 즐겨찾기 토글"""
    if not report_id:
        return _ar._error_response('report_id가 필요합니다.')

    result = _ar.toggle_favorite(g.user_id, report_id)
    if result.get('success'):
        return jsonify({'is_favorite': result['is_favorite']})
    return _ar._safe_service_error_response(
        result.get('error'),
        '[서버 오류] 즐겨찾기 변경에 실패했습니다.',
        500
    )


@auth_bp.route('/api/user/history/<report_id>', methods=['PUT'])
@require_auth
def update_user_history(report_id):
    """히스토리 콘텐츠 업데이트 (인라인 편집용)"""
    if not report_id:
        return _ar._error_response('report_id가 필요합니다.')

    data = _ar._get_json_data()
    allowed_fields = {'content', 'html', 'title'}
    updates = {k: v for k, v in data.items() if k in allowed_fields}

    if not updates:
        return _ar._error_response('업데이트할 필드가 없습니다.')

    if _ar.update_history(g.user_id, report_id, updates):
        return _ar._success_response()
    return _ar._error_response('업데이트에 실패했습니다.', 500)


# ── 프로필/비밀번호/계정 삭제 ─────────────────────────────


@auth_bp.route('/api/user/profile', methods=['PUT'])
@require_auth
def update_profile():
    """프로필(닉네임) 업데이트"""
    data = _ar._get_json_data()
    display_name = data.get('display_name', '').strip()
    if not display_name:
        return _ar._error_response('닉네임을 입력해주세요.')
    if len(display_name) > 50:
        return _ar._error_response('닉네임은 50자 이내로 입력해주세요.')

    result = _ar.update_user_profile(g.user_id, display_name)
    if result['success']:
        return _ar._success_response({'user': result.get('user')})
    return _ar._safe_service_error_response(
        result.get('error'),
        '[서버 오류] 프로필 업데이트에 실패했습니다.',
        500
    )


@auth_bp.route('/api/user/password', methods=['PUT'])
@require_auth
def change_password():
    """비밀번호 변경"""
    data = _ar._get_json_data()
    new_password = data.get('new_password', '')
    if len(new_password) < 6:
        return _ar._error_response('비밀번호는 6자 이상이어야 합니다.')

    result = _ar.update_user_password(g.user_id, new_password)
    if result['success']:
        return _ar._success_response()
    return _ar._safe_service_error_response(
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
    if _ar.delete_user_account(g.user_id):
        return _ar._success_response({'message': '계정이 삭제되었습니다.'})
    return _ar._error_response('계정 삭제에 실패했습니다.', 500)
