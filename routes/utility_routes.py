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


# ── 파워워드 분석 ─────────────────────────────────────

@blog_bp.route('/api/power-words', methods=['POST'])
def power_words_route():
    """콘텐츠의 파워워드를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        goal = data.get('goal', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.power_word_service import analyze_power_words, suggest_power_words
        result = analyze_power_words(content)
        if goal:
            result['recommended'] = suggest_power_words(content, goal)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '파워워드 분석')


# ── 감정 톤 매핑 ─────────────────────────────────────

@blog_bp.route('/api/emotional-tone', methods=['POST'])
def emotional_tone_route():
    """콘텐츠의 감정 흐름을 매핑합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.emotional_tone_service import map_emotional_tone
        result = map_emotional_tone(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '감정 톤 매핑')


# ── 참여 점수 ─────────────────────────────────────────

@blog_bp.route('/api/engagement-score', methods=['POST'])
def engagement_score_route():
    """콘텐츠의 참여 유도력을 종합 평가합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.engagement_scorer_service import score_engagement
        result = score_engagement(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '참여 점수 분석')


# ── 중복 표현 검사 ────────────────────────────────────

@blog_bp.route('/api/check-redundancy', methods=['POST'])
def check_redundancy_route():
    """콘텐츠의 중복/반복 표현을 감지합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.redundancy_checker_service import check_redundancy
        result = check_redundancy(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '중복 표현 검사')


# ── 피동 표현 감지 ────────────────────────────────────

@blog_bp.route('/api/detect-passive', methods=['POST'])
def detect_passive_route():
    """한국어 피동 표현을 감지하고 능동 전환을 제안합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.passive_voice_service import detect_passive
        result = detect_passive(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '피동 표현 감지')


# ── 약어 추출 ─────────────────────────────────────────

@blog_bp.route('/api/extract-acronyms', methods=['POST'])
def extract_acronyms_route():
    """콘텐츠에서 약어와 전문용어를 추출합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.acronym_extractor_service import extract_acronyms
        result = extract_acronyms(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '약어 추출')


# ── FAQ 생성 ──────────────────────────────────────────

@blog_bp.route('/api/generate-faq', methods=['POST'])
def generate_faq_route():
    """콘텐츠 기반 FAQ를 자동 생성합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        max_questions = data.get('max_questions', 5)

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.content.faq_generator_service import generate_faq
        result = generate_faq(content, max_questions)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, 'FAQ 생성')


# ── 브랜드 보이스 프로파일링 ──────────────────────────

@blog_bp.route('/api/brand-voice', methods=['POST'])
def brand_voice_route():
    """콘텐츠의 브랜드 보이스(톤, 문체)를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.content.brand_voice_profiler_service import profile_brand_voice
        result = profile_brand_voice(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '브랜드 보이스 분석')


# ── 타겟 독자 페르소나 추론 ──────────────────────────

@blog_bp.route('/api/audience-persona', methods=['POST'])
def audience_persona_route():
    """콘텐츠에서 타겟 독자 페르소나를 추론합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.content.audience_persona_service import build_persona
        result = build_persona(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '독자 페르소나 추론')


# ── 시각 콘텐츠 제안 ─────────────────────────────────

@blog_bp.route('/api/suggest-visuals', methods=['POST'])
def suggest_visuals_route():
    """콘텐츠에 삽입할 시각 콘텐츠를 제안합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.media.visual_content_service import suggest_visuals
        result = suggest_visuals(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '시각 콘텐츠 제안')


# ── AI 답변 엔진 최적화 ──────────────────────────────

@blog_bp.route('/api/analyze-aeo', methods=['POST'])
def analyze_aeo_route():
    """AI 검색엔진 답변 인용 가능성을 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        target_query = data.get('target_query', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.aeo_optimizer_service import analyze_aeo
        result = analyze_aeo(content, target_query)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, 'AEO 분석')


# ── 검색 의도 분석 ──────────────────────────────────

@blog_bp.route('/api/search-intent', methods=['POST'])
def search_intent_route():
    """콘텐츠의 검색 의도 적합도를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        target_keyword = data.get('target_keyword', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.search_intent_service import analyze_search_intent
        result = analyze_search_intent(content, target_keyword)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '검색 의도 분석')


