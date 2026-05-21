"""콘텐츠 관리 & 라이브러리 라우트 (Phase 8)

F8-01 ~ F8-25 기능에 대한 REST API 엔드포인트.
"""
import html
import re
from flask import Blueprint, request, jsonify, Response, current_app
from utils.responses import sanitize_error_for_client, clamp_query_int

from services.data.supabase_service import require_auth
from services.data import content_library_service
from services.data import archive_service
from services.data import lock_service
from services.data import expiry_service
from services.media import media_library_service
from services.data import custom_field_service
from services.seo import link_manager_service
from services.seo import seo_checklist_service
from services.platform import share_service
from services.content import comment_service
from services.data import workflow_service
from services.data import rbac_service
from services.data import backup_service
from services.data import data_migration_service
from services.data import trash_service

content_mgmt_bp = Blueprint('content_mgmt', __name__, url_prefix='/api/content')


# ─── 헬퍼 ──────────────────────────────────────────────────────────

def _json(data, status=200):
    return jsonify(data), status


def _err(msg, status=400):
    return jsonify({'error': msg}), status


def _get_json():
    return request.get_json(silent=True) or {}


def _safe_route_error(message, fallback_message):
    safe_message = sanitize_error_for_client(str(message or ''))
    if safe_message.startswith('[서버 오류]'):
        return fallback_message
    return safe_message


# ══════════════════════════════════════════════════════════════════
# F8-01 콘텐츠 라이브러리 CRUD
# ══════════════════════════════════════════════════════════════════

@content_mgmt_bp.route('', methods=['POST'])
@require_auth
def create_content():
    """콘텐츠 라이브러리에 항목 추가."""
    data = _get_json()
    title = (data.get('title') or '').strip()
    if not title:
        return _err('title 필드가 필요합니다.')
    item = content_library_service.create_item(
        title=title,
        content=data.get('content', ''),
        style=data.get('style', ''),
        tags=data.get('tags', []),
        url=data.get('url', ''),
        user_id=data.get('user_id', ''),
        workspace_id=data.get('workspace_id', ''),
        folder_id=data.get('folder_id', ''),
        meta=data.get('meta', {}),
    )
    return _json(item, 201)


@content_mgmt_bp.route('', methods=['GET'])
@require_auth
def list_contents():
    """콘텐츠 라이브러리 검색·필터."""
    args = request.args
    result = content_library_service.search_items(
        query=args.get('q', ''),
        style=args.get('style', ''),
        tags=args.getlist('tag'),
        status=args.get('status', ''),
        workspace_id=args.get('workspace_id', ''),
        user_id=args.get('user_id', ''),
        folder_id=args.get('folder_id', ''),
        is_pinned=_bool_arg(args.get('is_pinned')),
        is_archived=_bool_arg(args.get('is_archived')),
        page=clamp_query_int(args.get('page'), default=1, min_val=1, max_val=10000),
        per_page=clamp_query_int(args.get('per_page'), default=20, min_val=1, max_val=100),
        sort_by=args.get('sort_by', 'created_at'),
        sort_desc=args.get('sort_desc', 'true').lower() != 'false',
    )
    return _json(result)


@content_mgmt_bp.route('/<item_id>', methods=['GET'])
@require_auth
def get_content(item_id):
    """단일 콘텐츠 조회."""
    item = content_library_service.get_item(item_id)
    if not item:
        return _err('항목을 찾을 수 없습니다.', 404)
    content_library_service.increment_view(item_id)
    return _json(item)


@content_mgmt_bp.route('/<item_id>', methods=['PATCH'])
@require_auth
def update_content(item_id):
    """콘텐츠 업데이트."""
    data = _get_json()
    item = content_library_service.update_item(item_id, **data)
    if not item:
        return _err('항목을 찾을 수 없습니다.', 404)
    return _json(item)


