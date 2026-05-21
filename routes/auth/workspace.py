"""워크스페이스 CRUD + 멤버 관리 + 콘텐츠 승인 플로우 라우트.

auth_routes.py에서 분리됨. patch 호환을 위해 모든 supabase/service 호출은
`routes.auth_routes` namespace를 경유 (`_ar.workspace_service.*` 형식).
"""
from flask import g, jsonify, request

from routes import auth_routes as _ar
from routes.auth_routes import auth_bp
from services.data.supabase_service import require_auth


# ── 워크스페이스 CRUD/멤버 ─────────────────────────────


@auth_bp.route('/api/workspaces', methods=['POST'])
@require_auth
def create_workspace():
    """워크스페이스 생성"""
    error = _ar._check_supabase()
    if error:
        return error

    name = _ar._get_json_data().get('name', '').strip()
    if not name:
        return _ar._error_response('워크스페이스 이름을 입력해주세요.')

    try:
        result = _ar.workspace_service.create_workspace(name, g.user_id)
        if isinstance(result, dict) and 'error' in result:
            return _ar._safe_service_error_response(
                result['error'],
                '[서버 오류] 워크스페이스 생성에 실패했습니다.',
                500
            )
        return jsonify(result), 201
    except Exception as e:
        return _ar._exception_error_response(
            '워크스페이스 생성 오류',
            e,
            '[서버 오류] 워크스페이스 생성 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/workspaces', methods=['GET'])
@require_auth
def list_workspaces():
    """사용자 워크스페이스 목록"""
    error = _ar._check_supabase()
    if error:
        return jsonify({'workspaces': []})

    try:
        workspaces = _ar.workspace_service.list_workspaces(g.user_id)
        return jsonify({'workspaces': workspaces})
    except Exception as e:
        return _ar._exception_error_response(
            '워크스페이스 목록 조회 오류',
            e,
            '[서버 오류] 워크스페이스 목록 조회 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/workspaces/<workspace_id>/members', methods=['GET'])
@require_auth
def get_workspace_members(workspace_id):
    """워크스페이스 멤버 목록"""
    error = _ar._check_supabase()
    if error:
        return error

    try:
        # IDOR 방지: 요청자가 해당 워크스페이스 멤버인지 확인
        if not _ar.workspace_service.is_member(workspace_id, g.user_id):
            return _ar._error_response('워크스페이스에 접근할 수 없습니다.', 403)

        members = _ar.workspace_service.get_members(workspace_id)
        return jsonify({'members': members})
    except Exception as e:
        return _ar._exception_error_response(
            '워크스페이스 멤버 조회 오류',
            e,
            '[서버 오류] 워크스페이스 멤버 조회 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/workspaces/<workspace_id>/invite', methods=['POST'])
@require_auth
def invite_workspace_member(workspace_id):
    """워크스페이스 멤버 초대 (이메일로)"""
    error = _ar._check_supabase()
    if error:
        return error

    data = _ar._get_json_data()
    user_email = data.get('user_email', '').strip()
    role = data.get('role', 'editor')

    if not user_email:
        return _ar._error_response('이메일을 입력해주세요.')

    try:
        # owner 권한 확인
        ws = _ar.workspace_service.get_workspace(workspace_id)
        if not ws or ws.get('owner_id') != g.user_id:
            return _ar._error_response('워크스페이스 소유자만 초대할 수 있습니다.', 403)

        # 이메일로 사용자 ID 조회
        target_user_id = _ar.workspace_service.find_user_by_email(user_email)
        if not target_user_id:
            return _ar._error_response(f'등록되지 않은 이메일입니다: {user_email}', 404)

        result = _ar.workspace_service.invite_member(workspace_id, target_user_id, role)
        if isinstance(result, dict) and 'error' in result:
            return _ar._safe_service_error_response(
                result['error'],
                '[서버 오류] 워크스페이스 초대 처리에 실패했습니다.'
            )
        return _ar._success_response({'member': result})
    except Exception as e:
        return _ar._exception_error_response(
            '워크스페이스 초대 오류',
            e,
            '[서버 오류] 워크스페이스 초대 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/workspaces/<workspace_id>/members/<user_id>', methods=['DELETE'])
@require_auth
def remove_workspace_member(workspace_id, user_id):
    """워크스페이스 멤버 제거"""
    error = _ar._check_supabase()
    if error:
        return error

    try:
        # owner 권한 확인
        ws = _ar.workspace_service.get_workspace(workspace_id)
        if not ws or ws.get('owner_id') != g.user_id:
            return _ar._error_response('워크스페이스 소유자만 멤버를 제거할 수 있습니다.', 403)

        if _ar.workspace_service.remove_member(workspace_id, user_id):
            return _ar._success_response()
        return _ar._error_response('멤버 제거에 실패했습니다.', 500)
    except Exception as e:
        return _ar._exception_error_response(
            '워크스페이스 멤버 제거 오류',
            e,
            '[서버 오류] 멤버 제거 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/workspaces/<workspace_id>', methods=['DELETE'])
@require_auth
def delete_workspace(workspace_id):
    """워크스페이스 삭제 (owner만)"""
    error = _ar._check_supabase()
    if error:
        return error

    try:
        if _ar.workspace_service.delete_workspace(workspace_id, g.user_id):
            return _ar._success_response()
        return _ar._error_response('삭제에 실패했습니다. 소유자만 삭제할 수 있습니다.', 403)
    except Exception as e:
        return _ar._exception_error_response(
            '워크스페이스 삭제 오류',
            e,
            '[서버 오류] 워크스페이스 삭제 중 문제가 발생했습니다.'
        )


