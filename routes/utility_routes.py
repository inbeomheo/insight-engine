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
from utils.responses import handle_error, sanitize_error_for_client

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
        return jsonify({'error': f'[입력 오류] 잘못된 videoId 형식: {e}'}), 400

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
# - routes/utility/operations.py: 헬스/heartbeat/providers/ollama
# - routes/utility/feedback_quality.py: 캐시/피드백/팩트체크/SEO
# - routes/utility/generation.py: AI 스타일 추천/생성
# - routes/utility/external.py: 웹훅/재생목록/추천소스/RSS
# - routes/utility/content_evaluation.py: 콘텐츠 평가 (등급/헤드라인 등)
# - routes/utility/text_structure.py: 문장/단락/연결어/구조 분석
# - routes/utility/text_quality.py: 표현 품질 (군더더기/어휘/톤)
# - routes/utility/seo_aeo.py: SEO/AEO/EEAT/구조화 데이터
# - routes/utility/content_meta.py: 메타데이터/페르소나/투명성/위험
# ============================================================
from routes import utility as _utility_subroutes  # noqa: E402,F401
