"""외부 통신 라우트 — 웹훅 / 재생목록 / RSS.

utility_routes.py에서 분리됨. playlist 캐시는 utility_routes에서 가져와 공유.
"""
from flask import Response, current_app, g, jsonify, request

from extensions import limiter
from routes.blog_routes import blog_bp
from routes.utility._state import (
    PlaylistCacheUnavailable,
    PlaylistLoadError,
    get_or_load_playlist_cache,
)
from services.core import content_service
from services.usage import require_usage
from services.usage.usage_decorator import capture_usage_charge_callback
from services.usage.usage_lock import UsageLockUnavailable
from src.contexts.identity.interface.auth_decorators import require_auth
from services.platform.webhook_service import WebhookService
from utils.responses import api_error, sanitize_error_for_client


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
@limiter.limit("20/minute")
@require_auth
@require_usage
def playlist_videos():
    """채널 또는 재생목록 URL에서 영상 목록을 추출합니다."""
    try:
        data = request.get_json(silent=True) or {}
        url = data.get('url', '')
        if not isinstance(url, str):
            return api_error('URL은 문자열이어야 합니다.', 400)
        url = url.strip()
        if len(url) > 2_048:
            return api_error('URL이 너무 깁니다.', 400)
        try:
            max_results = int(data.get('maxResults', 10))
        except (TypeError, ValueError):
            return api_error('maxResults는 정수여야 합니다.', 400)
        max_results = max(1, min(max_results, 50))

        if not url:
            return api_error('URL이 필요합니다.', 400)

        if content_service.is_playlist_url(url):
            playlist_id = content_service._get_playlist_id(url)
            if not playlist_id:
                return api_error('유효한 재생목록 URL이 아닙니다.', 400)
            source_kind = 'playlist'
            source_id = playlist_id
        elif content_service.is_channel_url(url):
            channel = content_service._get_channel_identifier(url)
            if not channel:
                return api_error('유효한 채널 URL이 아닙니다.', 400)
            source_kind = f"channel:{channel['type']}"
            source_id = channel['value'].lower()
        else:
            return api_error('유효한 채널 또는 재생목록 URL이 아닙니다.', 400)

        # 쿼리 문자열 변형으로 캐시와 YouTube 쿼터를 우회할 수 없게 식별자만 사용합니다.
        cache_key = f"{source_kind}:{source_id}:{max_results}"
        on_cost_start = capture_usage_charge_callback()

        def _load_videos():
            if source_kind == 'playlist':
                loaded = content_service.get_playlist_videos(
                    url,
                    max_results,
                    on_cost_start=on_cost_start,
                )
            else:
                loaded = content_service.get_channel_videos(
                    url,
                    max_results,
                    on_cost_start=on_cost_start,
                )
            if not isinstance(loaded, dict):
                raise RuntimeError('invalid playlist provider response')
            # 오류 응답은 캐시하지 않습니다.
            if 'error' in loaded:
                raise PlaylistLoadError(
                    str(loaded.get('error') or '재생목록 조회 실패')
                )
            return loaded

        try:
            result, cached = get_or_load_playlist_cache(cache_key, _load_videos)
        except PlaylistCacheUnavailable:
            return api_error('재생목록 조회가 일시적으로 혼잡합니다.', 503)
        except PlaylistLoadError as exc:
            return api_error(str(exc), 400)

        if cached:
            result = {**result, 'cached': True}

        charge_state = getattr(g, 'usage_charge_state', None)
        if charge_state is not None and not charge_state.committed:
            g.skip_usage_decrement = True

        return jsonify(result)

    except UsageLockUnavailable:
        raise
    except Exception as e:
        current_app.logger.error(f"Playlist videos failed: {e}")
        return api_error('영상 목록을 가져올 수 없습니다.', 500)


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
    # 기존 legacy history 조회 호출은 대상 클래스 자체가 존재하지 않아
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
