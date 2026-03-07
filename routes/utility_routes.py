"""
유틸리티 라우트 — 헬스체크, 프로바이더, 캐시, 스타일 추천/생성, 웹훅, 재생목록
"""
import json
import os
import time
from typing import Dict

from flask import request, jsonify, current_app

from routes.blog_routes import blog_bp, _extract_client_id, _get_style_prompt, DEFAULT_MODEL
from services import ai_service, content_service
from services.content_service import clear_cache
from services.supabase_service import require_auth
from services.webhook_service import WebhookService
from utils.responses import handle_error

_CLIENT_TRACKER: Dict[str, float] = {}


@blog_bp.route('/health')
def health():
    """헬스체크 엔드포인트 (Railway/Docker용)"""
    return jsonify({'status': 'healthy'}), 200


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
    _CLIENT_TRACKER[client_id] = time.time()
    return jsonify({'ok': True})


@blog_bp.route('/api/close', methods=['POST'])
def api_close():
    """클라이언트 연결 종료를 처리합니다."""
    client_id = _extract_client_id(request)
    if not client_id:
        return jsonify({'ok': False, 'error': 'clientId required'}), 400
    _CLIENT_TRACKER.pop(client_id, None)
    return jsonify({'ok': True})


@blog_bp.route('/api/providers', methods=['GET'])
def api_providers():
    """API 키가 설정된 AI 서비스 및 모델 목록을 반환합니다.
    환경변수에 API 키가 설정된 프로바이더만 반환됩니다.
    """
    from config import get_available_providers, SUPADATA_API_KEY

    providers = get_available_providers()
    styles = current_app.config.get('STYLE_OPTIONS', [])

    return jsonify({
        'providers': providers,
        'styles': [{'id': s[0], 'name': s[1]} for s in styles],
        'supadataConfigured': bool(SUPADATA_API_KEY),
        'hasAutoFallback': True
    })


@blog_bp.route('/api/ollama/health', methods=['GET'])
def api_ollama_health():
    """Ollama 서버 연결 상태를 확인합니다."""
    import requests as http_requests

    base_url = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
    try:
        resp = http_requests.get(f'{base_url}/api/tags', timeout=5)
        resp.raise_for_status()
        data = resp.json()
        models = [m.get('name', '') for m in data.get('models', [])]
        return jsonify({'ok': True, 'models': models, 'base_url': base_url})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'base_url': base_url}), 503


@blog_bp.route('/api/providers/validate', methods=['POST'])
def api_validate_provider():
    """API 키를 소량 토큰 호출로 유효성 테스트합니다."""
    data = request.get_json(silent=True) or {}
    provider_id = data.get('provider_id', '')
    api_key = data.get('api_key', '')

    if not provider_id:
        return jsonify({'valid': False, 'error': 'provider_id가 필요합니다.'}), 400

    from config import SUPPORTED_PROVIDERS

    if provider_id not in SUPPORTED_PROVIDERS:
        return jsonify({'valid': False, 'error': f'지원하지 않는 프로바이더: {provider_id}'}), 400

    provider = SUPPORTED_PROVIDERS[provider_id]
    models = provider.get('models', [])
    if not models:
        return jsonify({'valid': False, 'error': '사용 가능한 모델이 없습니다.'}), 400

    test_model = models[0]['id']

    # Ollama는 API 키 대신 base URL로 연결 테스트
    if provider_id == 'ollama':
        import requests as http_requests
        base_url = api_key or provider.get('api_base', 'http://localhost:11434')
        try:
            resp = http_requests.get(f'{base_url}/api/tags', timeout=5)
            resp.raise_for_status()
            return jsonify({'valid': True, 'model_tested': test_model})
        except Exception as e:
            return jsonify({'valid': False, 'model_tested': test_model, 'error': str(e)})

    if not api_key:
        return jsonify({'valid': False, 'error': 'API 키가 필요합니다.'}), 400

    # LiteLLM으로 소량 토큰 호출 테스트
    try:
        import litellm

        kwargs = {
            'model': test_model,
            'messages': [{'role': 'user', 'content': 'Hi'}],
            'max_tokens': 5,
            'api_key': api_key,
        }
        # api_base가 있는 프로바이더 (zhipuai, openrouter 등)
        if provider.get('api_base'):
            kwargs['api_base'] = provider['api_base']

        litellm.completion(**kwargs)
        return jsonify({'valid': True, 'model_tested': test_model})
    except Exception as e:
        return jsonify({'valid': False, 'model_tested': test_model, 'error': str(e)})