# ── 내부 링크 기회 탐지 ──────────────────────────────

@blog_bp.route('/api/internal-links', methods=['POST'])
def internal_links_route():
    """여러 콘텐츠 간 내부 링크 기회를 탐지합니다."""
    try:
        data = request.get_json(silent=True) or {}
        contents = data.get('contents', [])
        current_content = data.get('current_content', '')

        if not contents or len(contents) < 2:
            return jsonify({'error': '최소 2개 콘텐츠가 필요합니다. contents: [{id, title, content}, ...]'}), 400

        from services.seo.internal_link_service import find_link_opportunities
        result = find_link_opportunities(contents, current_content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '내부 링크 탐지')


# ── 독창성 검사 ──────────────────────────────────────

@blog_bp.route('/api/check-originality', methods=['POST'])
def check_originality_route():
    """콘텐츠의 독창성과 중복 리스크를 검사합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        reference_contents = data.get('reference_contents', None)

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.quality.originality_checker_service import check_originality
        result = check_originality(content, reference_contents)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '독창성 검사')


# ── 토픽 갭 분석 ────────────────────────────────────

@blog_bp.route('/api/topic-gaps', methods=['POST'])
def topic_gaps_route():
    """현재 콘텐츠와 참고 콘텐츠를 비교하여 빠진 주제를 찾습니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        reference_contents = data.get('reference_contents', None)

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.topic_gap_service import analyze_topic_gaps
        result = analyze_topic_gaps(content, reference_contents)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '토픽 갭 분석')


# ── E-E-A-T 신뢰 신호 분석 ──────────────────────────

@blog_bp.route('/api/analyze-eeat', methods=['POST'])
def analyze_eeat_route():
    """콘텐츠의 E-E-A-T 신뢰 신호를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        author_info = data.get('author_info', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.eeat_analyzer_service import analyze_eeat
        result = analyze_eeat(content, author_info)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, 'E-E-A-T 분석')


# ── SERP 기능 기회 분석 ──────────────────────────────

@blog_bp.route('/api/serp-features', methods=['POST'])
def serp_features_route():
    """SERP 특수 기능 노출 가능성을 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        target_keyword = data.get('target_keyword', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.serp_feature_service import analyze_serp_features
        result = analyze_serp_features(content, target_keyword)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, 'SERP 기능 분석')


# ── 토픽 클러스터 매핑 ──────────────────────────────

@blog_bp.route('/api/topic-clusters', methods=['POST'])
def topic_clusters_route():
    """콘텐츠 목록의 토픽 클러스터 구조를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        contents = data.get('contents', [])

        if not contents or not isinstance(contents, list):
            return jsonify({'error': '분석할 콘텐츠 목록(contents)이 필요합니다.'}), 400

        from services.seo.topic_cluster_service import map_topic_clusters
        result = map_topic_clusters(contents)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '토픽 클러스터 분석')


# ── 엔터티 커버리지 분석 ──────────────────────────────

@blog_bp.route('/api/analyze-entities', methods=['POST'])
def analyze_entities_route():
    """콘텐츠의 엔터티 커버리지를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.entity_coverage_service import analyze_entities
        result = analyze_entities(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '엔터티 분석')


# ── 주장/인용 검증 ──────────────────────────────

@blog_bp.route('/api/verify-claims', methods=['POST'])
def verify_claims_route():
    """콘텐츠의 사실 주장과 인용 출처를 검증합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.quality.claim_verifier_service import verify_claims
        result = verify_claims(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '주장/인용 검증')


# ── 스키마 기회 탐색 ──────────────────────────────

@blog_bp.route('/api/schema-opportunities', methods=['POST'])
def schema_opportunities_route():
    """콘텐츠의 구조화 데이터(JSON-LD) 적용 기회를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.schema_opportunity_service import find_schema_opportunities
        result = find_schema_opportunities(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '스키마 기회 분석')


