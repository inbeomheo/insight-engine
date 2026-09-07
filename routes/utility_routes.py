"""
유틸리티 라우트 — 헬스체크, 프로바이더, 캐시, 스타일 추천/생성, 웹훅, 재생목록

공용 상태/카운터는 routes/utility/_state.py로 이동되어 순환 import를 제거함.
테스트 호환성을 위해 본 모듈에서 그대로 re-export 한다.
"""
import json
import os

from flask import request, jsonify, current_app, g

from extensions import limiter
from routes.blog_routes import blog_bp, _extract_client_id, DEFAULT_MODEL
from services.core import ai_service, content_service
from services.core.content_service import clear_cache
from services.usage.usage_service import UsageService, is_supabase_enabled
from src.contexts.identity.interface.auth_decorators import require_auth
from services.platform.webhook_service import WebhookService
from utils.responses import api_error, handle_error, sanitize_error_for_client

# 공용 상태/카운터 re-export (기존 import 경로 호환)
from routes.utility._state import (  # noqa: F401
    _CLIENT_TRACKER,
    _PLAYLIST_CACHE,
    _PLAYLIST_CACHE_TTL,
    _active_requests_counter,
    _active_requests_lock,
    _cleanup_stale_clients,
    _total_error_count,
    _total_error_count_lock,
    _total_request_count,
    _total_request_count_lock,
    decrement_active_requests,
    get_active_requests,
    get_error_count,
    get_error_rate,
    get_request_count,
    increment_active_requests,
    increment_error_count,
    increment_request_count,
)


@blog_bp.route('/api/cache', methods=['DELETE'])
@limiter.limit("5/minute")
@require_auth
def api_clear_cache():
    """특정 영상 캐시를 삭제하거나 관리자 요청으로 전체 캐시를 삭제합니다."""
    data = request.get_json(silent=True) or {}
    video_id = data.get('videoId')
    scope = data.get('scope')

    if scope not in (None, 'all'):
        return api_error('[입력 오류] scope는 all만 허용됩니다.', 400)

    if scope == 'all':
        # 인증 백엔드가 없는 로컬 개발 모드는 기존 전체 삭제 동작을 유지합니다.
        if is_supabase_enabled() and not UsageService.is_admin_user(g.get('user_id')):
            return api_error('[권한 부족] 전체 캐시 삭제는 관리자만 가능합니다.', 403)
        deleted = clear_cache(None)
        return jsonify({
            'success': True,
            'message': '전체 캐시가 삭제되었습니다.',
            'deleted': deleted
        })

    # URL에서 video_id 추출 (URL이 전달된 경우)
    url = data.get('url')
    if url and not video_id:
        if not content_service.is_youtube_url(url):
            return api_error('[입력 오류] 유효한 YouTube URL이 필요합니다.', 400)
        video_id = content_service.get_video_id(url)

    if not video_id:
        return api_error('[입력 오류] 유효한 videoId 또는 YouTube URL이 필요합니다.', 400)

    try:
        deleted = clear_cache(video_id)
    except ValueError as e:
        return api_error(sanitize_error_for_client(f'[입력 오류] 잘못된 videoId 형식: {e}'), 400)

    return jsonify({
        'success': True,
        'message': f'영상 {video_id}의 캐시가 삭제되었습니다.',
        'deleted': deleted
    })


# ============================================================
# 분리된 utility 서브 라우트 — 부수효과 import (blog_bp에 라우트 등록)
# - routes/utility/operations.py: 헬스/heartbeat/providers
# - routes/utility/feedback_quality.py: 캐시/피드백/팩트체크/SEO
# - routes/utility/external.py: 웹훅/재생목록/추천소스/RSS
# ============================================================
from routes import utility as _utility_subroutes  # noqa: E402,F401