@blog_bp.route('/api/providers/campaign-packs', methods=['GET'])
def api_campaign_packs():
    """사용 가능한 캠페인 팩 목록을 반환합니다."""
    from config import CAMPAIGN_PACKS
    packs = {
        pack_id: {**pack, 'id': pack_id}
        for pack_id, pack in CAMPAIGN_PACKS.items()
    }
    return jsonify({'packs': packs})


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
    result = test_svc.test()
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

        if content_service.is_playlist_url(url):
            result = content_service.get_playlist_videos(url, max_results)
        elif content_service.is_channel_url(url):
            result = content_service.get_channel_videos(url, max_results)
        else:
            return jsonify({'error': '유효한 채널 또는 재생목록 URL이 아닙니다.'}), 400

        if 'error' in result:
            return jsonify(result), 400

        return jsonify(result)

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

        from services.source_recommender_service import recommend_sources
        sources = recommend_sources(topic)
        return jsonify({'sources': sources})

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
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

        from services.wordcloud_service import generate_wordcloud
        svg = generate_wordcloud(text, max_words=max_words)
        return jsonify({'svg': svg})

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
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
    from services.supabase_service import is_supabase_enabled

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
            from services.supabase_service import SupabaseService
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


@blog_bp.route('/api/cache/stats', methods=['GET'])
@require_auth
def api_cache_stats():
    """AI 결과 캐시 통계를 반환합니다."""
    stats = current_app.ai_cache.get_stats()
    return jsonify(stats)


@blog_bp.route('/api/cache/ai', methods=['DELETE'])
@require_auth
def api_clear_ai_cache():
    """AI 결과 캐시를 삭제합니다. videoId가 있으면 해당 영상만."""
    data = request.get_json(silent=True) or {}
    video_id = data.get('videoId')
    deleted = current_app.ai_cache.clear(video_id)
    return jsonify({'success': True, 'deleted': deleted})


# === 피드백 (F3-06) ===

@blog_bp.route('/api/feedback', methods=['POST'])
def api_feedback():
    """사용자 피드백(좋아요/싫어요)을 저장합니다."""
    data = request.get_json(silent=True) or {}
    style_id = data.get('style_id', '')
    content_id = data.get('content_id', '')
    rating = data.get('rating', '')
    comment = data.get('comment')

    if not style_id or not content_id or rating not in ('like', 'dislike'):
        return jsonify({'error': 'style_id, content_id, rating(like/dislike) 필수'}), 400

    from services.prompt_optimizer_service import save_feedback
    result = save_feedback(
        style_id=style_id,
        content_id=content_id,
        rating=rating,
        comment=comment,
    )
    return jsonify(result)


@blog_bp.route('/api/feedback/stats/<style_id>', methods=['GET'])
def api_feedback_stats(style_id: str):
    """스타일별 피드백 통계를 반환합니다."""
    from services.prompt_optimizer_service import get_feedback_stats
    return jsonify(get_feedback_stats(style_id))


