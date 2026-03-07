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

