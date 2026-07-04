"""외부 자동화 통합 — Slack/Discord/Telegram 봇, Zapier, Make, IFTTT, Airtable, Sheets, Webhook Relay, Slack/Discord 알림."""
from flask import request, jsonify, current_app

from routes.blog_routes import blog_bp
from routes.integrations._shared import sanitize_integration_error
from utils.responses import api_error, clamp_query_int


# ── Slack 봇 웹훅 (F7-02) ──────────────────────────────────────


@blog_bp.route('/api/webhooks/slack', methods=['POST'])
def slack_webhook():
    """Slack Event API 웹훅 수신"""
    from services.integrations.slack_bot_service import slack_bot_service

    body = request.get_data()
    timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
    signature = request.headers.get('X-Slack-Signature', '')

    if not slack_bot_service.verify_signature(body, timestamp, signature):
        return api_error('Slack 서명 검증 실패', 401)

    payload = request.get_json(silent=True) or {}
    result = slack_bot_service.handle_event(payload)
    return jsonify(result)


# ── Discord 봇 웹훅 (F7-03) ──────────────────────────────────────


@blog_bp.route('/api/webhooks/discord', methods=['POST'])
def discord_webhook():
    """Discord Interactions 엔드포인트"""
    from services.integrations.discord_bot_service import discord_bot_service

    body = request.get_data()
    timestamp = request.headers.get('X-Signature-Timestamp', '')
    signature = request.headers.get('X-Signature-Ed25519', '')

    if not discord_bot_service.verify_signature(body, timestamp, signature):
        return api_error('Discord 서명 검증 실패', 401)

    payload = request.get_json(silent=True) or {}
    result = discord_bot_service.handle_interaction(payload)
    return jsonify(result)


# ── Telegram 봇 웹훅 (F7-04) ──────────────────────────────────────


@blog_bp.route('/api/webhooks/telegram', methods=['POST'])
def telegram_webhook():
    """Telegram 웹훅 수신"""
    from services.integrations.telegram_bot_service import telegram_bot_service

    update = request.get_json(silent=True) or {}

    # 콜백 쿼리 (인라인 버튼)
    if 'callback_query' in update:
        result = telegram_bot_service.handle_callback_query(update['callback_query'])
    else:
        result = telegram_bot_service.handle_update(update)

    return jsonify(result)


@blog_bp.route('/api/webhooks/telegram/setwebhook', methods=['POST'])
def telegram_set_webhook():
    """Telegram 웹훅 URL 등록"""
    from services.integrations.telegram_bot_service import telegram_bot_service

    data = request.get_json(silent=True) or {}
    webhook_url = data.get('webhook_url', '')
    if not webhook_url:
        return api_error('webhook_url이 필요합니다.', 400)

    success = telegram_bot_service.set_webhook(webhook_url)
    return jsonify({'success': success})


# ── Zapier 통합 (F7-05) ──────────────────────────────────────


@blog_bp.route('/api/zapier/trigger', methods=['POST'])
def zapier_trigger():
    """Zapier 트리거 — URL과 스타일을 받아 콘텐츠 생성 결과를 반환합니다.

    Zapier Action에서 이 엔드포인트를 호출하면 됩니다.
    """
    data = request.get_json(silent=True) or {}
    url = data.get('url', '').strip()
    style_id = data.get('style_id', 'blog_seo')

    if not url:
        return api_error('url이 필요합니다.', 400)

    # 동기 생성 (Zapier는 동기 응답 필요)
    try:
        from services.core.content_service import get_transcript
        from services.core.ai_service import create_content
        transcript = get_transcript(url)
        if not transcript:
            return api_error('자막을 가져올 수 없습니다.', 400)

        result = create_content(transcript, style_id)
        return jsonify({
            'title': result.get('title', ''),
            'content': result.get('content', ''),
            'html': result.get('html', ''),
            'source_url': url,
        })
    except Exception as e:
        current_app.logger.error(f"Zapier 트리거 오류: {e}")
        return api_error('콘텐츠 생성 중 오류가 발생했습니다.', 500)


@blog_bp.route('/api/zapier/auth/test', methods=['GET'])
def zapier_auth_test():
    """Zapier 인증 테스트 엔드포인트"""
    return jsonify({'status': 'ok', 'service': 'Insight Engine'})


# ── Make (Integromat) 통합 (F7-06) ──────────────────────────────────────