# ── 군더더기/헤지 표현 감지 ──────────────────────────────

@blog_bp.route('/api/detect-fillers', methods=['POST'])
def detect_fillers_route():
    """콘텐츠의 군더더기 및 헤지 표현을 감지합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.filler_detector_service import detect_fillers
        result = detect_fillers(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '군더더기 표현 감지')


# ── 정보 이득 분석 ──────────────────────────────

@blog_bp.route('/api/information-gain', methods=['POST'])
def information_gain_route():
    """콘텐츠의 정보 이득(차별화 수준)을 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        reference_contents = data.get('reference_contents', None)

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.information_gain_service import analyze_information_gain
        result = analyze_information_gain(content, reference_contents)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '정보 이득 분석')


# ── 자막 아티팩트 감지 ──────────────────────────────

@blog_bp.route('/api/detect-artifacts', methods=['POST'])
def detect_artifacts_route():
    """유튜브 자막 전사의 아티팩트를 감지합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.transcript.transcript_artifact_service import detect_transcript_artifacts
        result = detect_transcript_artifacts(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '자막 아티팩트 감지')


# ── 포용적 언어 검사 ──────────────────────────────

@blog_bp.route('/api/check-inclusive-language', methods=['POST'])
def check_inclusive_language_route():
    """콘텐츠의 포용적 언어 사용을 검사합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.inclusive_language_service import check_inclusive_language
        result = check_inclusive_language(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '포용적 언어 검사')


# ── 홍보 톤 포화도 검사 ──────────────────────────────

@blog_bp.route('/api/check-promotional-tone', methods=['POST'])
def check_promotional_tone_route():
    """콘텐츠의 홍보/세일즈 표현 밀도를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.promotional_tone_service import check_promotional_tone
        result = check_promotional_tone(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '홍보 톤 분석')


# ── 수치 약속 무결성 검사 ──────────────────────────────

@blog_bp.route('/api/check-numerical-promises', methods=['POST'])
def check_numerical_promises_route():
    """제목의 수치 약속이 본문에서 이행되는지 검사합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.numerical_promise_service import check_numerical_promises
        result = check_numerical_promises(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '수치 약속 검사')


# ── 앵커 텍스트 품질 감사 ──────────────────────────────

@blog_bp.route('/api/audit-anchors', methods=['POST'])
def audit_anchors_route():
    """콘텐츠 내 링크의 앵커 텍스트 품질을 검사합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.anchor_text_service import audit_anchor_texts
        result = audit_anchor_texts(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '앵커 텍스트 감사')


# ── 약속 이행 감사 ──────────────────────────────

@blog_bp.route('/api/audit-promises', methods=['POST'])
def audit_promises_route():
    """제목/소제목의 약속이 본문에서 이행되는지 검증합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.quality.promise_match_service import audit_promise_match
        result = audit_promise_match(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '약속 이행 감사')


# ── 내부 일관성 검사 ──────────────────────────────

@blog_bp.route('/api/check-consistency', methods=['POST'])
def check_consistency_route():
    """콘텐츠 내부의 수치/날짜/비교 모순을 검사합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.quality.consistency_checker_service import check_consistency
        result = check_consistency(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '일관성 검사')


# ── 전문 용어 정의 커버리지 ──────────────────────────────

@blog_bp.route('/api/analyze-jargon', methods=['POST'])
def analyze_jargon_route():
    """전문 용어/약어의 정의 동반 여부를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.jargon_analyzer_service import analyze_jargon_coverage
        result = analyze_jargon_coverage(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '전문 용어 분석')


# ── 음성 적합성 분석 ──────────────────────────────