@content_mgmt_bp.route('/<item_id>', methods=['DELETE'])
@require_auth
def delete_content(item_id):
    """콘텐츠 소프트 삭제 (휴지통으로 이동)."""
    success = trash_service.move_to_trash(item_id)
    if not success:
        return _err('항목을 찾을 수 없습니다.', 404)
    return _json({'deleted': True})


# ══════════════════════════════════════════════════════════════════
# F8-05 일괄 작업 (Bulk Actions)
# ══════════════════════════════════════════════════════════════════

@content_mgmt_bp.route('/bulk', methods=['POST'])
@require_auth
def bulk_action():
    """여러 항목에 일괄 작업을 수행합니다.

    action: 'delete' | 'archive' | 'restore' | 'tag' | 'status_change'
    item_ids: 대상 ID 목록
    """
    data = _get_json()
    action = data.get('action', '')
    item_ids: list[str] = data.get('item_ids', [])
    if not item_ids:
        return _err('item_ids가 필요합니다.')

    results = {'success': [], 'failed': []}

    for item_id in item_ids:
        try:
            if action == 'delete':
                if trash_service.move_to_trash(item_id):
                    results['success'].append(item_id)
                else:
                    results['failed'].append(item_id)

            elif action == 'archive':
                item = archive_service.archive_item(item_id)
                (results['success'] if item else results['failed']).append(item_id)

            elif action == 'restore':
                item = archive_service.restore_item(item_id)
                (results['success'] if item else results['failed']).append(item_id)

            elif action == 'tag':
                tags = data.get('tags', [])
                item = content_library_service.get_item(item_id)
                if item:
                    existing = item.get('tags', [])
                    merged = list(set(existing + tags))
                    content_library_service.update_item(item_id, tags=merged)
                    results['success'].append(item_id)
                else:
                    results['failed'].append(item_id)

            elif action == 'status_change':
                new_status = data.get('status', '')
                item = content_library_service.update_item(item_id, status=new_status)
                (results['success'] if item else results['failed']).append(item_id)

            else:
                results['failed'].append(item_id)

        except Exception:
            results['failed'].append(item_id)

    return _json({
        'action': action,
        'success_count': len(results['success']),
        'failed_count': len(results['failed']),
        **results,
    })


# ══════════════════════════════════════════════════════════════════
# F8-06 콘텐츠 복제
# ══════════════════════════════════════════════════════════════════

@content_mgmt_bp.route('/<item_id>/clone', methods=['POST'])
@require_auth
def clone_content(item_id):
    """콘텐츠를 복제합니다."""
    original = content_library_service.get_item(item_id)
    if not original:
        return _err('항목을 찾을 수 없습니다.', 404)

    data = _get_json()
    cloned = content_library_service.create_item(
        title=data.get('title') or f"[복사] {original['title']}",
        content=original['content'],
        style=original['style'],
        tags=list(original.get('tags', [])),
        url=original.get('url', ''),
        user_id=data.get('user_id', original.get('user_id', '')),
        workspace_id=data.get('workspace_id', original.get('workspace_id', '')),
        folder_id=data.get('folder_id', original.get('folder_id', '')),
        meta={**original.get('meta', {}), 'cloned_from': item_id},
    )
    return _json(cloned, 201)


# ══════════════════════════════════════════════════════════════════
# F8-07 아카이브
# ══════════════════════════════════════════════════════════════════

@content_mgmt_bp.route('/<item_id>/archive', methods=['POST'])
@require_auth
def archive_content(item_id):
    """콘텐츠를 아카이브합니다."""
    data = _get_json()
    item = archive_service.archive_item(item_id, data.get('user_id', ''), data.get('reason', ''))
    if not item:
        return _err('항목을 찾을 수 없습니다.', 404)
    return _json(item)


@content_mgmt_bp.route('/<item_id>/unarchive', methods=['POST'])
@require_auth
def unarchive_content(item_id):
    """아카이브를 해제합니다."""
    data = _get_json()
    item = archive_service.restore_item(item_id, data.get('user_id', ''))
    if not item:
        return _err('항목을 찾을 수 없습니다.', 404)
    return _json(item)


