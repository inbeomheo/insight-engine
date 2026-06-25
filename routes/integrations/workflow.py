"""발행 큐, 예약 발행, CMS 통합 허브 워크플로우."""
from flask import request, jsonify, current_app, g
from utils.responses import api_error

from routes.blog_routes import blog_bp
from routes.integrations._shared import sanitize_result_message
from src.contexts.identity.interface.auth_decorators import require_auth


# ── 발행 큐 (재시도 정책) ──────────────────────────────────────


@blog_bp.route('/api/publish-queue', methods=['GET'])
@require_auth
def publish_queue_list():
    """현재 사용자의 발행 큐 목록 조회"""
    from services.data.publish_queue_service import publish_queue_service

    user_id = getattr(g, 'user_id', None)
    items = publish_queue_service.get_queue_status(user_id=user_id)
    summary = publish_queue_service.get_status_summary(user_id=user_id)
    return jsonify({'items': items, 'status_summary': summary})


@blog_bp.route('/api/publish-queue', methods=['POST'])
@require_auth
def publish_queue_enqueue():
    """발행 큐에 새 항목 추가"""
    from services.data.publish_queue_service import publish_queue_service

    data = request.get_json(silent=True)
    if not data:
        return api_error('요청 데이터가 없습니다.', 400)

    content_id = data.get('content_id')
    title = data.get('title')
    content = data.get('content')
    plugin_id = data.get('plugin_id')

    if not content_id or not title or not content or not plugin_id:
        return jsonify({
            'error': 'content_id, title, content, plugin_id는 필수입니다.',
        }), 400

    user_id = getattr(g, 'user_id', None) or 'anonymous'
    item = publish_queue_service.enqueue(
        content_id=content_id,
        title=title,
        content=content,
        plugin_id=plugin_id,
        user_id=user_id,
    )
    return jsonify(item), 201


@blog_bp.route('/api/publish-queue/<item_id>/cancel', methods=['POST'])
@require_auth
def publish_queue_cancel(item_id: str):
    """큐 항목 취소"""
    from services.data.publish_queue_service import publish_queue_service

    result = publish_queue_service.cancel_item(item_id)
    status_code = 200 if result.get('success') else 400
    return jsonify(result), status_code


@blog_bp.route('/api/publish-queue/<item_id>/retry', methods=['POST'])
@require_auth
def publish_queue_retry(item_id: str):
    """실패 항목 수동 재시도"""
    from services.data.publish_queue_service import publish_queue_service

    result = publish_queue_service.retry_item(item_id)
    status_code = 200 if result.get('success') else 400
    return jsonify(result), status_code


# ── 예약 발행 ──────────────────────────────────────


@blog_bp.route('/api/schedule', methods=['POST'])
@require_auth
def schedule_create():
    """예약 발행 생성"""
    from services.data.schedule_service import schedule_service

    data = request.get_json(silent=True)
    if not data:
        return api_error('요청 데이터가 없습니다.', 400)

    title = data.get('title')
    content = data.get('content')
    html = data.get('html')
    target_plugin = data.get('target_plugin')
    scheduled_at = data.get('scheduled_at')

    if not title or not content or not target_plugin or not scheduled_at:
        return api_error('title, content, target_plugin, scheduled_at는 필수입니다.', 400)

    post = schedule_service.create(
        user_id=g.user_id,
        title=title,
        content=content,
        html=html,
        target_plugin=target_plugin,
        scheduled_at=scheduled_at,
    )
    if post is None:
        return api_error('예약 생성에 실패했습니다.', 500)

    return jsonify(post), 201


@blog_bp.route('/api/schedule', methods=['GET'])
@require_auth
def schedule_list():
    """사용자 예약 목록 조회"""
    from services.data.schedule_service import schedule_service

    posts = schedule_service.list_by_user(g.user_id)
    # next_run_at: pending 상태 중 가장 빠른 scheduled_at
    pending = [p for p in posts if p.get('status') == 'pending' and p.get('scheduled_at')]
    pending_ats = [p['scheduled_at'] for p in pending]
    next_run_at = min(pending_ats) if pending_ats else None
    return jsonify({
        'schedules': posts,
        'next_run_at': next_run_at,
        'total_count': len(posts),
        'pending_count': len(pending),
    })


@blog_bp.route('/api/schedule/<post_id>', methods=['DELETE'])
@require_auth
def schedule_delete(post_id):
    """예약 삭제"""
    from services.data.schedule_service import schedule_service

    success = schedule_service.delete(post_id, g.user_id)
    if not success:
        return api_error('삭제할 예약을 찾을 수 없습니다.', 404)

    return jsonify({'success': True})


# ── CMS 통합 허브 (F7-23) ──────────────────────────────────────


@blog_bp.route('/api/cms/publish-all', methods=['POST'])
def cms_publish_all():
    """여러 CMS에 동시에 콘텐츠를 발행합니다."""
    from services.mcp.cms_hub import cms_hub

    data = request.get_json(silent=True) or {}
    plugin_ids = data.get('plugin_ids', [])
    title = data.get('title', '')
    content = data.get('content', '')
    plugin_configs = data.get('plugin_configs', {})

    if not plugin_ids:
        return api_error('plugin_ids 목록이 필요합니다.', 400)
    if not title or not content:
        return api_error('title과 content가 필요합니다.', 400)

    try:
        result = cms_hub.publish_to_all(plugin_ids, title, content, plugin_configs)
    except Exception as e:
        current_app.logger.error('CMS publish-all failed: %s', e, exc_info=True)
        return api_error('[서버 오류] CMS 발행 중 문제가 발생했습니다.', 500)

    sanitized_results = {}
    for plugin_id, plugin_result in (result.get('results') or {}).items():
        sanitized_results[plugin_id] = sanitize_result_message(
            plugin_result,
            'message',
            '[서버 오류] CMS 발행에 실패했습니다.'
        )
    if sanitized_results:
        result = {**result, 'results': sanitized_results}

    return jsonify(result)


@blog_bp.route('/api/cms/plugins', methods=['GET'])
def cms_list_plugins():
    """CMS 허브에서 사용 가능한 플러그인 목록"""
    from services.mcp.cms_hub import cms_hub
    return jsonify({'plugins': cms_hub.get_available_plugins()})


@blog_bp.route('/api/cms/validate-config', methods=['POST'])
def cms_validate_config():
    """플러그인 설정 유효성 검사"""
    from services.mcp.cms_hub import cms_hub

    data = request.get_json(silent=True) or {}
    plugin_id = data.get('plugin_id', '')
    config = data.get('config', {})

    if not plugin_id:
        return api_error('plugin_id가 필요합니다.', 400)

    result = cms_hub.validate_plugin_config(plugin_id, config)
    return jsonify(result)
