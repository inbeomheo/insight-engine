"""콘텐츠 워크스페이스 — 버전 히스토리, 검색, 폴더, 알림 센터, 협업 세션."""
from flask import request, jsonify, current_app

from routes.blog_routes import blog_bp
from utils.responses import api_error, clamp_query_int


# ── 버전 히스토리 (F5-04) ────────────────────────────


@blog_bp.route('/api/content/<content_id>/versions', methods=['GET'])
def list_content_versions(content_id):
    """콘텐츠의 버전 목록을 반환합니다."""
    from services.data.version_service import list_versions
    return jsonify({'versions': list_versions(content_id)})


@blog_bp.route('/api/content/<content_id>/versions', methods=['POST'])
def save_content_version(content_id):
    """콘텐츠의 새 버전을 저장합니다."""
    from services.data.version_service import save_version
    data = request.get_json(silent=True) or {}
    title = data.get('title', '')
    content = data.get('content', '')
    if not content:
        return api_error('콘텐츠가 비어 있습니다.', 400)

    try:
        version = save_version(
            content_id=content_id,
            title=title,
            content=content,
            html=data.get('html', ''),
            author_id=data.get('author_id', ''),
            note=data.get('note', ''),
        )
    except Exception as e:
        current_app.logger.error('Save content version failed: %s', e, exc_info=True)
        return api_error('[서버 오류] 버전 저장 중 문제가 발생했습니다.', 500)
    return jsonify(version), 201


@blog_bp.route('/api/content/<content_id>/versions/<version_id>', methods=['GET'])
def get_content_version(content_id, version_id):
    """특정 버전의 전체 데이터를 반환합니다."""
    from services.data.version_service import get_version
    ver = get_version(content_id, version_id)
    if not ver:
        return api_error('버전을 찾을 수 없습니다.', 404)
    return jsonify(ver)


@blog_bp.route('/api/content/<content_id>/versions/diff', methods=['GET'])
def diff_content_versions(content_id):
    """두 버전의 차이를 반환합니다."""
    from services.data.version_service import diff_versions
    a = request.args.get('a', '')
    b = request.args.get('b', '')
    if not a or not b:
        return api_error('a, b 버전 ID가 필요합니다.', 400)

    result = diff_versions(content_id, a, b)
    if not result:
        return api_error('버전을 찾을 수 없습니다.', 404)
    return jsonify(result)


@blog_bp.route('/api/content/<content_id>/versions/<version_id>/restore', methods=['POST'])
def restore_content_version(content_id, version_id):
    """특정 버전을 복원합니다."""
    from services.data.version_service import restore_version
    ver = restore_version(content_id, version_id)
    if not ver:
        return api_error('버전을 찾을 수 없습니다.', 404)
    return jsonify(ver), 201


# ── 전문 검색 (F5-09) ────────────────────────────────


@blog_bp.route('/api/search', methods=['GET'])
def search_content():
    """콘텐츠를 검색합니다."""
    from services.seo.search_service import search
    query = request.args.get('q', '')
    style = request.args.get('style', None)
    limit = clamp_query_int(request.args.get('limit'), default=20, min_val=1, max_val=50)
    offset = clamp_query_int(request.args.get('offset'), default=0, min_val=0, max_val=100000)

    result = search(query, style_filter=style, limit=limit, offset=offset)
    return jsonify(result)


# ── 폴더/카테고리 (F5-11) ────────────────────────────


@blog_bp.route('/api/folders', methods=['GET'])
def list_content_folders():
    """폴더 목록을 반환합니다."""
    from services.data.folder_service import list_folders
    parent_id = request.args.get('parent_id', None)
    return jsonify({'folders': list_folders(parent_id=parent_id)})


@blog_bp.route('/api/folders', methods=['POST'])
def create_content_folder():
    """폴더를 생성합니다."""
    from services.data.folder_service import create_folder
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    if not name:
        return api_error('폴더 이름이 필요합니다.', 400)

    folder = create_folder(name=name, parent_id=data.get('parent_id'))
    return jsonify(folder), 201


@blog_bp.route('/api/folders/<folder_id>', methods=['PUT'])
def update_content_folder(folder_id):
    """폴더를 수정합니다."""
    from services.data.folder_service import update_folder
    data = request.get_json(silent=True) or {}
    folder = update_folder(folder_id, name=data.get('name'))
    if not folder:
        return api_error('폴더를 찾을 수 없습니다.', 404)
    return jsonify(folder)