@content_mgmt_bp.route('/archive', methods=['GET'])
@require_auth
def list_archived():
    """아카이브 목록 조회."""
    args = request.args
    result = archive_service.list_archived(
        workspace_id=args.get('workspace_id', ''),
        user_id=args.get('user_id', ''),
        page=clamp_query_int(args.get('page'), default=1, min_val=1, max_val=10000),
        per_page=clamp_query_int(args.get('per_page'), default=20, min_val=1, max_val=100),
    )
    return _json(result)


# ══════════════════════════════════════════════════════════════════
# F8-08 콘텐츠 잠금
# ══════════════════════════════════════════════════════════════════

@content_mgmt_bp.route('/<item_id>/lock', methods=['POST'])
@require_auth
def acquire_lock(item_id):
    """편집 잠금을 획득합니다."""
    data = _get_json()
    result = lock_service.acquire_lock(
        item_id,
        user_id=data.get('user_id', ''),
        user_name=data.get('user_name', ''),
        ttl=clamp_query_int(data.get('ttl'), default=lock_service.DEFAULT_TTL, min_val=10, max_val=86400),
    )
    return _json(result, 200 if result['success'] else 423)


@content_mgmt_bp.route('/<item_id>/lock', methods=['DELETE'])
@require_auth
def release_lock(item_id):
    """편집 잠금을 해제합니다."""
    data = _get_json()
    success = lock_service.release_lock(item_id, data.get('user_id', ''))
    return _json({'released': success})


@content_mgmt_bp.route('/<item_id>/lock/heartbeat', methods=['POST'])
@require_auth
def lock_heartbeat(item_id):
    """잠금 TTL을 갱신합니다."""
    data = _get_json()
    success = lock_service.heartbeat(item_id, data.get('user_id', ''))
    return _json({'refreshed': success})


@content_mgmt_bp.route('/<item_id>/lock', methods=['GET'])
@require_auth
def get_lock_status(item_id):
    """잠금 상태를 조회합니다."""
    lock = lock_service.get_lock(item_id)
    return _json({'lock': lock, 'is_locked': lock is not None})


# ══════════════════════════════════════════════════════════════════
# F8-09 만료 관리
# ══════════════════════════════════════════════════════════════════

@content_mgmt_bp.route('/<item_id>/expiry', methods=['POST'])
@require_auth
def set_expiry(item_id):
    """만료 규칙을 설정합니다."""
    data = _get_json()
    expires_at = data.get('expires_at')
    if not expires_at:
        return _err('expires_at (Unix timestamp)이 필요합니다.')
    rule = expiry_service.set_expiry(
        item_id,
        expires_at=float(expires_at),
        action=data.get('action', 'archive'),
        notify_before_days=clamp_query_int(data.get('notify_before_days'), default=3, min_val=0, max_val=365),
    )
    return _json(rule)


@content_mgmt_bp.route('/<item_id>/expiry', methods=['DELETE'])
@require_auth
def remove_expiry(item_id):
    """만료 규칙을 제거합니다."""
    success = expiry_service.remove_expiry(item_id)
    return _json({'removed': success})


@content_mgmt_bp.route('/<item_id>/expiry', methods=['GET'])
@require_auth
def get_expiry(item_id):
    """만료 규칙을 조회합니다."""
    rule = expiry_service.get_expiry(item_id)
    return _json({'expiry': rule})


# ══════════════════════════════════════════════════════════════════
# F8-10 미디어 라이브러리
# ══════════════════════════════════════════════════════════════════