@blog_bp.route('/api/make/webhook', methods=['POST'])
def make_webhook():
    """Make (Integromat) 호환 웹훅

    Make 시나리오의 Custom Webhook 모듈에서 이 URL을 트리거로 사용합니다.
    """
    data = request.get_json(silent=True) or {}
    url = data.get('url', '').strip()
    style_id = data.get('style_id', 'blog_seo')
    language = data.get('language', 'ko')
    callback_url = data.get('callback_url', '')  # Make 응답 URL

    if not url:
        return api_error('url이 필요합니다.', 400)

    # 즉시 수락 응답 (Make는 비동기 처리 가능)
    import threading

    app = current_app._get_current_object()

    def _process():
        with app.app_context():
            try:
                from services.core.content_service import get_transcript
                from services.core.ai_service import create_content
                transcript = get_transcript(url)
                if not transcript:
                    return
                result = create_content(transcript, style_id, modifiers={'language': language})

                # callback_url이 있으면 결과 전달
                if callback_url:
                    import json
                    import urllib.request
                    payload = json.dumps({
                        'title': result.get('title', ''),
                        'content': result.get('content', ''),
                        'source_url': url,
                    }).encode()
                    req = urllib.request.Request(
                        callback_url,
                        data=payload,
                        headers={'Content-Type': 'application/json'},
                    )
                    urllib.request.urlopen(req, timeout=30)
            except Exception as e:
                app.logger.error(f"Make 웹훅 처리 오류: {e}")

    threading.Thread(target=_process, daemon=True).start()
    return jsonify({'accepted': True, 'message': '처리를 시작했습니다.'})


# ── IFTTT 연동 (F7-20) ──────────────────────────────────────


@blog_bp.route('/api/ifttt/trigger', methods=['POST'])
def ifttt_trigger():
    """IFTTT Webhook 트리거

    IFTTT Webhooks 서비스에서 이 URL로 POST 요청을 보내면
    콘텐츠 생성을 시작합니다.

    IFTTT Webhooks 형식: {"value1": "URL", "value2": "스타일", "value3": "언어"}
    """
    data = request.get_json(silent=True) or {}
    url = (data.get('value1') or data.get('url', '')).strip()
    style_id = data.get('value2') or data.get('style_id', 'blog_seo')
    language = data.get('value3') or data.get('language', 'ko')

    if not url:
        return api_error('value1(URL)이 필요합니다.', 400)

    try:
        from services.core.content_service import get_transcript
        from services.core.ai_service import create_content
        transcript = get_transcript(url)
        if not transcript:
            return api_error('자막을 가져올 수 없습니다.', 400)

        result = create_content(transcript, style_id, modifiers={'language': language})
        return jsonify({
            'title': result.get('title', ''),
            'content_preview': result.get('content', '')[:500],
            'source_url': url,
        })
    except Exception as e:
        current_app.logger.error(f"IFTTT 트리거 오류: {e}")
        return api_error('처리 중 오류가 발생했습니다.', 500)


# ── Webhook Relay (F7-19) ──────────────────────────────────────


@blog_bp.route('/api/webhook-relay', methods=['POST'])
def webhook_relay():
    """다수의 웹훅 URL에 동시 발송"""
    from services.platform.webhook_relay_service import webhook_relay_service

    data = request.get_json(silent=True) or {}
    urls = data.get('urls', [])
    payload = data.get('payload', {})
    headers = data.get('headers', {})
    timeout = clamp_query_int(data.get('timeout'), default=15, min_val=1, max_val=60)

    if not urls:
        return api_error('urls 목록이 필요합니다.', 400)
    if not payload:
        return api_error('payload가 필요합니다.', 400)
    if len(urls) > 50:
        return api_error('URL은 최대 50개까지 허용됩니다.', 400)

    try:
        result = webhook_relay_service.send_all(urls, payload, headers, timeout)
    except Exception as e:
        current_app.logger.error('Webhook relay failed: %s', e, exc_info=True)
        return api_error('[서버 오류] 웹훅 전송 중 문제가 발생했습니다.', 500)

    sanitized_results = []
    for item in result.get('results', []):
        sanitized_item = dict(item)
        if sanitized_item.get('error'):
            sanitized_item['error'] = sanitize_integration_error(
                sanitized_item['error'],
                '[서버 오류] 웹훅 전송에 실패했습니다.'
            )
        sanitized_results.append(sanitized_item)
    if sanitized_results:
        result = {**result, 'results': sanitized_results}

    return jsonify(result)