@blog_bp.route('/api/analyze-speakability', methods=['POST'])
def analyze_speakability_route():
    """콘텐츠의 음성 재생 적합성을 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.speakability_service import analyze_speakability
        result = analyze_speakability(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '음성 적합성 분석')


# ── 소제목 간격 분석 ──────────────────────────────

@blog_bp.route('/api/detect-subheading-gaps', methods=['POST'])
def detect_subheading_gaps_route():
    """헤딩 사이 텍스트 길이와 섹션 균형을 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.subheading_gap_service import detect_subheading_gaps
        result = detect_subheading_gaps(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '소제목 간격 분석')


# ── 섹션 주제 이탈 감지 ──────────────────────────────

@blog_bp.route('/api/detect-section-drift', methods=['POST'])
def detect_section_drift_route():
    """각 섹션이 소제목 주제에서 벗어나는 지점을 감지합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.quality.section_drift_service import detect_section_drift
        result = detect_section_drift(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '섹션 이탈 감지')

# ── Example Coverage Analyzer ────────────────────────────────────────
@blog_bp.route('/api/analyze-example-coverage', methods=['POST'])
def analyze_example_coverage_route():
    """주장/조언의 예시·근거 커버리지를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.example_coverage_service import analyze_example_coverage
        result = analyze_example_coverage(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '예시 커버리지 분석')

# ── Question-Answer Closure Checker ──────────────────────────────────
@blog_bp.route('/api/check-qa-closure', methods=['POST'])
def check_qa_closure_route():
    """질문-답변 완결성을 검사합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.quality.qa_closure_service import check_qa_closure
        result = check_qa_closure(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '질문-답변 완결성 검사')

# ── Adverb Overuse Detector ──────────────────────────────────────────
@blog_bp.route('/api/detect-adverb-overuse', methods=['POST'])
def detect_adverb_overuse_route():
    """부사 남용을 감지합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.adverb_overuse_service import detect_adverb_overuse
        result = detect_adverb_overuse(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '부사 남용 감지')

# ── Statistics Coverage Analyzer ─────────────────────────────────────
@blog_bp.route('/api/analyze-statistics-coverage', methods=['POST'])
def analyze_statistics_coverage_route():
    """섹션별 수치 근거 커버리지를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.statistics_coverage_service import analyze_statistics_coverage
        result = analyze_statistics_coverage(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '수치 커버리지 분석')

# ── Simple Alternative Finder ────────────────────────────────────────
@blog_bp.route('/api/find-simple-alternatives', methods=['POST'])
def find_simple_alternatives_route():
    """고난도 어휘의 쉬운 대체어를 제안합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.simple_alternative_service import find_simple_alternatives
        result = find_simple_alternatives(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '쉬운 대체어 검색')

@blog_bp.route('/api/detect-actionability-gaps', methods=['POST'])
def detect_actionability_gaps_route():
    """실행 가능성 갭 감지 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.actionability_gap_service import detect_actionability_gaps
        result = detect_actionability_gaps(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '실행 가능성 갭 감지')

@blog_bp.route('/api/check-thesis-frontload', methods=['POST'])
def check_thesis_frontload_route():
    """핵심 주장 프론트로드 점검 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.thesis_frontload_service import check_thesis_frontload
        result = check_thesis_frontload(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '핵심 주장 프론트로드 점검')

@blog_bp.route('/api/detect-list-table-opportunities', methods=['POST'])
def detect_list_table_opportunities_route():
    """목록/표 변환 기회 감지 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.list_table_opportunity_service import detect_list_table_opportunities
        result = detect_list_table_opportunities(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '목록/표 변환 기회 감지')

@blog_bp.route('/api/audit-image-seo', methods=['POST'])
def audit_image_seo_route():
    """이미지 SEO 점검 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.image_seo_auditor_service import audit_image_seo
        result = audit_image_seo(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '이미지 SEO 점검')