@content_mgmt_bp.route('/media', methods=['POST'])
@require_auth
def register_media():
    """미디어 항목을 등록합니다."""
    data = _get_json()
    if not data.get('name') or not data.get('url'):
        return _err('name, url 필드가 필요합니다.')
    item = media_library_service.register_media(
        name=data['name'],
        url=data['url'],
        media_type=data.get('media_type', 'image'),
        size_bytes=clamp_query_int(data.get('size_bytes'), default=0, min_val=0, max_val=2_147_483_647),
        mime_type=data.get('mime_type', ''),
        user_id=data.get('user_id', ''),
        workspace_id=data.get('workspace_id', ''),
        tags=data.get('tags', []),
        meta=data.get('meta', {}),
    )
    return _json(item, 201)


@content_mgmt_bp.route('/media', methods=['GET'])
@require_auth
def list_media():
    """미디어 목록을 조회합니다."""
    args = request.args
    result = media_library_service.list_media(
        workspace_id=args.get('workspace_id', ''),
        user_id=args.get('user_id', ''),
        media_type=args.get('media_type', ''),
        tags=args.getlist('tag'),
        query=args.get('q', ''),
        page=clamp_query_int(args.get('page'), default=1, min_val=1, max_val=10000),
        per_page=clamp_query_int(args.get('per_page'), default=30, min_val=1, max_val=100),
    )
    return _json(result)


@content_mgmt_bp.route('/media/<media_id>', methods=['DELETE'])
@require_auth
def delete_media(media_id):
    """미디어 항목을 삭제합니다."""
    success = media_library_service.delete_media(media_id)
    if not success:
        return _err('미디어를 찾을 수 없습니다.', 404)
    return _json({'deleted': True})


@content_mgmt_bp.route('/media/stats', methods=['GET'])
@require_auth
def media_stats():
    """미디어 스토리지 통계."""
    stats = media_library_service.get_storage_stats(request.args.get('workspace_id', ''))
    return _json(stats)


# ══════════════════════════════════════════════════════════════════
# F8-11 커스텀 필드
# ══════════════════════════════════════════════════════════════════

@content_mgmt_bp.route('/fields', methods=['POST'])
@require_auth
def create_field():
    """커스텀 필드 스키마를 생성합니다."""
    data = _get_json()
    if not data.get('workspace_id') or not data.get('name'):
        return _err('workspace_id, name 필드가 필요합니다.')
    schema = custom_field_service.create_field_schema(
        workspace_id=data['workspace_id'],
        name=data['name'],
        field_type=data.get('field_type', 'text'),
        required=bool(data.get('required', False)),
        options=data.get('options', []),
        default_value=data.get('default_value'),
        description=data.get('description', ''),
    )
    return _json(schema, 201)


@content_mgmt_bp.route('/fields', methods=['GET'])
@require_auth
def list_fields():
    """워크스페이스의 커스텀 필드 목록."""
    workspace_id = request.args.get('workspace_id', '')
    if not workspace_id:
        return _err('workspace_id가 필요합니다.')
    schemas = custom_field_service.list_schemas(workspace_id)
    return _json({'schemas': schemas})


@content_mgmt_bp.route('/<item_id>/fields', methods=['GET'])
@require_auth
def get_item_fields(item_id):
    """콘텐츠 항목의 커스텀 필드 값 조회."""
    values = custom_field_service.get_field_values(item_id)
    return _json({'item_id': item_id, 'values': values})


@content_mgmt_bp.route('/<item_id>/fields/<field_id>', methods=['PUT'])
@require_auth
def set_item_field(item_id, field_id):
    """콘텐츠 항목의 커스텀 필드 값 설정."""
    data = _get_json()
    result = custom_field_service.set_field_value(item_id, field_id, data.get('value'))
    return _json(result)


# ══════════════════════════════════════════════════════════════════
# F8-12 링크 관리
# ══════════════════════════════════════════════════════════════════

@content_mgmt_bp.route('/<item_id>/links', methods=['POST'])
@require_auth
def add_link(item_id):
    """링크를 추가합니다."""
    data = _get_json()
    if not data.get('target'):
        return _err('target이 필요합니다.')
    link = link_manager_service.add_link(
        source_id=item_id,
        target=data['target'],
        link_type=data.get('link_type', 'internal'),
        label=data.get('label', ''),
        user_id=data.get('user_id', ''),
    )
    return _json(link, 201)


