"""외부 통신 라우트 — 웹훅 / 재생목록 / 소스 추천 / 워드클라우드 / 스키마 / RSS.

utility_routes.py에서 분리됨. playlist 캐시는 utility_routes에서 가져와 공유.
"""
import time

from flask import Response, current_app, jsonify, request

from routes.blog_routes import blog_bp
from routes.utility._state import _PLAYLIST_CACHE, _PLAYLIST_CACHE_TTL
from services.core import content_service
from src.contexts.identity.interface.auth_decorators import require_auth
from services.platform.webhook_service import WebhookService
from utils.responses import handle_error, sanitize_error_for_client


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

        # 캐시 키: URL + max_results
        cache_key = f"{url}|{max_results}"
        now = time.time()

        # 캐시 히트 확인 (TTL 5분)
        cached = _PLAYLIST_CACHE.get(cache_key)
        if cached and (now - cached['ts']) < _PLAYLIST_CACHE_TTL:
            result = cached['data']
            result['cached'] = True
            return jsonify(result)

        if content_service.is_playlist_url(url):
            result = content_service.get_playlist_videos(url, max_results)
        elif content_service.is_channel_url(url):
            result = content_service.get_channel_videos(url, max_results)
        else:
            return jsonify({'error': '유효한 채널 또는 재생목록 URL이 아닙니다.'}), 400

        if 'error' in result:
            return jsonify(result), 400

        # 성공 결과를 캐시에 저장
        _PLAYLIST_CACHE[cache_key] = {'data': dict(result), 'ts': now}

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
    from src.shared.infrastructure.supabase_client import is_supabase_enabled

    channel_title = 'Insight Engine'
    channel_link = request.host_url.rstrip('/')
    channel_desc = 'AI로 생성된 최신 콘텐츠 피드'

    rss = Element('rss', version='2.0')
    channel = SubElement(rss, 'channel')
    SubElement(channel, 'title').text = channel_title
    SubElement(channel, 'link').text = channel_link
    SubElement(channel, 'description').text = channel_desc
    SubElement(channel, 'language').text = 'ko'

    # RSS 피드: 공개 히스토리 조회 미구현 — Phase 5+에서 공개 콘텐츠 BC 도입 시 연결 예정.
    # 기존 `SupabaseService.get_histories(limit=20)` 호출은 클래스 자체가 존재하지 않아
    # 항상 빈 결과였음 (dead code, try/except로 silent fail). 명시적 빈 리스트로 단순화.
    items: list = []
    _ = is_supabase_enabled  # noqa: F841 — 후속 PR에서 공개 콘텐츠 BC 도입 시 사용 예정

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
