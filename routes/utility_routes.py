"""
유틸리티 라우트 — 헬스체크, 프로바이더, 캐시, 스타일 추천/생성, 웹훅, 재생목록
"""
import json
import os
import threading
from typing import Dict

from flask import request, jsonify, current_app

from routes.blog_routes import blog_bp, _extract_client_id, DEFAULT_MODEL
from services.content.playlist_video_service import PlaylistVideoService
from services.core import ai_service, content_service
from services.core.content_service import clear_cache
from services.data.supabase_service import require_auth
from services.ops.client_tracker_service import ClientTracker
from services.platform.webhook_service import WebhookService
from utils.responses import handle_error, sanitize_error_for_client

_CLIENT_TRACKER_SERVICE = ClientTracker()
_CLIENT_TRACKER: Dict[str, float] = _CLIENT_TRACKER_SERVICE.clients

# 재생목록/채널 조회 결과 캐시 (5분 TTL)
_PLAYLIST_CACHE: Dict[str, dict] = {}
_PLAYLIST_CACHE_TTL: int = 300  # 초
_playlist_video_service = PlaylistVideoService(
    content_api=content_service,
    cache=_PLAYLIST_CACHE,
    ttl_seconds=_PLAYLIST_CACHE_TTL,
)

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
    _CLIENT_TRACKER_SERVICE.cleanup_stale()


@blog_bp.route('/health')
def health():
    """Health check endpoint for liveness probes."""
    from services.ops.health_service import (
        build_health_payload,
        detect_runtime_environment,
        get_process_memory_usage_mb,
    )

    increment_request_count()
    env = detect_runtime_environment(
        os.environ.get('FLASK_ENV'),
        debug=current_app.debug,
    )
    payload = build_health_payload(
        environment=env,
        request_count=get_request_count(),
        error_count=get_error_count(),
        error_rate=get_error_rate(),
        memory_usage_mb=get_process_memory_usage_mb(),
    )
    return jsonify(payload), 200


@blog_bp.route('/ready')
def ready():
    """Readiness probe for Redis, Supabase, ChromaDB, and scheduler.

    Used by container orchestrators to decide whether this process can handle
    traffic. `/health` is liveness; `/ready` verifies runtime dependencies.

    Returns:
        200: all required dependencies are ready
        503: one or more required dependencies failed
    """
    from services.ops.readiness_service import build_readiness_report

    report = build_readiness_report()
    status_code = 200 if report.ready else 503
    return jsonify({'ready': report.ready, 'checks': report.checks}), status_code


@blog_bp.route('/metrics')
def metrics():
    """Prometheus 스타일 metrics 엔드포인트.

    외부 의존성(prometheus-client) 없이 stdlib만으로 text/plain format 생성.
    Prometheus, Grafana Agent, Datadog 등에서 스크랩 가능.

    환경변수 METRICS_AUTH_TOKEN 설정 시 Authorization: Bearer <token> 요구.
    """
    expected_token = os.getenv('METRICS_AUTH_TOKEN', '').strip()
    if expected_token:
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer ') or auth[7:] != expected_token:
            return ('# unauthorized\n', 401, {'Content-Type': 'text/plain; charset=utf-8'})

    total_requests = get_request_count()
    total_errors = get_error_count()
    error_rate = get_error_rate()
    active = get_active_requests()

    queue_summary = {}
    try:
        from services.data.publish_queue_service import publish_queue_service
        queue_summary = publish_queue_service.get_status_summary()
    except Exception:
        pass

    import sys as _sys
    py_version = f"{_sys.version_info.major}.{_sys.version_info.minor}"

    memory_rss_bytes = None
    try:
        import resource
        memory_rss_bytes = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    except (ImportError, Exception):
        pass

    from services.ops.metrics_service import build_prometheus_metrics
    body = build_prometheus_metrics(
        total_requests=total_requests,
        total_errors=total_errors,
        error_rate=error_rate,
        active_requests=active,
        queue_summary=queue_summary,
        memory_rss_bytes=memory_rss_bytes,
        python_version=py_version,
    )
    return (body, 200, {'Content-Type': 'text/plain; version=0.0.4; charset=utf-8'})


@blog_bp.route('/')
def home():
    """API 서버 상태를 반환합니다. 프론트엔드는 Next.js에서 제공."""
    return jsonify({'status': 'ok', 'message': 'Insight Engine API Server'})


@blog_bp.route('/api/heartbeat', methods=['POST'])
def api_heartbeat():
    """클라이언트 연결 상태를 추적합니다."""
    client_id = _extract_client_id(request)
    if not client_id:
        return jsonify({'ok': False, 'error': 'clientId required'}), 400
    _CLIENT_TRACKER_SERVICE.heartbeat(client_id)
    _cleanup_stale_clients()
    return jsonify({'ok': True})


@blog_bp.route('/api/close', methods=['POST'])
def api_close():
    """클라이언트 연결 종료를 처리합니다."""
    client_id = _extract_client_id(request)
    if not client_id:
        return jsonify({'ok': False, 'error': 'clientId required'}), 400
    _CLIENT_TRACKER_SERVICE.close(client_id)
    return jsonify({'ok': True})