@content_mgmt_bp.route('/<item_id>/links', methods=['GET'])
@require_auth
def get_links(item_id):
    """콘텐츠의 링크와 역링크를 반환합니다."""
    links = link_manager_service.get_links_from(item_id)
    backlinks = link_manager_service.get_backlinks(item_id)
    return _json({'links': links, 'backlinks': backlinks})


@content_mgmt_bp.route('/links/<link_id>', methods=['DELETE'])
@require_auth
def remove_link(link_id):
    """링크를 삭제합니다."""
    success = link_manager_service.remove_link(link_id)
    return _json({'removed': success})


# ══════════════════════════════════════════════════════════════════
# F8-13 SEO 체크리스트
# ══════════════════════════════════════════════════════════════════

@content_mgmt_bp.route('/seo-check', methods=['POST'])
@require_auth
def seo_check():
    """SEO 체크리스트를 실행합니다."""
    data = _get_json()
    title = data.get('title', '')
    content = data.get('content', '')
    if not title and not content:
        return _err('title 또는 content가 필요합니다.')
    result = seo_checklist_service.run_checklist(title, content, data.get('meta'))
    return _json(result)


@content_mgmt_bp.route('/<item_id>/seo-check', methods=['GET'])
@require_auth
def seo_check_item(item_id):
    """저장된 콘텐츠에 SEO 체크리스트를 실행합니다."""
    item = content_library_service.get_item(item_id)
    if not item:
        return _err('항목을 찾을 수 없습니다.', 404)
    result = seo_checklist_service.run_checklist(
        item.get('title', ''),
        item.get('content', ''),
        item.get('meta', {}).get('seo'),
    )
    return _json(result)


# ══════════════════════════════════════════════════════════════════
# F8-14 콘텐츠 임베드
# ══════════════════════════════════════════════════════════════════