@blog_bp.route('/api/audit-source-diversity', methods=['POST'])
def audit_source_diversity_route():
    """외부 소스 다양성 점검 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.external_source_diversity_service import audit_external_source_diversity
        result = audit_external_source_diversity(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '외부 소스 다양성 점검')

@blog_bp.route('/api/detect-chapter-breakpoints', methods=['POST'])
def detect_chapter_breakpoints_route():
    """챕터 분할점 감지 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.transcript.chapter_breakpoint_service import detect_chapter_breakpoints
        result = detect_chapter_breakpoints(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '챕터 분할점 감지')

@blog_bp.route('/api/analyze-question-density', methods=['POST'])
def analyze_question_density_route():
    """질문 밀도 분석 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.question_density_service import analyze_question_density
        result = analyze_question_density(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '질문 밀도 분석')

@blog_bp.route('/api/audit-whitespace-formatting', methods=['POST'])
def audit_whitespace_formatting_route():
    """공백/포맷 점검 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.whitespace_formatting_service import audit_whitespace_formatting
        result = audit_whitespace_formatting(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '공백/포맷 점검')

@blog_bp.route('/api/analyze-bullet-density', methods=['POST'])
def analyze_bullet_density_route():
    """불릿 리스트 밀도 분석 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.bullet_point_density_service import analyze_bullet_density
        result = analyze_bullet_density(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '불릿 리스트 밀도 분석')

@blog_bp.route('/api/check-code-block-quality', methods=['POST'])
def check_code_block_quality_route():
    """코드 블록 품질 점검 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.code_block_quality_service import check_code_block_quality
        result = check_code_block_quality(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '코드 블록 품질 점검')

@blog_bp.route('/api/validate-instruction-sequence', methods=['POST'])
def validate_instruction_sequence_route():
    """절차 시퀀스 검증 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.instruction_sequence_service import validate_instruction_sequence
        result = validate_instruction_sequence(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '절차 시퀀스 검증')

# ── Meta Description Quality Checker ──
@blog_bp.route('/api/check-meta-description-quality', methods=['POST'])
def check_meta_description_quality_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.meta_description_quality_service import check_meta_description_quality
        result = check_meta_description_quality(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '메타 디스크립션 품질 검사')

# ── Parenthetical Overuse Checker ──
@blog_bp.route('/api/check-parenthetical-overuse', methods=['POST'])
def check_parenthetical_overuse_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.parenthetical_overuse_service import check_parenthetical_overuse
        result = check_parenthetical_overuse(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '괄호 과다 사용 검사')

# ── Word Frequency Cloud Generator ──
@blog_bp.route('/api/generate-word-frequency', methods=['POST'])
def generate_word_frequency_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.media.word_frequency_cloud_service import generate_word_frequency
        top_n = data.get('top_n', 30)
        result = generate_word_frequency(content, top_n=top_n)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '단어 빈도 분석')

# ── Anaphora Repetition Detector ──
@blog_bp.route('/api/detect-anaphora-repetition', methods=['POST'])
def detect_anaphora_repetition_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.anaphora_repetition_service import detect_anaphora_repetition
        result = detect_anaphora_repetition(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '수사 반복 감지')

# ── Table of Contents Generator ──
@blog_bp.route('/api/generate-toc', methods=['POST'])
def generate_toc_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.content.toc_generator_service import generate_toc
        max_depth = data.get('max_depth', 3)
        result = generate_toc(content, max_depth=max_depth)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '목차 생성')

# ── Article Format Template Checker ──
@blog_bp.route('/api/check-article-format', methods=['POST'])
def check_article_format_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.content.article_format_template_service import check_article_format
        result = check_article_format(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '글 형식 템플릿 검사')

# ── Emotional Arc Mapper ──
@blog_bp.route('/api/map-emotional-arc', methods=['POST'])
def map_emotional_arc_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.emotional_arc_mapper_service import map_emotional_arc
        result = map_emotional_arc(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '감정 아크 매핑')

# ── Title Tag Length Checker ──
@blog_bp.route('/api/check-title-tag-length', methods=['POST'])
def check_title_tag_length_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.title_tag_length_service import check_title_tag_length
        result = check_title_tag_length(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '제목 태그 길이 검사')

# ── Keyword Stuffing Detector ──
@blog_bp.route('/api/detect-keyword-stuffing', methods=['POST'])
def detect_keyword_stuffing_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.keyword_stuffing_detector_service import detect_keyword_stuffing
        result = detect_keyword_stuffing(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '키워드 스터핑 감지')

# ── URL Health Checker ──
@blog_bp.route('/api/check-url-health', methods=['POST'])
def check_url_health_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.url_health_checker_service import check_url_health
        result = check_url_health(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, 'URL 건강 검사')

# ── Emoji Usage Analyzer ──
@blog_bp.route('/api/analyze-emoji-usage', methods=['POST'])
def analyze_emoji_usage_route():
    """이모지 사용 패턴을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.emoji_usage_analyzer_service import analyze_emoji_usage
        result = analyze_emoji_usage(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '이모지 사용 분석')