# ── 워크스페이스 콘텐츠 승인 플로우 ─────────────────────────


@auth_bp.route('/api/workspace/<workspace_id>/contents', methods=['POST'])
@require_auth
def add_workspace_content(workspace_id):
    """워크스페이스에 콘텐츠 추가 (draft 상태)"""
    error = _ar._check_supabase()
    if error:
        return error

    data = _ar._get_json_data()
    content_id = data.get('content_id', '').strip()
    title = data.get('title', '').strip()

    if not content_id or not title:
        return _ar._error_response('content_id와 title이 필요합니다.')

    try:
        result = _ar.content_approval_service.add_content(workspace_id, g.user_id, content_id, title)
        if isinstance(result, dict) and 'error' in result:
            return _ar._safe_service_error_response(
                result['error'],
                '[서버 오류] 콘텐츠 추가에 실패했습니다.'
            )
        return jsonify(result), 201
    except Exception as e:
        return _ar._exception_error_response(
            '워크스페이스 콘텐츠 추가 오류',
            e,
            '[서버 오류] 콘텐츠 추가 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/workspace/<workspace_id>/contents', methods=['GET'])
@require_auth
def get_workspace_contents(workspace_id):
    """워크스페이스 콘텐츠 목록 (상태 필터 선택)"""
    error = _ar._check_supabase()
    if error:
        return error

    try:
        # 멤버 확인
        if not _ar.workspace_service.is_member(workspace_id, g.user_id):
            return _ar._error_response('워크스페이스에 접근할 수 없습니다.', 403)

        status = request.args.get('status', None, type=str)
        contents = _ar.content_approval_service.get_workspace_contents(workspace_id, status)
        return jsonify({'contents': contents})
    except Exception as e:
        return _ar._exception_error_response(
            '워크스페이스 콘텐츠 조회 오류',
            e,
            '[서버 오류] 워크스페이스 콘텐츠 조회 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/workspace/contents/<content_id>/submit-review', methods=['POST'])
@require_auth
def submit_content_review(content_id):
    """draft → review 상태 전환"""
    error = _ar._check_supabase()
    if error:
        return error

    try:
        result = _ar.content_approval_service.submit_for_review(content_id, g.user_id)
        if isinstance(result, dict) and 'error' in result:
            return _ar._safe_service_error_response(
                result['error'],
                '[서버 오류] 검토 요청에 실패했습니다.'
            )
        return jsonify(result)
    except Exception as e:
        return _ar._exception_error_response(
            '콘텐츠 검토 요청 오류',
            e,
            '[서버 오류] 검토 요청 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/workspace/contents/<content_id>/approve', methods=['POST'])
@require_auth
def approve_content(content_id):
    """review → approved 상태 전환 (owner만)"""
    error = _ar._check_supabase()
    if error:
        return error

    try:
        result = _ar.content_approval_service.approve_content(content_id, g.user_id)
        if isinstance(result, dict) and 'error' in result:
            return _ar._safe_service_error_response(
                result['error'],
                '[서버 오류] 승인 처리에 실패했습니다.'
            )
        return jsonify(result)
    except Exception as e:
        return _ar._exception_error_response(
            '콘텐츠 승인 오류',
            e,
            '[서버 오류] 승인 처리 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/workspace/contents/<content_id>/reject', methods=['POST'])
@require_auth
def reject_content(content_id):
    """review → rejected 상태 전환 (owner만)"""
    error = _ar._check_supabase()
    if error:
        return error

    data = _ar._get_json_data()
    reason = data.get('reason', '').strip()
    if not reason:
        return _ar._error_response('반려 사유를 입력해주세요.')

    try:
        result = _ar.content_approval_service.reject_content(content_id, g.user_id, reason)
        if isinstance(result, dict) and 'error' in result:
            return _ar._safe_service_error_response(
                result['error'],
                '[서버 오류] 반려 처리에 실패했습니다.'
            )
        return jsonify(result)
    except Exception as e:
        return _ar._exception_error_response(
            '콘텐츠 반려 오류',
            e,
            '[서버 오류] 반려 처리 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/workspace/contents/<content_id>/publish', methods=['POST'])
@require_auth
def publish_content(content_id):
    """approved → published 상태 전환 (owner만)"""
    error = _ar._check_supabase()
    if error:
        return error

    try:
        result = _ar.content_approval_service.publish_content(content_id, g.user_id)
        if isinstance(result, dict) and 'error' in result:
            return _ar._safe_service_error_response(
                result['error'],
                '[서버 오류] 게시 처리에 실패했습니다.'
            )
        return jsonify(result)
    except Exception as e:
        return _ar._exception_error_response(
            '콘텐츠 게시 오류',
            e,
            '[서버 오류] 게시 처리 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/workspace/contents/<content_id>/revert-draft', methods=['POST'])
@require_auth
def revert_content_to_draft(content_id):
    """approved/rejected → draft 상태 전환 (editor 이상)"""
    error = _ar._check_supabase()
    if error:
        return error

    try:
        result = _ar.content_approval_service.revert_to_draft(content_id, g.user_id)
        if isinstance(result, dict) and 'error' in result:
            return _ar._safe_service_error_response(
                result['error'],
                '[서버 오류] 초안 복구에 실패했습니다.'
            )
        return jsonify(result)
    except Exception as e:
        return _ar._exception_error_response(
            '콘텐츠 초안 복구 오류',
            e,
            '[서버 오류] 초안 복구 중 문제가 발생했습니다.'
        )