@content_mgmt_bp.route('/embed/<item_id>', methods=['GET'])
@require_auth
def embed_content(item_id):
    """임베드 가능한 HTML 스니펫을 반환합니다."""
    item = content_library_service.get_item(item_id)
    if not item:
        return _err('항목을 찾을 수 없습니다.', 404)

    title = html.escape(item.get('title', ''))
    # content를 마크다운 → HTML 변환 (간단 버전)
    content_html = item.get('content', '').replace('\n', '<br>')
    # XSS 방지: <script> 태그 및 인라인 이벤트 핸들러 제거
    content_html = re.sub(r'<script[\s\S]*?</script>', '', content_html, flags=re.IGNORECASE)
    content_html = re.sub(r'\s+on\w+\s*=\s*["\'][^"\']*["\']', '', content_html, flags=re.IGNORECASE)
    embed_html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  body {{ font-family: sans-serif; margin: 1rem; color: #333; }}
  h1 {{ font-size: 1.4rem; }}
  p {{ line-height: 1.6; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div>{content_html}</div>
</body>
</html>
""".strip()
    return Response(embed_html, content_type='text/html; charset=utf-8')


# ══════════════════════════════════════════════════════════════════
# F8-15 공유 링크
# ══════════════════════════════════════════════════════════════════

@content_mgmt_bp.route('/<item_id>/share', methods=['POST'])
@require_auth
def create_share(item_id):
    """공유 링크를 생성합니다."""
    data = _get_json()
    link = share_service.create_share_link(
        item_id=item_id,
        user_id=data.get('user_id', ''),
        expires_in_hours=clamp_query_int(data.get('expires_in_hours'), default=72, min_val=1, max_val=8760),
        password=data.get('password', ''),
        allow_download=bool(data.get('allow_download', False)),
    )
    return _json({'token': link['token'], 'expires_at': link.get('expires_at')}, 201)


@content_mgmt_bp.route('/share/<token>', methods=['GET'])
@require_auth
def access_share(token):
    """공유 링크로 콘텐츠에 접근합니다."""
    password = request.args.get('password', '')
    result = share_service.verify_and_access(token, password)
    if not result['success']:
        return _err(result['reason'], 403)

    item = content_library_service.get_item(result['item_id'])
    if not item:
        return _err('항목을 찾을 수 없습니다.', 404)

    return _json({'item': item, 'allow_download': result.get('allow_download', False)})


@content_mgmt_bp.route('/share/<token>', methods=['DELETE'])
@require_auth
def revoke_share(token):
    """공유 링크를 취소합니다."""
    data = _get_json()
    success = share_service.revoke_share(token, data.get('user_id', ''))
    return _json({'revoked': success})


# ══════════════════════════════════════════════════════════════════
# F8-16 댓글
# ══════════════════════════════════════════════════════════════════

@content_mgmt_bp.route('/<item_id>/comments', methods=['POST'])
@require_auth
def add_comment(item_id):
    """댓글을 추가합니다."""
    data = _get_json()
    if not data.get('user_id') or not data.get('text'):
        return _err('user_id, text 필드가 필요합니다.')
    c = comment_service.add_comment(
        item_id=item_id,
        user_id=data['user_id'],
        user_name=data.get('user_name', ''),
        text=data['text'],
        parent_id=data.get('parent_id', ''),
        selection=data.get('selection', ''),
    )
    return _json(c, 201)


@content_mgmt_bp.route('/<item_id>/comments', methods=['GET'])
@require_auth
def list_comments(item_id):
    """댓글 목록 조회."""
    include_resolved = request.args.get('include_resolved', 'true').lower() != 'false'
    parent_id = request.args.get('parent_id')
    comments = comment_service.list_comments(item_id, include_resolved, parent_id)
    return _json({'comments': comments, 'count': len(comments)})


@content_mgmt_bp.route('/comments/<comment_id>', methods=['PATCH'])
@require_auth
def update_comment(comment_id):
    """댓글 수정."""
    data = _get_json()
    c = comment_service.update_comment(comment_id, data.get('user_id', ''), data.get('text', ''))
    if not c:
        return _err('댓글을 찾을 수 없거나 권한이 없습니다.', 404)
    return _json(c)


@content_mgmt_bp.route('/comments/<comment_id>', methods=['DELETE'])
@require_auth
def delete_comment(comment_id):
    """댓글 삭제."""
    data = _get_json()
    success = comment_service.delete_comment(comment_id, data.get('user_id', ''))
    return _json({'deleted': success})


@content_mgmt_bp.route('/comments/<comment_id>/resolve', methods=['POST'])
@require_auth
def resolve_comment(comment_id):
    """댓글 해결 처리."""
    data = _get_json()
    c = comment_service.resolve_comment(comment_id, data.get('user_id', ''))
    if not c:
        return _err('댓글을 찾을 수 없습니다.', 404)
    return _json(c)


@content_mgmt_bp.route('/comments/<comment_id>/react', methods=['POST'])
@require_auth
def react_comment(comment_id):
    """댓글에 이모지 반응을 추가/토글합니다."""
    data = _get_json()
    c = comment_service.add_reaction(comment_id, data.get('user_id', ''), data.get('emoji', '👍'))
    if not c:
        return _err('댓글을 찾을 수 없습니다.', 404)
    return _json(c)


# ══════════════════════════════════════════════════════════════════
# F8-17 워크플로우 자동화
# ══════════════════════════════════════════════════════════════════

@content_mgmt_bp.route('/workflows', methods=['POST'])
@require_auth
def create_workflow():
    """워크플로우를 생성합니다."""
    data = _get_json()
    try:
        wf = workflow_service.create_workflow(
            name=data.get('name', ''),
            workspace_id=data.get('workspace_id', ''),
            trigger=data.get('trigger', ''),
            trigger_conditions=data.get('trigger_conditions', {}),
            actions=data.get('actions', []),
            is_enabled=bool(data.get('is_enabled', True)),
            user_id=data.get('user_id', ''),
        )
        return _json(wf, 201)
    except ValueError as e:
        return _err(
            _safe_route_error(
                e,
                '[입력 오류] 워크플로우 설정을 확인해주세요.'
            )
        )


@content_mgmt_bp.route('/workflows', methods=['GET'])
@require_auth
def list_workflows():
    """워크플로우 목록 조회."""
    workspace_id = request.args.get('workspace_id', '')
    wfs = workflow_service.list_workflows(workspace_id)
    return _json({'workflows': wfs})


@content_mgmt_bp.route('/workflows/<wf_id>', methods=['PATCH'])
@require_auth
def update_workflow(wf_id):
    """워크플로우 업데이트."""
    data = _get_json()
    wf = workflow_service.update_workflow(wf_id, **data)
    if not wf:
        return _err('워크플로우를 찾을 수 없습니다.', 404)
    return _json(wf)


@content_mgmt_bp.route('/workflows/<wf_id>', methods=['DELETE'])
@require_auth
def delete_workflow(wf_id):
    """워크플로우 삭제."""
    success = workflow_service.delete_workflow(wf_id)
    return _json({'deleted': success})


@content_mgmt_bp.route('/workflows/fire', methods=['POST'])
@require_auth
def fire_trigger():
    """워크플로우 트리거를 수동 발동합니다."""
    data = _get_json()
    results = workflow_service.fire_trigger(
        trigger=data.get('trigger', ''),
        item_id=data.get('item_id', ''),
        workspace_id=data.get('workspace_id', ''),
        context=data.get('context', {}),
    )
    return _json({'results': results})


# ══════════════════════════════════════════════════════════════════
# F8-19 RBAC
# ══════════════════════════════════════════════════════════════════

@content_mgmt_bp.route('/roles', methods=['POST'])
@require_auth
def create_role():
    """사용자 정의 역할을 생성합니다."""
    data = _get_json()
    role = rbac_service.create_custom_role(
        workspace_id=data.get('workspace_id', ''),
        name=data.get('name', ''),
        permissions=data.get('permissions', []),
        label=data.get('label', ''),
        description=data.get('description', ''),
    )
    return _json(role, 201)


@content_mgmt_bp.route('/roles', methods=['GET'])
@require_auth
def list_roles():
    """역할 목록 조회."""
    workspace_id = request.args.get('workspace_id', '')
    roles = rbac_service.list_roles(workspace_id)
    return _json({'roles': roles})


@content_mgmt_bp.route('/roles/assign', methods=['POST'])
@require_auth
def assign_role():
    """사용자에게 역할을 할당합니다."""
    data = _get_json()
    result = rbac_service.assign_role(
        workspace_id=data.get('workspace_id', ''),
        user_id=data.get('user_id', ''),
        role=data.get('role', ''),
    )
    return _json(result)


@content_mgmt_bp.route('/roles/check', methods=['POST'])
@require_auth
def check_permission():
    """권한 보유 여부를 확인합니다."""
    data = _get_json()
    has = rbac_service.has_permission(
        workspace_id=data.get('workspace_id', ''),
        user_id=data.get('user_id', ''),
        permission=data.get('permission', ''),
    )
    return _json({'has_permission': has})


# ─── 유틸 ──────────────────────────────────────────────────────────

def _bool_arg(val: str | None) -> bool | None:
    """쿼리 파라미터를 bool 또는 None으로 변환합니다."""
    if val is None:
        return None
    return val.lower() in ('true', '1', 'yes')

# ============================================================
# 분리된 라우트 서브패키지 — 부수효과 import
# - routes/content_mgmt/backup_io.py: F8-22 백업/복원 + F8-23 가져오기/내보내기
# - routes/content_mgmt/trash_pin.py: F8-24 휴지통 + F8-25 콘텐츠 핀
# ============================================================
from routes import content_mgmt as _content_mgmt_subroutes  # noqa: E402,F401
