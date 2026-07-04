"""예약 발행 워크플로우."""
from flask import request, jsonify, g
from utils.responses import api_error

from routes.blog_routes import blog_bp
from src.contexts.identity.interface.auth_decorators import require_auth


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
