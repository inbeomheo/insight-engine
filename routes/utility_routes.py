"""
유틸리티 라우트 — 헬스체크, 프로바이더, 캐시, 스타일 추천/생성, 웹훅, 재생목록
"""
import json
import os
import threading
import time
from typing import Dict

from flask import request, jsonify, current_app

from routes.blog_routes import blog_bp, _extract_client_id, DEFAULT_MODEL
from services.core import ai_service, content_service
from services.core.content_service import clear_cache
from services.data.supabase_service import require_auth
from services.platform.webhook_service import WebhookService
from utils.responses import handle_error, sanitize_error_for_client

_CLIENT_TRACKER: Dict[str, float] = {}

# 재생목록/채널 조회 결과 캐시 (5분 TTL)
_PLAYLIST_CACHE: Dict[str, dict] = {}
_PLAYLIST_CACHE_TTL: int = 300  # 초

# 현재 처리 중인 요청 수 (active_requests 카운터)
_active_requests_counter: int = 0
_active_requests_lock = threading.Lock()

# 서버 시작 후 총 요청 수
_total_request_count: int = 0
_total_request_count_lock = threading.Lock()

# 서버 시작 후 에러 응답 수 (5xx)
_total_error_count: int = 0
_total_error_count_lock = threading.Lock()


def increment_request_count():
    """총 요청 수 1 증가."""
    global _total_request_count
    with _total_request_count_lock:
        _total_request_count += 1


def increment_error_count():
    """에러 응답 수 1 증가."""
    global _total_error_count
    with _total_error_count_lock:
        _total_error_count += 1


def get_request_count() -> int:
    """서버 시작 후 총 요청 수 반환."""
    return _total_request_count


def get_error_count() -> int:
    """서버 시작 후 에러 응답 수 반환."""
    return _total_error_count


def get_error_rate() -> float:
    """에러율 반환 (0.0~1.0). 요청이 없으면 0.0."""
    total = _total_request_count
    if total == 0:
        return 0.0
    return round(_total_error_count / total, 4)


def increment_active_requests():
    """활성 요청 수 증가."""
    global _active_requests_counter
    with _active_requests_lock:
        _active_requests_counter += 1


def decrement_active_requests():
    """활성 요청 수 감소."""
    global _active_requests_counter
    with _active_requests_lock:
        _active_requests_counter = max(0, _active_requests_counter - 1)


def get_active_requests() -> int:
    """현재 활성 요청 수 반환."""
    return _active_requests_counter


def _cleanup_stale_clients():
    """5분 이상 heartbeat 없는 클라이언트 정리."""
    now = time.time()
    stale = [cid for cid, ts in _CLIENT_TRACKER.items() if now - ts > 300]
    for cid in stale:
        del _CLIENT_TRACKER[cid]


@blog_bp.route('/api/cache', methods=['DELETE'])
def api_clear_cache():
    """캐시를 삭제합니다. video_id 파라미터가 있으면 해당 영상만, 없으면 전체 삭제."""
    data = request.get_json(silent=True) or {}
    video_id = data.get('videoId')

    # URL에서 video_id 추출 (URL이 전달된 경우)
    url = data.get('url')
    if url and not video_id:
        video_id = content_service.get_video_id(url)

    deleted = clear_cache(video_id)

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
