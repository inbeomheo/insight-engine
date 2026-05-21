"""휴지통 + 콘텐츠 핀(고정) 라우트 (F8-24 / F8-25).

content_mgmt_routes.py에서 분리됨.
"""
from flask import request

from routes.content_mgmt._shared import _err, _get_json, _json
from routes.content_mgmt_routes import content_mgmt_bp
from services.data import content_library_service, trash_service
from services.data.supabase_service import require_auth
from utils.responses import clamp_query_int


# ══════════════════════════════════════════════════════════════════
# F8-24 휴지통
# ══════════════════════════════════════════════════════════════════

@content_mgmt_bp.route('/trash', methods=['GET'])
@require_auth
def list_trash():
    """휴지통 목록 조회."""
    args = request.args
    result = trash_service.list_trash(
        workspace_id=args.get('workspace_id', ''),
        user_id=args.get('user_id', ''),
        page=clamp_query_int(args.get('page'), default=1, min_val=1, max_val=10000),
        per_page=clamp_query_int(args.get('per_page'), default=20, min_val=1, max_val=100),
    )
    return _json(result)


@content_mgmt_bp.route('/trash/<item_id>/restore', methods=['POST'])
@require_auth
def restore_from_trash(item_id):
    """휴지통에서 복구합니다."""
    data = _get_json()
    item = trash_service.restore_from_trash(item_id, data.get('user_id', ''))
    if not item:
        return _err('휴지통에서 항목을 찾을 수 없습니다.', 404)
    return _json(item)


@content_mgmt_bp.route('/trash/<item_id>', methods=['DELETE'])
@require_auth
def permanent_delete(item_id):
    """항목을 영구 삭제합니다."""
    data = _get_json()
    success = trash_service.permanently_delete(item_id, data.get('user_id', ''))
    return _json({'deleted': success})


@content_mgmt_bp.route('/trash/empty', methods=['POST'])
@require_auth
def empty_trash():
    """휴지통을 비웁니다."""
    data = _get_json()
    count = trash_service.empty_trash(
        workspace_id=data.get('workspace_id', ''),
        user_id=data.get('user_id', ''),
    )
    return _json({'permanently_deleted': count})


# ══════════════════════════════════════════════════════════════════
# F8-25 콘텐츠 핀 (고정)
# ══════════════════════════════════════════════════════════════════

@content_mgmt_bp.route('/<item_id>/pin', methods=['POST'])
@require_auth
def pin_content(item_id):
    """콘텐츠를 고정합니다."""
    item = content_library_service.update_item(item_id, is_pinned=True)
    if not item:
        return _err('항목을 찾을 수 없습니다.', 404)
    return _json({'pinned': True, 'item': item})


@content_mgmt_bp.route('/<item_id>/pin', methods=['DELETE'])
@require_auth
def unpin_content(item_id):
    """콘텐츠 고정을 해제합니다."""
    item = content_library_service.update_item(item_id, is_pinned=False)
    if not item:
        return _err('항목을 찾을 수 없습니다.', 404)
    return _json({'pinned': False, 'item': item})


@content_mgmt_bp.route('/pinned', methods=['GET'])
@require_auth
def list_pinned():
    """고정된 콘텐츠 목록 조회."""
    args = request.args
    result = content_library_service.search_items(
        workspace_id=args.get('workspace_id', ''),
        user_id=args.get('user_id', ''),
        is_pinned=True,
        per_page=50,
    )
    return _json(result)
