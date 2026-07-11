"""
유틸리티 라우트 — 헬스체크, 프로바이더, 캐시, 스타일 추천/생성, 웹훅, 재생목록

공용 상태/카운터는 routes/utility/_state.py로 이동되어 순환 import를 제거함.
테스트 호환성을 위해 본 모듈에서 그대로 re-export 한다.
"""
import json
import os

from flask import request, jsonify, current_app

from routes.blog_routes import blog_bp, _extract_client_id, DEFAULT_MODEL
from services.core import ai_service, content_service
from services.core.content_service import clear_cache
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
def api_clear_cache():
    """캐시를 삭제합니다. video_id 파라미터가 있으면 해당 영상만, 없으면 전체 삭제."""
    data = request.get_json(silent=True) or {}
    video_id = data.get('videoId')

    # URL에서 video_id 추출 (URL이 전달된 경우)
    url = data.get('url')
    if url and not video_id:
        video_id = content_service.get_video_id(url)

    try:
        deleted = clear_cache(video_id)
    except ValueError as e:
        return api_error(sanitize_error_for_client(f'[입력 오류] 잘못된 videoId 형식: {e}'), 400)

    if video_id:
        return jsonify({
            'success': True,
            'message': f'영상 {video_id}의 캐시가 삭제되었습니다.',
            'deleted': deleted
        })
    return jsonify({
        'success': True,
        'message': '전체 캐시가 삭제되었습니다.',
        'deleted': deleted
    })


# ============================================================
# 분리된 utility 서브 라우트 — 부수효과 import (blog_bp에 라우트 등록)
# - routes/utility/operations.py: 헬스/heartbeat/providers
# - routes/utility/feedback_quality.py: 캐시/피드백/팩트체크/SEO
# - routes/utility/external.py: 웹훅/재생목록/추천소스/RSS
# ============================================================
from routes import utility as _utility_subroutes  # noqa: E402,F401