# === 팩트체크 (F3-07) ===

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

    from services.plagiarism_service import check_plagiarism
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

    from services.readability_service import analyze_readability
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

    from services.nlp_analysis_service import analyze_sentiment_flow
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

        from services.content_grader_service import grade_content
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

        from services.headline_optimizer_service import optimize_headline
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

        from services.freshness_monitor_service import check_freshness
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

        from services.quiz_generator_service import generate_quiz
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

        from services.cannibalization_service import detect_cannibalization
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

        from services.debate_service import generate_debate
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

        from services.sentiment_analyzer_service import analyze_sentiment
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

        from services.hook_generator_service import generate_hooks
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

        from services.social_proof_service import extract_snippets
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

        from services.readability_benchmark_service import benchmark_readability
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

        from services.outline_generator_service import generate_outline
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

        from services.reading_time_service import estimate_reading_time
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

        from services.cta_optimizer_service import analyze_ctas, suggest_ctas
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
            from services.keyword_density_service import analyze_density
            result = analyze_density(content, keywords)
        else:
            from services.keyword_density_service import get_density_report
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

        from services.transition_analyzer_service import analyze_transitions, suggest_transitions
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

        from services.paragraph_balance_service import analyze_balance
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

        from services.power_word_service import analyze_power_words, suggest_power_words
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

        from services.emotional_tone_service import map_emotional_tone
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

        from services.engagement_scorer_service import score_engagement
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

        from services.sentence_variety_service import analyze_variety
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

        from services.redundancy_checker_service import check_redundancy
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

        from services.passive_voice_service import detect_passive
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

        from services.acronym_extractor_service import extract_acronyms
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

        from services.faq_generator_service import generate_faq
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

        from services.content_performance_predictor_service import predict_performance
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

        from services.brand_voice_profiler_service import profile_brand_voice
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

        from services.audience_persona_service import build_persona
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

        from services.visual_content_service import suggest_visuals
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

        from services.aeo_optimizer_service import analyze_aeo
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

        from services.search_intent_service import analyze_search_intent
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

        from services.internal_link_service import find_link_opportunities
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

        from services.originality_checker_service import check_originality
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

        from services.topic_gap_service import analyze_topic_gaps
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

        from services.eeat_analyzer_service import analyze_eeat
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

        from services.serp_feature_service import analyze_serp_features
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

        from services.topic_cluster_service import map_topic_clusters
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

        from services.entity_coverage_service import analyze_entities
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

        from services.claim_verifier_service import verify_claims
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

        from services.schema_opportunity_service import find_schema_opportunities
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

        from services.filler_detector_service import detect_fillers
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

        from services.information_gain_service import analyze_information_gain
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

        from services.transcript_artifact_service import detect_transcript_artifacts
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

        from services.inclusive_language_service import check_inclusive_language
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

        from services.promotional_tone_service import check_promotional_tone
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

        from services.numerical_promise_service import check_numerical_promises
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

        from services.anchor_text_service import audit_anchor_texts
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

        from services.promise_match_service import audit_promise_match
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

        from services.consistency_checker_service import check_consistency
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

        from services.jargon_analyzer_service import analyze_jargon_coverage
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

        from services.speakability_service import analyze_speakability
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

        from services.subheading_gap_service import detect_subheading_gaps
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

        from services.heading_parallelism_service import check_heading_parallelism
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

        from services.section_drift_service import detect_section_drift
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

            from services.pronoun_clarity_service import check_pronoun_clarity
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

            from services.example_coverage_service import analyze_example_coverage
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

            from services.qa_closure_service import check_qa_closure
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

            from services.adverb_overuse_service import detect_adverb_overuse
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

            from services.clause_overload_service import detect_clause_overload
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

            from services.statistics_coverage_service import analyze_statistics_coverage
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

            from services.simple_alternative_service import find_simple_alternatives
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

            from services.heading_term_placement_service import audit_heading_term_placement
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

            from services.acronym_expansion_service import check_acronym_expansion
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

            from services.actionability_gap_service import detect_actionability_gaps
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

            from services.thesis_frontload_service import check_thesis_frontload
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

            from services.list_table_opportunity_service import detect_list_table_opportunities
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

            from services.image_seo_auditor_service import audit_image_seo
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

            from services.external_source_diversity_service import audit_external_source_diversity
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

            from services.chapter_breakpoint_service import detect_chapter_breakpoints
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

            from services.question_density_service import analyze_question_density
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

            from services.whitespace_formatting_service import audit_whitespace_formatting
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

            from services.bullet_point_density_service import analyze_bullet_density
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

            from services.code_block_quality_service import check_code_block_quality
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

            from services.paragraph_opening_variety_service import check_paragraph_opening_variety
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

            from services.tone_consistency_service import check_tone_consistency
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

            from services.linking_verb_overuse_service import detect_linking_verb_overuse
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

            from services.instruction_sequence_service import validate_instruction_sequence
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

            from services.content_depth_scorer_service import score_content_depth
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

            from services.conclusion_strength_service import analyze_conclusion_strength
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

            from services.meta_description_quality_service import check_meta_description_quality
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

            from services.parenthetical_overuse_service import check_parenthetical_overuse
            result = check_parenthetical_overuse(content)
            return jsonify(result)

        except Exception as e:
            return handle_error(e, '괄호 과다 사용 검사')