# ── Rhetorical Device Detector ──
@blog_bp.route('/api/detect-rhetorical-devices', methods=['POST'])
def detect_rhetorical_devices_route():
    """수사법을 감지합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.rhetorical_device_detector_service import detect_rhetorical_devices
        result = detect_rhetorical_devices(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '수사법 감지')

# ── Cliché Detector ──
@blog_bp.route('/api/detect-cliches', methods=['POST'])
def detect_cliches_route():
    """진부한 표현을 감지합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.cliche_detector_service import detect_cliches
        result = detect_cliches(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '클리셰 감지')

# ── Gender-Neutral Language Checker ──
@blog_bp.route('/api/check-gender-neutral', methods=['POST'])
def check_gender_neutral_route():
    """성별 포용적 언어 사용을 검사합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.gender_neutral_language_service import check_gender_neutral
        result = check_gender_neutral(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '성별 포용 언어 검사')

# ── Temporal Reference Checker ──
@blog_bp.route('/api/check-temporal-references', methods=['POST'])
def check_temporal_references_route():
    """시제/시간 참조 일관성을 검사합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.temporal_reference_checker_service import check_temporal_references
        result = check_temporal_references(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '시제 참조 검사')

# ── Data Visualization Opportunity ──
@blog_bp.route('/api/find-visualization-opportunities', methods=['POST'])
def find_visualization_opportunities_route():
    """데이터 시각화 기회를 찾습니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.data_visualization_opportunity_service import find_visualization_opportunities
        result = find_visualization_opportunities(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '데이터 시각화 기회 분석')

# ── Quotation Usage Analyzer ──
@blog_bp.route('/api/analyze-quotation-usage', methods=['POST'])
def analyze_quotation_usage_route():
    """인용문 사용 패턴을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.quotation_usage_analyzer_service import analyze_quotation_usage
        result = analyze_quotation_usage(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '인용문 사용 분석')

@blog_bp.route('/api/check-material-connection-disclosure', methods=['POST'])
def check_material_connection_disclosure_route():
    """제휴/협찬 공시 누락을 점검합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.material_connection_disclosure_service import check_material_connection_disclosure
        result = check_material_connection_disclosure(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '이해관계 공시 점검')

@blog_bp.route('/api/check-ai-disclosure', methods=['POST'])
def check_ai_disclosure_route():
    """AI 작성/보조 표시 누락을 점검합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.quality.ai_disclosure_checker_service import check_ai_disclosure
        result = check_ai_disclosure(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, 'AI 공시 점검')

@blog_bp.route('/api/analyze-tradeoff-coverage', methods=['POST'])
def analyze_tradeoff_coverage_route():
    """장단점 균형을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.tradeoff_coverage_analyzer_service import analyze_tradeoff_coverage
        result = analyze_tradeoff_coverage(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '장단점 균형 분석')

@blog_bp.route('/api/check-primary-source-preference', methods=['POST'])
def check_primary_source_preference_route():
    """인용 출처의 1차/2차 비율을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.primary_source_preference_service import check_primary_source_preference
        result = check_primary_source_preference(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '출처 품질 분석')