@blog_bp.route('/api/providers', methods=['GET'])
def api_providers():
    """API 키가 설정된 AI 서비스 및 모델 목록을 반환합니다.
    환경변수에 API 키가 설정된 프로바이더만 반환됩니다.
    """
    from config import get_available_providers, SUPADATA_API_KEY
    from services.core.provider_catalog_service import build_provider_catalog_response

    providers = get_available_providers()
    styles = current_app.config.get('STYLE_OPTIONS', [])
    return jsonify(build_provider_catalog_response(
        providers=providers,
        styles=styles,
        supadata_api_key=SUPADATA_API_KEY,
    ))


@blog_bp.route('/api/ollama/health', methods=['GET'])
def api_ollama_health():
    """Ollama 서버 연결 상태를 확인합니다."""
    from services.integrations.ollama_health_service import check_ollama_health

    base_url = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
    payload, status_code = check_ollama_health(base_url=base_url)
    return jsonify(payload), status_code


@blog_bp.route('/api/providers/validate', methods=['POST'])
def api_validate_provider():
    """API 키를 소량 토큰 호출로 유효성 테스트합니다."""
    data = request.get_json(silent=True) or {}
    provider_id = data.get('provider_id', '')
    api_key = data.get('api_key', '')

    from config import SUPPORTED_PROVIDERS
    from services.core.provider_validation_service import validate_provider_credentials

    payload, status_code = validate_provider_credentials(
        provider_id=provider_id,
        api_key=api_key,
        supported_providers=SUPPORTED_PROVIDERS,
    )
    return jsonify(payload), status_code


@blog_bp.route('/api/providers/campaign-packs', methods=['GET'])
def api_campaign_packs():
    """사용 가능한 캠페인 팩 목록을 반환합니다."""
    from config import CAMPAIGN_PACKS
    from services.core.provider_catalog_service import build_campaign_packs_response

    return jsonify(build_campaign_packs_response(CAMPAIGN_PACKS))


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


@blog_bp.route('/api/recommend-style', methods=['POST'])
def recommend_style():
    """YouTube 제목을 분석하여 최적의 스타일과 모디파이어를 AI로 추천합니다.
    API 키는 서버 환경변수에서 자동으로 로드됩니다.
    """
    title: str | None = None  # P1 버그 수정: 예외 발생 전 title 미정의 방지
    try:
        data = request.get_json(silent=True) or {}
        url = data.get('url')
        model = data.get('model', DEFAULT_MODEL)

        if not url:
            return jsonify({'error': 'YouTube URL이 필요합니다.'}), 400
        if not content_service.is_youtube_url(url):
            return jsonify({'error': '유효한 YouTube URL을 입력해주세요.'}), 400

        video_id = content_service.get_video_id(url)
        if not video_id:
            return jsonify({'error': '유효하지 않은 YouTube URL입니다.'}), 400

        title = content_service.get_content_title(url) or 'YouTube 영상'

        style_options = current_app.config.get('STYLE_OPTIONS', [])
        style_list = ', '.join([f"{s[0]}({s[1]})" for s in style_options])

        prompt = f"""다음 YouTube 영상 제목을 분석하여 가장 적합한 콘텐츠 스타일을 추천해주세요.

영상 제목: {title}

사용 가능한 스타일: {style_list}

다음 JSON 형식으로만 응답해주세요 (다른 텍스트 없이):
{{
    "style": "추천 스타일 ID",
    "reason": "추천 이유 (20자 이내)",
    "modifiers": {{
        "length": "short|medium|long",
        "tone": "professional|friendly|humorous",
        "emoji": "use|none"
    }}
}}"""

        response = ai_service.create_content(
            prompt,
            model,
            style_prompt=""
        )

        import re
        content = response.get('content', '')
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            recommendation = json.loads(json_match.group())
            recommendation['title'] = title
            return jsonify(recommendation)

        return jsonify({
            'style': 'detailed',
            'reason': '기본 추천',
            'modifiers': {'length': 'medium', 'tone': 'professional', 'emoji': 'none'},
            'title': title
        })

    except json.JSONDecodeError:
        return jsonify({
            'style': 'detailed',
            'reason': 'AI 응답 파싱 실패',
            'modifiers': {'length': 'medium', 'tone': 'professional', 'emoji': 'none'},
            'title': title or 'YouTube 영상'
        })
    except Exception as e:
        current_app.logger.error(f"Recommend style failed: {e}")
        return handle_error(str(e))