@blog_bp.route('/api/folders/<folder_id>', methods=['DELETE'])
def delete_content_folder(folder_id):
    """폴더를 삭제합니다."""
    from services.data.folder_service import delete_folder
    if not delete_folder(folder_id):
        return api_error('폴더를 찾을 수 없습니다.', 404)
    return jsonify({'success': True})


@blog_bp.route('/api/folders/<folder_id>/contents', methods=['GET'])
def list_folder_content_ids(folder_id):
    """폴더의 콘텐츠 ID 목록을 반환합니다."""
    from services.data.folder_service import list_folder_contents
    return jsonify({'content_ids': list_folder_contents(folder_id)})


# ── 알림 센터 (F5-13) ────────────────────────────────


@blog_bp.route('/api/notifications', methods=['GET'])
def get_notifications():
    """알림 목록을 반환합니다."""
    from services.data.notification_service import list_notifications
    user_id = request.args.get('user_id', 'anonymous')
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    limit = clamp_query_int(request.args.get('limit'), default=20, min_val=1, max_val=50)
    offset = clamp_query_int(request.args.get('offset'), default=0, min_val=0, max_val=100000)

    result = list_notifications(user_id, unread_only=unread_only,
                                limit=limit, offset=offset)
    return jsonify(result)


@blog_bp.route('/api/notifications/<notification_id>/read', methods=['POST'])
def mark_notification_read(notification_id):
    """알림을 읽음으로 표시합니다."""
    from services.data.notification_service import mark_read
    user_id = request.args.get('user_id', 'anonymous')
    mark_read(user_id, notification_id)
    return jsonify({'success': True})


@blog_bp.route('/api/notifications/read-all', methods=['POST'])
def mark_all_notifications_read():
    """모든 알림을 읽음으로 표시합니다."""
    from services.data.notification_service import mark_all_read
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id', 'anonymous')
    count = mark_all_read(user_id)
    return jsonify({'success': True, 'count': count})


# ── 협업 세션 (F5-02) ────────────────────────────────


@blog_bp.route('/api/collab/session', methods=['POST'])
def create_collab_session():
    """협업 세션을 생성하거나 참가합니다."""
    from services.data.collaboration_service import create_session
    data = request.get_json(silent=True) or {}
    content_id = data.get('content_id', '')
    user_id = data.get('user_id', 'anonymous')
    user_name = data.get('user_name', '')
    if not content_id:
        return api_error('content_id가 필요합니다.', 400)

    result = create_session(content_id, user_id, user_name)
    return jsonify(result)


@blog_bp.route('/api/collab/session/<session_id>', methods=['GET'])
def poll_collab_session(session_id):
    """협업 세션 상태를 폴링합니다."""
    from services.data.collaboration_service import get_session
    result = get_session(session_id)
    if not result:
        return api_error('세션을 찾을 수 없습니다.', 404)
    return jsonify(result)


@blog_bp.route('/api/collab/session/<session_id>/update', methods=['POST'])
def update_collab_content(session_id):
    """협업 콘텐츠를 업데이트합니다."""
    from services.data.collaboration_service import update_content
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id', 'anonymous')
    content = data.get('content', '')
    cursor = data.get('cursor_position', 0)

    result = update_content(session_id, user_id, content, cursor)
    if not result:
        return api_error('세션을 찾을 수 없습니다.', 404)
    return jsonify(result)


@blog_bp.route('/api/collab/session/<session_id>/heartbeat', methods=['POST'])
def collab_heartbeat(session_id):
    """협업 세션 하트비트."""
    from services.data.collaboration_service import heartbeat
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id', 'anonymous')
    cursor = data.get('cursor_position', 0)

    heartbeat(session_id, user_id, cursor)
    return jsonify({'success': True})


@blog_bp.route('/api/collab/session/<session_id>/leave', methods=['POST'])
def leave_collab_session(session_id):
    """협업 세션에서 나갑니다."""
    from services.data.collaboration_service import leave_session
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id', 'anonymous')
    leave_session(session_id, user_id)
    return jsonify({'success': True})