@blog_bp.route('/api/detect-high-stakes-advice-risk', methods=['POST'])
def detect_high_stakes_advice_risk_route():
    """고위험 조언 콘텐츠의 안전성을 점검합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.high_stakes_advice_risk_service import detect_high_stakes_advice_risk
        result = detect_high_stakes_advice_risk(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, 'YMYL 위험 감지')

@blog_bp.route('/api/check-evaluation-criteria-disclosure', methods=['POST'])
def check_evaluation_criteria_disclosure_route():
    """리뷰/비교 글의 평가 기준 공시를 점검합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.evaluation_criteria_disclosure_service import check_evaluation_criteria_disclosure
        result = check_evaluation_criteria_disclosure(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '평가 기준 공시 점검')

@blog_bp.route('/api/analyze-recommendation-justification', methods=['POST'])
def analyze_recommendation_justification_route():
    """추천 항목의 근거 충분성을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.quality.recommendation_justification_service import analyze_recommendation_justification
        result = analyze_recommendation_justification(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '추천 근거 분석')

@blog_bp.route('/api/check-prerequisite-disclosure', methods=['POST'])
def check_prerequisite_disclosure_route():
    """튜토리얼/가이드의 사전조건 공시를 점검합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.prerequisite_disclosure_service import check_prerequisite_disclosure
        result = check_prerequisite_disclosure(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '사전조건 공시 점검')

@blog_bp.route('/api/analyze-troubleshooting-coverage', methods=['POST'])
def analyze_troubleshooting_coverage_route():
    """가이드의 문제 해결 커버리지를 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.troubleshooting_coverage_service import analyze_troubleshooting_coverage
        result = analyze_troubleshooting_coverage(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '문제 해결 커버리지 분석')

@blog_bp.route('/api/analyze-extractability', methods=['POST'])
def analyze_extractability_route():
    """콘텐츠의 문맥 독립 추출 가능성을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.extractability_analyzer_service import analyze_extractability
        result = analyze_extractability(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '추출 가능성 분석')

@blog_bp.route('/api/analyze-community-evidence', methods=['POST'])
def analyze_community_evidence_route():
    """커뮤니티 근거 포함 여부를 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.quality.community_evidence_service import analyze_community_evidence
        result = analyze_community_evidence(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '커뮤니티 근거 분석')

@blog_bp.route('/api/check-update-delta-summary', methods=['POST'])
def check_update_delta_summary_route():
    """업데이트 변경 요약 블록 존재 여부를 점검합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.content.update_delta_summary_service import check_update_delta_summary
        result = check_update_delta_summary(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '업데이트 요약 점검')

# ── Audience-Fit Framing Analyzer ──
@blog_bp.route('/api/analyze-audience-fit-framing', methods=['POST'])
def analyze_audience_fit_framing_route():
    """대상 독자/상황/비적합 프레이밍을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.quality.audience_fit_framing_service import analyze_audience_fit_framing
        result = analyze_audience_fit_framing(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '대상 프레이밍 분석')

# ── Geo Scope Assumption Detector ──
@blog_bp.route('/api/detect-geo-scope-assumptions', methods=['POST'])
def detect_geo_scope_assumptions_route():
    """지역 의존 정보의 범위 라벨 누락을 탐지합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.geo_scope_assumption_service import detect_geo_scope_assumptions
        result = detect_geo_scope_assumptions(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '지역 범위 가정 탐지')