@blog_bp.route('/api/generate-style', methods=['POST'])
def generate_style():
    """YouTube 제목과 자막을 분석하여 맞춤형 프롬프트를 AI로 생성합니다.
    API 키는 서버 환경변수에서 자동으로 로드됩니다.
    """
    title: str | None = None  # P1 버그 수정: 예외 발생 전 title 미정의 방지
    try:
        data = request.get_json(silent=True) or {}
        url = data.get('url')
        model = data.get('model', DEFAULT_MODEL)

        if not url:
            return jsonify({'error': 'YouTube URL이 필요합니다.'}), 400
        if not content_service.is_youtube_url(url):
            return jsonify({'error': '유효한 YouTube URL을 입력해주세요.'}), 400

        video_id = content_service.get_video_id(url)
        if not video_id:
            return jsonify({'error': '유효하지 않은 YouTube URL입니다.'}), 400

        title = content_service.get_content_title(url) or 'YouTube 영상'

        transcript = content_service.get_transcript(video_id)
        if isinstance(transcript, dict) and transcript.get('error'):
            transcript_preview = "(자막 없음)"
        else:
            # P2 버그 #4 수정: transcript가 dict이면 text 필드 추출
            text = transcript.get('text', '') if isinstance(transcript, dict) else str(transcript or '')
            transcript_preview = text[:500] if text else "(자막 없음)"

        prompt = f"""다음 YouTube 영상의 제목과 자막 일부를 분석하여, 이 영상 콘텐츠에 최적화된 블로그 작성 프롬프트를 생성해주세요.

영상 제목: {title}
자막 미리보기: {transcript_preview}

다음 JSON 형식으로만 응답해주세요:
{{
    "styleName": "이 스타일의 이름 (10자 이내, 예: '기술 분석', '리뷰 정리')",
    "stylePrompt": "AI가 블로그를 작성할 때 사용할 상세 프롬프트 (200-400자)",
    "description": "이 스타일이 왜 이 영상에 적합한지 (30자 이내)"
}}"""

        response = ai_service.create_content(
            prompt,
            model,
            style_prompt=""
        )

        import re
        content = response.get('content', '')
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            result = json.loads(json_match.group())
            result['title'] = title
            return jsonify(result)

        return jsonify({
            'error': 'AI 응답을 파싱할 수 없습니다.',
            'title': title
        }), 500

    except json.JSONDecodeError:
        return jsonify({
            'error': 'AI 응답 JSON 파싱 실패',
            'title': title or 'YouTube 영상'
        }), 500
    except Exception as e:
        current_app.logger.error(f"Generate style failed: {e}")
        return handle_error(str(e))


@blog_bp.route('/api/webhook/test', methods=['POST'])
@require_auth
def webhook_test():
    """웹훅 URL로 테스트 페이로드를 전송합니다."""
    data = request.get_json(silent=True) or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'success': False, 'error': '웹훅 URL이 필요합니다.'}), 400

    test_svc = WebhookService(url=url, enabled=True)
    try:
        result = test_svc.test()
    except Exception as e:
        current_app.logger.error(f"Webhook test failed: {e}", exc_info=True)
        return jsonify({'success': False, 'error': '[서버 오류] 웹훅 테스트 중 문제가 발생했습니다.'}), 500

    if not result.get('success'):
        result = {
            **result,
            'error': sanitize_error_for_client(result.get('error', '웹훅 테스트 실패'))
        }
        if str(result.get('error', '')).startswith('[서버 오류]'):
            result['error'] = '[서버 오류] 웹훅 테스트에 실패했습니다.'

    status = 200 if result.get('success') else 400
    return jsonify(result), status


@blog_bp.route('/api/playlist-videos', methods=['POST'])
@require_auth
def playlist_videos():
    """채널 또는 재생목록 URL에서 영상 목록을 추출합니다."""
    try:
        data = request.get_json(silent=True) or {}
        url = data.get('url', '')
        max_results = min(int(data.get('maxResults', 10)), 50)

        if not url:
            return jsonify({'error': 'URL이 필요합니다.'}), 400

        result, status_code = _playlist_video_service.get_videos(url, max_results)
        return jsonify(result), status_code

    except Exception as e:
        current_app.logger.error(f"Playlist videos failed: {e}")
        return jsonify({'error': '영상 목록을 가져올 수 없습니다.'}), 500


@blog_bp.route('/api/recommend-sources', methods=['POST'])
def api_recommend_sources():
    """주제 기반 소스 추천"""
    try:
        data = request.get_json(silent=True) or {}
        topic = data.get('topic', '').strip()
        if not topic:
            return jsonify({'error': '주제를 입력해주세요.'}), 400

        from services.content.source_recommender_service import recommend_sources
        sources = recommend_sources(topic)
        return jsonify({'sources': sources})

    except ValueError as e:
        return handle_error(str(e))
    except Exception as e:
        current_app.logger.error(f"Source recommendation failed: {e}")
        return jsonify({'error': '소스 추천에 실패했습니다.'}), 500


@blog_bp.route('/api/wordcloud', methods=['POST'])
@require_auth
def api_wordcloud():
    """텍스트에서 워드클라우드 SVG를 생성합니다."""
    try:
        data = request.get_json(silent=True) or {}
        text = data.get('text', '')
        max_words = min(int(data.get('max_words', 60)), 100)

        if not text:
            return jsonify({'error': '텍스트가 필요합니다.'}), 400

        from services.media.wordcloud_service import generate_wordcloud
        svg = generate_wordcloud(text, max_words=max_words)
        return jsonify({'svg': svg})

    except ValueError as e:
        return handle_error(str(e))
    except Exception as e:
        current_app.logger.error(f"Wordcloud failed: {e}")
        return jsonify({'error': '워드클라우드 생성에 실패했습니다.'}), 500


@blog_bp.route('/api/schema', methods=['GET'])
def api_schema():
    """API 파라미터 OpenAPI 스키마를 반환합니다."""
    schema = {
        'openapi': '3.0.0',
        'info': {'title': 'Insight Engine API', 'version': '1.0.0'},
        'paths': {
            '/generate': {
                'post': {
                    'summary': 'AI 콘텐츠 생성',
                    'requestBody': {
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': 'object',
                                    'required': ['url', 'model', 'style'],
                                    'properties': {
                                        'url': {'type': 'string', 'description': 'YouTube 영상 URL'},
                                        'model': {'type': 'string', 'description': 'AI 모델 ID'},
                                        'style': {'type': 'string', 'description': '콘텐츠 스타일 ID'},
                                        'modifiers': {
                                            'type': 'object',
                                            'properties': {
                                                'length': {'type': 'string', 'enum': ['short', 'medium', 'long']},
                                                'writing_style': {'type': 'string', 'enum': ['conversational', 'explanatory', 'casual', 'expert']},
                                                'language': {'type': 'string', 'enum': ['ko', 'en', 'ja']},
                                            },
                                        },
                                        'detail_level': {'type': 'string', 'enum': ['brief', 'standard', 'deep'], 'default': 'standard'},
                                        'output_format': {'type': 'string', 'enum': ['html', 'markdown', 'plain'], 'default': 'html'},
                                        'max_chars': {'type': 'integer', 'minimum': 100, 'maximum': 50000},
                                        'include_transcript': {'type': 'boolean', 'default': False},
                                        'web_search': {'type': 'boolean', 'default': False},
                                        'agent_mode': {'type': 'boolean', 'default': False},
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
    }
    return jsonify(schema)


@blog_bp.route('/feed.xml', methods=['GET'])
def rss_feed():
    """최근 생성 콘텐츠를 RSS 2.0 XML로 발행합니다."""
    from xml.etree.ElementTree import Element, SubElement, tostring
    from flask import Response
    from services.data.supabase_service import is_supabase_enabled

    channel_title = 'Insight Engine'
    channel_link = request.host_url.rstrip('/')
    channel_desc = 'AI로 생성된 최신 콘텐츠 피드'

    rss = Element('rss', version='2.0')
    channel = SubElement(rss, 'channel')
    SubElement(channel, 'title').text = channel_title
    SubElement(channel, 'link').text = channel_link
    SubElement(channel, 'description').text = channel_desc
    SubElement(channel, 'language').text = 'ko'

    # Supabase 활성화 시 최근 히스토리에서 가져오기
    items = []
    if is_supabase_enabled():
        try:
            from services.data.supabase_service import SupabaseService
            result = SupabaseService.get_histories(limit=20)
            items = result.get('histories', [])
        except Exception:
            pass

    for item_data in items:
        item = SubElement(channel, 'item')
        SubElement(item, 'title').text = item_data.get('title', '제목 없음')
        SubElement(item, 'description').text = (item_data.get('content', '') or '')[:500]
        SubElement(item, 'pubDate').text = item_data.get('created_at', '')
        report_id = item_data.get('report_id', '')
        if report_id:
            SubElement(item, 'guid').text = report_id

    xml_bytes = tostring(rss, encoding='unicode', xml_declaration=False)
    xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes

    return Response(xml_str, mimetype='application/rss+xml; charset=utf-8')


@blog_bp.route('/api/cache/ai', methods=['DELETE'])
@require_auth
def api_clear_ai_cache():
    """AI 결과 캐시를 삭제합니다. videoId가 있으면 해당 영상만."""
    data = request.get_json(silent=True) or {}
    video_id = data.get('videoId')
    deleted = current_app.ai_cache.clear(video_id)
    return jsonify({'success': True, 'deleted': deleted})


@blog_bp.route('/api/fact-check', methods=['POST'])
def api_fact_check():
    """콘텐츠의 팩트체크를 수행합니다."""
    data = request.get_json(silent=True) or {}
    content = data.get('content', '')
    if not content:
        return jsonify({'error': 'content 필수'}), 400

    from services.agents.fact_check_agent import fact_check
    result = fact_check(content)
    return jsonify(result)


# === SEO 최적화 (F3-08) ===

@blog_bp.route('/api/seo-optimize', methods=['POST'])
def api_seo_optimize():
    """콘텐츠의 SEO를 분석하고 최적화 제안을 반환합니다."""
    data = request.get_json(silent=True) or {}
    content = data.get('content', '')
    keywords = data.get('keywords', [])
    if not content:
        return jsonify({'error': 'content 필수'}), 400

    from services.agents.seo_optimize_agent import optimize_seo
    result = optimize_seo(content, keywords)
    return jsonify(result)


# === 표절 감지 (F3-09) ===

@blog_bp.route('/api/plagiarism-check', methods=['POST'])
def api_plagiarism_check():
    """콘텐츠의 표절/중복 여부를 검사합니다."""
    data = request.get_json(silent=True) or {}
    content = data.get('content', '')
    if not content:
        return jsonify({'error': 'content 필수'}), 400

    from services.quality.plagiarism_service import check_plagiarism
    result = check_plagiarism(content)
    return jsonify(result)


# === 가독성 분석 (F3-10) ===

@blog_bp.route('/api/readability', methods=['POST'])
def api_readability():
    """콘텐츠의 가독성 점수를 분석합니다."""
    data = request.get_json(silent=True) or {}
    text = data.get('text', '')
    if not text:
        return jsonify({'error': 'text 필수'}), 400

    from services.analysis.readability_service import analyze_readability
    result = analyze_readability(text)
    return jsonify(result)


# === 감정 흐름 분석 (F3-11) ===

@blog_bp.route('/api/sentiment-flow', methods=['POST'])
def api_sentiment_flow():
    """콘텐츠의 문단별 감정 흐름을 분석합니다."""
    data = request.get_json(silent=True) or {}
    content = data.get('content', '')
    if not content:
        return jsonify({'error': 'content 필수'}), 400

    from services.analysis.nlp_analysis_service import analyze_sentiment_flow
    result = analyze_sentiment_flow(content)
    return jsonify(result)


# === NPS 피드백 (F4-20) ===

@blog_bp.route('/api/feedback/nps', methods=['POST'])
def submit_nps_feedback():
    """NPS 점수 + 피드백 제출"""
    from flask import g
    data = request.get_json(silent=True) or {}
    score = data.get('score')
    feedback = data.get('feedback', '')

    if score is None or not (0 <= int(score) <= 10):
        return jsonify({'error': 'score는 0~10 사이여야 합니다.'}), 400

    # 인메모리 저장 (프로덕션에서는 DB)
    entry = {
        'user_id': getattr(g, 'user_id', 'anonymous'),
        'score': int(score),
        'feedback': feedback,
    }
    return jsonify({'success': True, **entry})


# ── 콘텐츠 종합 등급 평가 ──────────────────────────────

@blog_bp.route('/api/grade-content', methods=['POST'])
def grade_content_route():
    """콘텐츠를 종합 평가하여 A~F 등급을 반환합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '평가할 콘텐츠가 필요합니다.'}), 400

        from services.quality.content_grader_service import grade_content
        result = grade_content(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '콘텐츠 등급 평가')


# ── 스마트 헤드라인 최적화 ──────────────────────────────

@blog_bp.route('/api/optimize-headline', methods=['POST'])
def optimize_headline_route():
    """제목을 분석하고 최적화 제안을 반환합니다."""
    try:
        data = request.get_json(silent=True) or {}
        title = data.get('title', '')
        content = data.get('content', '')

        if not title or not title.strip():
            return jsonify({'error': '분석할 제목이 필요합니다.'}), 400

        from services.seo.headline_optimizer_service import optimize_headline
        result = optimize_headline(title, content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '헤드라인 최적화')


# ── 콘텐츠 신선도 모니터링 ──────────────────────────────

@blog_bp.route('/api/freshness-check', methods=['POST'])
def freshness_check_route():
    """콘텐츠의 신선도를 평가합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        published_date = data.get('published_date', '')

        if not content or not content.strip():
            return jsonify({'error': '평가할 콘텐츠가 필요합니다.'}), 400
        if not published_date:
            return jsonify({'error': '발행일(published_date)이 필요합니다. ISO 8601 형식 (예: 2025-06-15)'}), 400

        from services.seo.freshness_monitor_service import check_freshness
        result = check_freshness(content, published_date)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '콘텐츠 신선도 체크')


# ── 인터랙티브 퀴즈 생성 ──────────────────────────────

@blog_bp.route('/api/generate-quiz', methods=['POST'])
def generate_quiz_route():
    """콘텐츠에서 퀴즈를 자동 생성합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        count = data.get('count', 5)

        if not content or not content.strip():
            return jsonify({'error': '퀴즈를 생성할 콘텐츠가 필요합니다.'}), 400

        from services.content.quiz_generator_service import generate_quiz
        result = generate_quiz(content, count)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '퀴즈 생성')


# ── 콘텐츠 카니발리제이션 감지 ──────────────────────────

@blog_bp.route('/api/check-cannibalization', methods=['POST'])
def check_cannibalization_route():
    """여러 콘텐츠 간의 키워드 카니발리제이션을 감지합니다."""
    try:
        data = request.get_json(silent=True) or {}
        contents = data.get('contents', [])

        if not contents or len(contents) < 2:
            return jsonify({'error': '최소 2개 콘텐츠가 필요합니다. contents: [{id, title, content}, ...]'}), 400

        from services.seo.cannibalization_service import detect_cannibalization
        result = detect_cannibalization(contents)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '카니발리제이션 감지')


# ── AI 토론 생성 ──────────────────────────────────────

@blog_bp.route('/api/generate-debate', methods=['POST'])
def generate_debate_route():
    """주제에 대한 다각적 관점(찬성/반대/중립)을 생성합니다."""
    try:
        data = request.get_json(silent=True) or {}
        topic = data.get('topic', '')
        content = data.get('content', '')

        if not topic or not topic.strip():
            return jsonify({'error': '토론 주제가 필요합니다.'}), 400

        from services.content.debate_service import generate_debate
        result = generate_debate(topic, content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '토론 생성')


# ── 콘텐츠 감성 분석 ──────────────────────────────────

@blog_bp.route('/api/analyze-sentiment', methods=['POST'])
def analyze_sentiment_route():
    """콘텐츠의 감성 톤(긍정/부정/중립)을 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.sentiment_analyzer_service import analyze_sentiment
        result = analyze_sentiment(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '감성 분석')


# ── 훅 문장 생성 ──────────────────────────────────────

@blog_bp.route('/api/generate-hooks', methods=['POST'])
def generate_hooks_route():
    """주제에 대한 훅(서두) 문장을 생성합니다."""
    try:
        data = request.get_json(silent=True) or {}
        topic = data.get('topic', '')
        content = data.get('content', '')
        count = data.get('count', 5)

        if not topic or not topic.strip():
            return jsonify({'error': '주제(topic)가 필요합니다.'}), 400

        from services.content.hook_generator_service import generate_hooks
        result = generate_hooks(topic, content, count)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '훅 생성')


# ── 소셜 프루프 스니펫 추출 ────────────────────────────

@blog_bp.route('/api/extract-snippets', methods=['POST'])
def extract_snippets_route():
    """콘텐츠에서 소셜 공유용 스니펫을 추출합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        max_count = data.get('max_count', 10)

        if not content or not content.strip():
            return jsonify({'error': '스니펫을 추출할 콘텐츠가 필요합니다.'}), 400

        from services.media.social_proof_service import extract_snippets
        result = extract_snippets(content, max_count)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '스니펫 추출')


# ── 가독성 벤치마크 ────────────────────────────────────

@blog_bp.route('/api/benchmark-readability', methods=['POST'])
def benchmark_readability_route():
    """콘텐츠 가독성을 카테고리 벤치마크와 비교합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        category = data.get('category', 'blog')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.readability_benchmark_service import benchmark_readability
        result = benchmark_readability(content, category)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '가독성 벤치마크')


# ── 콘텐츠 아웃라인 생성 ───────────────────────────────

@blog_bp.route('/api/generate-outline', methods=['POST'])
def generate_outline_route():
    """주제에 맞는 콘텐츠 아웃라인을 생성합니다."""
    try:
        data = request.get_json(silent=True) or {}
        topic = data.get('topic', '')
        template = data.get('template', 'guide')
        keywords = data.get('keywords', [])

        if not topic or not topic.strip():
            return jsonify({'error': '주제(topic)가 필요합니다.'}), 400

        from services.content.outline_generator_service import generate_outline
        result = generate_outline(topic, template, keywords)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '아웃라인 생성')


# ── 읽기 시간 예측 ─────────────────────────────────────

@blog_bp.route('/api/reading-time', methods=['POST'])
def reading_time_route():
    """콘텐츠의 읽기 시간과 난이도를 예측합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        content_type = data.get('content_type', 'general')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.reading_time_service import estimate_reading_time
        result = estimate_reading_time(content, content_type)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '읽기 시간 예측')


# ── CTA 분석 ─────────────────────────────────────────

@blog_bp.route('/api/analyze-cta', methods=['POST'])
def analyze_cta_route():
    """콘텐츠의 CTA를 감지하고 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        goal = data.get('goal', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.cta_optimizer_service import analyze_ctas, suggest_ctas
        analysis = analyze_ctas(content)
        if goal:
            suggestions = suggest_ctas(content, goal)
            analysis['goal_suggestions'] = suggestions
        return jsonify(analysis)

    except Exception as e:
        return handle_error(e, 'CTA 분석')


# ── 키워드 밀도 분석 ──────────────────────────────────

@blog_bp.route('/api/keyword-density', methods=['POST'])
def keyword_density_route():
    """콘텐츠의 키워드 밀도를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        keywords = data.get('keywords', None)

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        if keywords:
            from services.seo.keyword_density_service import analyze_density
            result = analyze_density(content, keywords)
        else:
            from services.seo.keyword_density_service import get_density_report
            result = get_density_report(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '키워드 밀도 분석')


# ── 연결어 분석 ───────────────────────────────────────

@blog_bp.route('/api/analyze-transitions', methods=['POST'])
def analyze_transitions_route():
    """콘텐츠의 연결어 사용을 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        suggest = data.get('suggest', False)

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.transition_analyzer_service import analyze_transitions, suggest_transitions
        result = analyze_transitions(content)
        if suggest:
            result['recommendations'] = suggest_transitions(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '연결어 분석')


# ── 문단 균형 분석 ────────────────────────────────────

@blog_bp.route('/api/paragraph-balance', methods=['POST'])
def paragraph_balance_route():
    """문단 길이 균형을 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.paragraph_balance_service import analyze_balance
        result = analyze_balance(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '문단 균형 분석')


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


# ── 문장 다양성 분석 ──────────────────────────────────

@blog_bp.route('/api/sentence-variety', methods=['POST'])
def sentence_variety_route():
    """문장 길이/구조 다양성을 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.sentence_analysis_service import analyze_variety
        result = analyze_variety(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '문장 다양성 분석')


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


# ── 콘텐츠 성과 예측 ─────────────────────────────────

@blog_bp.route('/api/predict-performance', methods=['POST'])
def predict_performance_route():
    """콘텐츠의 성과(조회수, 참여도)를 예측합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        title = data.get('title', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.content_performance_predictor_service import predict_performance
        result = predict_performance(content, title)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '콘텐츠 성과 예측')


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


# ── 헤딩 병렬성 검사 ──────────────────────────────

@blog_bp.route('/api/check-heading-parallelism', methods=['POST'])
def check_heading_parallelism_route():
    """동일 레벨 헤딩의 문법 형태 일관성을 검사합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.heading_parallelism_service import check_heading_parallelism
        result = check_heading_parallelism(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '헤딩 병렬성 검사')


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

# ── Pronoun Clarity Checker ──────────────────────────────────────────
@blog_bp.route('/api/check-pronoun-clarity', methods=['POST'])
def check_pronoun_clarity_route():
    """대명사 명확성을 검사합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.pronoun_clarity_service import check_pronoun_clarity
        result = check_pronoun_clarity(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '대명사 명확성 검사')

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

# ── Clause Overload Detector ─────────────────────────────────────────
@blog_bp.route('/api/detect-clause-overload', methods=['POST'])
def detect_clause_overload_route():
    """문장 내 절 과부하를 감지합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.clause_overload_service import detect_clause_overload
        result = detect_clause_overload(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '절 과부하 감지')

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

# ── Heading Term Placement Auditor ───────────────────────────────────
@blog_bp.route('/api/audit-heading-terms', methods=['POST'])
def audit_heading_terms_route():
    """핵심 용어의 헤딩 배치를 점검합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.heading_term_placement_service import audit_heading_term_placement
        result = audit_heading_term_placement(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '헤딩 용어 배치 점검')

# ── Acronym Expansion Compliance Checker ─────────────────────────────
@blog_bp.route('/api/check-acronym-expansion', methods=['POST'])
def check_acronym_expansion_route():
    """약어의 첫 등장 시 풀어쓰기 여부를 점검합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.acronym_expansion_service import check_acronym_expansion
        result = check_acronym_expansion(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '약어 풀어쓰기 점검')

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

@blog_bp.route('/api/check-paragraph-opening-variety', methods=['POST'])
def check_paragraph_opening_variety_route():
    """문단 시작 다양성 점검 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.paragraph_opening_variety_service import check_paragraph_opening_variety
        result = check_paragraph_opening_variety(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '문단 시작 다양성 점검')

@blog_bp.route('/api/check-tone-consistency', methods=['POST'])
def check_tone_consistency_route():
    """문체 일관성 점검 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.tone_consistency_service import check_tone_consistency
        result = check_tone_consistency(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '문체 일관성 점검')

@blog_bp.route('/api/detect-linking-verb-overuse', methods=['POST'])
def detect_linking_verb_overuse_route():
    """연결 동사 과다 사용 감지 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.linking_verb_overuse_service import detect_linking_verb_overuse
        result = detect_linking_verb_overuse(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '연결 동사 과다 사용 감지')

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

@blog_bp.route('/api/score-content-depth', methods=['POST'])
def score_content_depth_route():
    """콘텐츠 심도 측정 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.content_depth_scorer_service import score_content_depth
        result = score_content_depth(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '콘텐츠 심도 측정')

# ── Conclusion Strength Analyzer ──
@blog_bp.route('/api/analyze-conclusion-strength', methods=['POST'])
def analyze_conclusion_strength_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.conclusion_strength_service import analyze_conclusion_strength
        result = analyze_conclusion_strength(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '결론 강도 분석')

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

# ── Sentence Connector Variety Analyzer ──
@blog_bp.route('/api/analyze-connector-variety', methods=['POST'])
def analyze_connector_variety_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.sentence_analysis_service import analyze_connector_variety
        result = analyze_connector_variety(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '연결어 다양성 분석')

# ── Content Freshness Indicator ──
@blog_bp.route('/api/check-content-freshness', methods=['POST'])
def check_content_freshness_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.content_freshness_indicator_service import check_content_freshness
        result = check_content_freshness(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '콘텐츠 시의성 평가')

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

# ── Sentence Length Rhythm Analyzer ──
@blog_bp.route('/api/analyze-sentence-rhythm', methods=['POST'])
def analyze_sentence_rhythm_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.sentence_analysis_service import analyze_sentence_rhythm
        result = analyze_sentence_rhythm(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '문장 리듬 분석')

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

# ── Sentence Ending Variety ──
@blog_bp.route('/api/analyze-sentence-ending-variety', methods=['POST'])
def analyze_sentence_ending_variety_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.sentence_analysis_service import analyze_sentence_ending_variety
        result = analyze_sentence_ending_variety(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '종결어미 다양성 분석')

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

# ── Passive Construction Ratio ──
@blog_bp.route('/api/analyze-passive-ratio', methods=['POST'])
def analyze_passive_ratio_route():
    """피동/수동 구문 비율을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.passive_construction_ratio_service import analyze_passive_ratio
        result = analyze_passive_ratio(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '피동 구문 비율 분석')

# ── Average Words Per Sentence ──
@blog_bp.route('/api/analyze-avg-words-per-sentence', methods=['POST'])
def analyze_avg_words_per_sentence_route():
    """문장당 평균 단어 수를 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.sentence_analysis_service import analyze_avg_words_per_sentence
        result = analyze_avg_words_per_sentence(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '문장당 평균 단어 수 분석')

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

# ── Acronym Consistency Checker ──
@blog_bp.route('/api/check-acronym-consistency', methods=['POST'])
def check_acronym_consistency_route():
    """약어 일관성을 검사합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.acronym_consistency_checker_service import check_acronym_consistency
        result = check_acronym_consistency(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '약어 일관성 검사')

# ── Heading Keyword Density ──
@blog_bp.route('/api/analyze-heading-keyword-density', methods=['POST'])
def analyze_heading_keyword_density_route():
    """헤딩 키워드 밀도를 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.heading_keyword_density_service import analyze_heading_keyword_density
        result = analyze_heading_keyword_density(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '헤딩 키워드 밀도 분석')

# ── Content Symmetry Analyzer ──
@blog_bp.route('/api/analyze-content-symmetry', methods=['POST'])
def analyze_content_symmetry_route():
    """콘텐츠 구조적 대칭성을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.content_symmetry_analyzer_service import analyze_content_symmetry
        result = analyze_content_symmetry(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '콘텐츠 대칭성 분석')

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

# ── Sentence Complexity Scorer ──
@blog_bp.route('/api/score-sentence-complexity', methods=['POST'])
def score_sentence_complexity_route():
    """문장 복잡도를 평가합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.sentence_analysis_service import score_sentence_complexity
        result = score_sentence_complexity(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '문장 복잡도 평가')

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

# ── Sentence Starter Diversity ──
@blog_bp.route('/api/analyze-sentence-starter-diversity', methods=['POST'])
def analyze_sentence_starter_diversity_route():
    """문장 시작어 다양성을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.sentence_analysis_service import analyze_sentence_starter_diversity
        result = analyze_sentence_starter_diversity(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '문장 시작어 다양성 분석')

# ── Average Paragraph Length ──
@blog_bp.route('/api/analyze-avg-paragraph-length', methods=['POST'])
def analyze_avg_paragraph_length_route():
    """단락 평균 길이를 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.avg_paragraph_length_service import analyze_avg_paragraph_length
        result = analyze_avg_paragraph_length(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '단락 평균 길이 분석')

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

@blog_bp.route('/api/analyze-noun-verb-ratio', methods=['POST'])
def analyze_noun_verb_ratio_route():
    """명사/동사 비율을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.noun_verb_ratio_service import analyze_noun_verb_ratio
        result = analyze_noun_verb_ratio(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '명사/동사 비율 분석')

@blog_bp.route('/api/score-content-scanability', methods=['POST'])
def score_content_scanability_route():
    """콘텐츠 스캔 가독성을 평가합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.content_scanability_service import score_content_scanability
        result = score_content_scanability(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '스캔 가독성 평가')

@blog_bp.route('/api/analyze-passive-active-trend', methods=['POST'])
def analyze_passive_active_trend_route():
    """섹션별 능동/피동 비율 추이를 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.passive_active_trend_service import analyze_passive_active_trend
        result = analyze_passive_active_trend(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '능동/피동 추이 분석')

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

# ── List Parallelism Checker ──
@blog_bp.route('/api/check-list-parallelism', methods=['POST'])
def check_list_parallelism_route():
    """목록 항목의 병렬 구조 일관성을 검사합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.list_parallelism_service import check_list_parallelism
        result = check_list_parallelism(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '목록 병렬 구조 검사')

# ── Heading Hierarchy Integrity Checker ──
@blog_bp.route('/api/check-heading-hierarchy', methods=['POST'])
def check_heading_hierarchy_route():
    """마크다운 제목 계층 구조를 검사합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.heading_hierarchy_service import check_heading_hierarchy
        result = check_heading_hierarchy(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '제목 계층 구조 검사')

# ── Numeric & Unit Consistency Checker ──
@blog_bp.route('/api/check-numeric-unit-consistency', methods=['POST'])
def check_numeric_unit_consistency_route():
    """숫자/단위 표기 일관성을 검사합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.numeric_unit_consistency_service import check_numeric_unit_consistency
        result = check_numeric_unit_consistency(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '숫자/단위 일관성 검사')

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

# ── Topic Sentence Alignment Analyzer ──
@blog_bp.route('/api/analyze-topic-sentence-alignment', methods=['POST'])
def analyze_topic_sentence_alignment_route():
    """문단별 주제문 정렬을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.sentence_analysis_service import analyze_topic_sentence_alignment
        result = analyze_topic_sentence_alignment(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '주제문 정렬 분석')

# ── Paragraph Unity Checker ──
@blog_bp.route('/api/check-paragraph-unity', methods=['POST'])
def check_paragraph_unity_route():
    """문단별 주제 통일성을 검사합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.paragraph_unity_service import check_paragraph_unity
        result = check_paragraph_unity(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '문단 통일성 검사')

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

# ── Adjacent Paragraph Cohesion Analyzer ──
@blog_bp.route('/api/analyze-adjacent-cohesion', methods=['POST'])
def analyze_adjacent_cohesion_route():
    """인접 문단 간 응집도를 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.adjacent_cohesion_service import analyze_adjacent_cohesion
        result = analyze_adjacent_cohesion(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '문단 응집도 분석')

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