# ── Absolute Claim Risk Detector ──
@blog_bp.route('/api/detect-absolute-claim-risk', methods=['POST'])
def detect_absolute_claim_risk_route():
    """절대 표현의 위험도를 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.absolute_claim_risk_service import detect_absolute_claim_risk
        result = detect_absolute_claim_risk(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '절대 표현 위험 분석')

# ── Quantifier Specificity Analyzer ──
@blog_bp.route('/api/analyze-quantifier-specificity', methods=['POST'])
def analyze_quantifier_specificity_route():
    """수량 표현의 구체성을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.quantifier_specificity_service import analyze_quantifier_specificity
        result = analyze_quantifier_specificity(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '수량 구체성 분석')

# ── Step Verification Coverage Analyzer ──
@blog_bp.route('/api/analyze-step-verification-coverage', methods=['POST'])
def analyze_step_verification_coverage_route():
    """가이드 문서의 단계별 검증 기준 커버리지를 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.step_verification_coverage_service import analyze_step_verification_coverage
        result = analyze_step_verification_coverage(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '단계 검증 커버리지 분석')

# ── Comparison Criteria Completeness Checker ──
@blog_bp.route('/api/check-comparison-criteria-completeness', methods=['POST'])
def check_comparison_criteria_completeness_route():
    """비교 콘텐츠의 기준 명시 완전성을 검사합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.comparison_criteria_completeness_service import check_comparison_criteria_completeness
        result = check_comparison_criteria_completeness(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '비교 기준 완전성 검사')

# ── Terminology Drift Analyzer ──
@blog_bp.route('/api/analyze-terminology-drift', methods=['POST'])
def analyze_terminology_drift_route():
    """섹션 간 용어 혼용을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.terminology_drift_service import analyze_terminology_drift
        result = analyze_terminology_drift(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '용어 혼용 분석')

# ── Original Evidence Signal Analyzer ──
@blog_bp.route('/api/analyze-original-evidence', methods=['POST'])
def analyze_original_evidence_route():
    """원본 증거 신호를 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.original_evidence_signal_service import analyze_original_evidence
        result = analyze_original_evidence(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '원본 증거 신호 분석')

# ── Claim-Evidence Distance Analyzer ──
@blog_bp.route('/api/analyze-claim-evidence-distance', methods=['POST'])
def analyze_claim_evidence_distance_route():
    """주장-근거 거리를 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.claim_evidence_distance_service import analyze_claim_evidence_distance
        result = analyze_claim_evidence_distance(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '주장-근거 거리 분석')

# ── Definition Gap Detector ──
@blog_bp.route('/api/detect-definition-gaps', methods=['POST'])
def detect_definition_gaps_route():
    """정의 없는 전문 용어/약어를 탐지합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.definition_gap_service import detect_definition_gaps
        result = detect_definition_gaps(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '정의 갭 탐지')

# ── Methodology Transparency Checker ──
@blog_bp.route('/api/check-methodology-transparency', methods=['POST'])
def check_methodology_transparency_route():
    """방법론 투명성을 검사합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.methodology_transparency_service import check_methodology_transparency
        result = check_methodology_transparency(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '방법론 투명성 검사')

# ── Concept Load Analyzer ──
@blog_bp.route('/api/analyze-concept-load', methods=['POST'])
def analyze_concept_load_route():
    """구간별 인지부하를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.concept_load_service import analyze_concept_load
        result = analyze_concept_load(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '인지부하 분석')


# ── 스케줄러 상태 조회 ──────────────────────────────────────


@blog_bp.route('/api/scheduler/status', methods=['GET'])
@require_auth
def scheduler_status():
    """스케줄러 실행 상태 및 등록된 잡 목록을 조회합니다."""
    from services.data.scheduler_worker import scheduler

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
            'trigger': str(job.trigger),
        })

    return jsonify({
        'running': scheduler.running,
        'jobs': jobs,
        'total_jobs': len(jobs),
    })

# ============================================================
# 분리된 utility 서브 라우트 — 부수효과 import
# - routes/utility/operations.py: 헬스/heartbeat/providers/ollama (8개)
# ============================================================
from routes import utility as _utility_subroutes  # noqa: E402,F401
