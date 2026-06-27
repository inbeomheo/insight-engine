"""외부 자동화 통합 — Slack/Discord/Telegram 봇, Zapier, Make, IFTTT, Airtable, Sheets, Webhook Relay, Slack/Discord 알림."""
import hmac
import os

from flask import request, jsonify, current_app

from routes.blog_routes import blog_bp
from routes.integrations._shared import (
    sanitize_integration_error,
    sanitize_result_message,
)
from src.contexts.identity.interface.auth_decorators import require_auth
from utils.responses import handle_error, clamp_query_int


AUTOMATION_WEBHOOK_SECRET_HEADER = 'X-Insight-Webhook-Secret'
TELEGRAM_WEBHOOK_SECRET_HEADER = 'X-Telegram-Bot-Api-Secret-Token'


def _is_production() -> bool:
    return (os.getenv('FLASK_ENV') or '').strip().lower() == 'production'


def _bearer_token() -> str:
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:].strip()
    return ''


def _automation_webhook_secret_error():
    configured_secret = (os.getenv('AUTOMATION_WEBHOOK_SECRET') or '').strip()
    if not configured_secret:
        if _is_production():
            current_app.logger.warning('Blocked automation webhook without AUTOMATION_WEBHOOK_SECRET')
            return jsonify({
                'error': '자동화 웹훅 secret이 설정되지 않았습니다.',
                'code': 'AUTOMATION_WEBHOOK_SECRET_NOT_CONFIGURED',
            }), 503
        return None

    supplied_secret = (
        request.headers.get(AUTOMATION_WEBHOOK_SECRET_HEADER, '').strip()
        or request.headers.get('X-Automation-Webhook-Secret', '').strip()
        or _bearer_token()
    )
    if not supplied_secret or not hmac.compare_digest(supplied_secret, configured_secret):
        return jsonify({
            'error': '자동화 웹훅 인증에 실패했습니다.',
            'code': 'AUTOMATION_WEBHOOK_AUTH_FAILED',
        }), 401
    return None


def _telegram_webhook_secret_error():
    configured_secret = (os.getenv('TELEGRAM_WEBHOOK_SECRET') or '').strip()
    if not configured_secret:
        if _is_production():
            current_app.logger.warning('Blocked Telegram webhook without TELEGRAM_WEBHOOK_SECRET')
            return jsonify({
                'error': 'Telegram 웹훅 secret이 설정되지 않았습니다.',
                'code': 'TELEGRAM_WEBHOOK_SECRET_NOT_CONFIGURED',
            }), 503
        return None

    supplied_secret = request.headers.get(TELEGRAM_WEBHOOK_SECRET_HEADER, '').strip()
    if not supplied_secret or not hmac.compare_digest(supplied_secret, configured_secret):
        return jsonify({
            'error': 'Telegram 웹훅 인증에 실패했습니다.',
            'code': 'TELEGRAM_WEBHOOK_AUTH_FAILED',
        }), 401
    return None


# ── Slack 봇 웹훅 (F7-02) ──────────────────────────────────────


@blog_bp.route('/api/webhooks/slack', methods=['POST'])
def slack_webhook():
    """Slack Event API 웹훅 수신"""
    from services.integrations.slack_bot_service import slack_bot_service

    body = request.get_data()
    timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
    signature = request.headers.get('X-Slack-Signature', '')

    if not slack_bot_service.verify_signature(body, timestamp, signature):
        return jsonify({'error': 'Slack 서명 검증 실패'}), 401

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
        return jsonify({'error': 'Discord 서명 검증 실패'}), 401

    payload = request.get_json(silent=True) or {}
    result = discord_bot_service.handle_interaction(payload)
    return jsonify(result)


# ── Telegram 봇 웹훅 (F7-04) ──────────────────────────────────────


@blog_bp.route('/api/webhooks/telegram', methods=['POST'])
def telegram_webhook():
    """Telegram 웹훅 수신"""
    from services.integrations.telegram_bot_service import telegram_bot_service

    secret_error = _telegram_webhook_secret_error()
    if secret_error:
        return secret_error

    update = request.get_json(silent=True) or {}

    # 콜백 쿼리 (인라인 버튼)
    if 'callback_query' in update:
        result = telegram_bot_service.handle_callback_query(update['callback_query'])
    else:
        result = telegram_bot_service.handle_update(update)

    return jsonify(result)


@blog_bp.route('/api/webhooks/telegram/setwebhook', methods=['POST'])
@require_auth
def telegram_set_webhook():
    """Telegram 웹훅 URL 등록"""
    from services.integrations.telegram_bot_service import telegram_bot_service

    if _is_production() and not (os.getenv('TELEGRAM_WEBHOOK_SECRET') or '').strip():
        return jsonify({
            'error': 'Telegram 웹훅 secret이 설정되지 않았습니다.',
            'code': 'TELEGRAM_WEBHOOK_SECRET_NOT_CONFIGURED',
        }), 503

    data = request.get_json(silent=True) or {}
    webhook_url = data.get('webhook_url', '')
    if not webhook_url:
        return jsonify({'error': 'webhook_url이 필요합니다.'}), 400

    success = telegram_bot_service.set_webhook(webhook_url)
    return jsonify({'success': success})


# ── Zapier 통합 (F7-05) ──────────────────────────────────────


@blog_bp.route('/api/zapier/trigger', methods=['POST'])
def zapier_trigger():
    """Zapier 트리거 — URL과 스타일을 받아 콘텐츠 생성 결과를 반환합니다.

    Zapier Action에서 이 엔드포인트를 호출하면 됩니다.
    """
    secret_error = _automation_webhook_secret_error()
    if secret_error:
        return secret_error

    data = request.get_json(silent=True) or {}
    url = data.get('url', '').strip()
    style_id = data.get('style_id', 'blog_seo')

    if not url:
        return jsonify({'error': 'url이 필요합니다.'}), 400

    # 동기 생성 (Zapier는 동기 응답 필요)
    try:
        from services.core.content_service import get_transcript
        from services.core.ai_service import create_content
        transcript = get_transcript(url)
        if not transcript:
            return jsonify({'error': '자막을 가져올 수 없습니다.'}), 400

        result = create_content(transcript, style_id)
        return jsonify({
            'title': result.get('title', ''),
            'content': result.get('content', ''),
            'html': result.get('html', ''),
            'source_url': url,
        })
    except Exception as e:
        current_app.logger.error(f"Zapier 트리거 오류: {e}")
        return jsonify({'error': '콘텐츠 생성 중 오류가 발생했습니다.'}), 500


@blog_bp.route('/api/zapier/auth/test', methods=['GET'])
def zapier_auth_test():
    """Zapier 인증 테스트 엔드포인트"""
    secret_error = _automation_webhook_secret_error()
    if secret_error:
        return secret_error

    return jsonify({'status': 'ok', 'service': 'Insight Engine'})


# ── Make (Integromat) 통합 (F7-06) ──────────────────────────────────────


@blog_bp.route('/api/make/webhook', methods=['POST'])
def make_webhook():
    """Make (Integromat) 호환 웹훅

    Make 시나리오의 Custom Webhook 모듈에서 이 URL을 트리거로 사용합니다.
    """
    secret_error = _automation_webhook_secret_error()
    if secret_error:
        return secret_error

    data = request.get_json(silent=True) or {}
    url = data.get('url', '').strip()
    style_id = data.get('style_id', 'blog_seo')
    language = data.get('language', 'ko')
    callback_url = data.get('callback_url', '')  # Make 응답 URL

    if not url:
        return jsonify({'error': 'url이 필요합니다.'}), 400

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
                    from services.platform.webhook_relay_service import webhook_relay_service
                    payload = {
                        'title': result.get('title', ''),
                        'content': result.get('content', ''),
                        'source_url': url,
                    }
                    webhook_relay_service.send_all(
                        [callback_url],
                        payload,
                        headers={'Content-Type': 'application/json'},
                        timeout=30,
                    )
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
    secret_error = _automation_webhook_secret_error()
    if secret_error:
        return secret_error

    data = request.get_json(silent=True) or {}
    url = (data.get('value1') or data.get('url', '')).strip()
    style_id = data.get('value2') or data.get('style_id', 'blog_seo')
    language = data.get('value3') or data.get('language', 'ko')

    if not url:
        return jsonify({'error': 'value1(URL)이 필요합니다.'}), 400

    try:
        from services.core.content_service import get_transcript
        from services.core.ai_service import create_content
        transcript = get_transcript(url)
        if not transcript:
            return jsonify({'error': '자막을 가져올 수 없습니다.'}), 400

        result = create_content(transcript, style_id, modifiers={'language': language})
        return jsonify({
            'title': result.get('title', ''),
            'content_preview': result.get('content', '')[:500],
            'source_url': url,
        })
    except Exception as e:
        current_app.logger.error(f"IFTTT 트리거 오류: {e}")
        return jsonify({'error': '처리 중 오류가 발생했습니다.'}), 500


# ── Airtable 동기화 (F7-21) ──────────────────────────────────────


@blog_bp.route('/api/sync/airtable', methods=['POST'])
@require_auth
def sync_to_airtable():
    """생성된 콘텐츠를 Airtable에 동기화"""
    from services.integrations.airtable_service import airtable_service

    data = request.get_json(silent=True) or {}
    title = data.get('title', '')
    content = data.get('content', '')
    style = data.get('style', '')
    url = data.get('url', '')
    table_name = data.get('table_name', 'Contents')

    if not title or not content:
        return jsonify({'error': 'title과 content가 필요합니다.'}), 400

    try:
        result = airtable_service.sync_content(title, content, style, url, table_name)
    except Exception as e:
        current_app.logger.error('Airtable sync failed: %s', e, exc_info=True)
        return jsonify({'error': '[서버 오류] Airtable 동기화 중 문제가 발생했습니다.'}), 500

    if not result.get('success'):
        result = sanitize_result_message(
            result,
            'message',
            '[서버 오류] Airtable 동기화에 실패했습니다.'
        )
    status_code = 200 if result.get('success') else 400
    return jsonify(result), status_code


# ── Google Sheets 동기화 (F7-22) ──────────────────────────────────────


@blog_bp.route('/api/sync/gsheets', methods=['POST'])
@require_auth
def sync_to_gsheets():
    """생성된 콘텐츠를 Google Sheets에 동기화"""
    from services.integrations.gsheets_service import gsheets_service

    data = request.get_json(silent=True) or {}
    title = data.get('title', '')
    content = data.get('content', '')
    style = data.get('style', '')
    url = data.get('url', '')
    sheet_name = data.get('sheet_name', 'Contents')

    if not title or not content:
        return jsonify({'error': 'title과 content가 필요합니다.'}), 400

    try:
        result = gsheets_service.sync_content(title, content, style, url, sheet_name)
    except Exception as e:
        current_app.logger.error('Google Sheets sync failed: %s', e, exc_info=True)
        return jsonify({'error': '[서버 오류] Google Sheets 동기화 중 문제가 발생했습니다.'}), 500

    if not result.get('success'):
        result = sanitize_result_message(
            result,
            'message',
            '[서버 오류] Google Sheets 동기화에 실패했습니다.'
        )
    status_code = 200 if result.get('success') else 400
    return jsonify(result), status_code


# ── Webhook Relay (F7-19) ──────────────────────────────────────


@blog_bp.route('/api/webhook-relay', methods=['POST'])
@require_auth
def webhook_relay():
    """다수의 웹훅 URL에 동시 발송"""
    from services.platform.webhook_relay_service import webhook_relay_service

    data = request.get_json(silent=True) or {}
    urls = data.get('urls', [])
    payload = data.get('payload', {})
    headers = data.get('headers', {})
    timeout = clamp_query_int(data.get('timeout'), default=15, min_val=1, max_val=60)

    if not urls:
        return jsonify({'error': 'urls 목록이 필요합니다.'}), 400
    if not payload:
        return jsonify({'error': 'payload가 필요합니다.'}), 400
    if len(urls) > 50:
        return jsonify({'error': 'URL은 최대 50개까지 허용됩니다.'}), 400

    try:
        result = webhook_relay_service.send_all(urls, payload, headers, timeout)
    except Exception as e:
        current_app.logger.error('Webhook relay failed: %s', e, exc_info=True)
        return jsonify({'error': '[서버 오류] 웹훅 전송 중 문제가 발생했습니다.'}), 500

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


# ── Discord 알림 (F6-20) ──────────────────────────────────

@blog_bp.route('/api/integrations/discord/status', methods=['GET'])
@require_auth
def discord_status():
    """Discord 웹훅 설정 상태 조회"""
    from services.integrations.discord_service import DiscordService
    svc = DiscordService()
    return jsonify({'enabled': svc.is_enabled()})


@blog_bp.route('/api/integrations/discord/send', methods=['POST'])
@require_auth
def discord_send():
    """Discord 메시지 전송"""
    from services.integrations.discord_service import DiscordService

    data = request.get_json(silent=True) or {}
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'error': '메시지 내용이 필요합니다.'}), 400

    try:
        svc = DiscordService()
        result = svc.send(content, username=data.get('username', 'Insight Engine'))
        if not result.get('ok'):
            return jsonify({'error': sanitize_integration_error(
                result.get('reason') or result.get('error', '전송 실패'),
                'Discord 메시지 전송에 실패했습니다.'
            )}), 400
        return jsonify({'ok': True})
    except Exception as e:
        return handle_error(str(e))


@blog_bp.route('/api/integrations/discord/send-embed', methods=['POST'])
@require_auth
def discord_send_embed():
    """Discord Embed 메시지 전송"""
    from services.integrations.discord_service import DiscordService

    data = request.get_json(silent=True) or {}
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    if not title or not description:
        return jsonify({'error': 'title과 description이 필요합니다.'}), 400

    try:
        svc = DiscordService()
        result = svc.send_embed(
            title=title,
            description=description,
            color=data.get('color', 0x5865F2),
            fields=data.get('fields'),
        )
        if not result.get('ok'):
            return jsonify({'error': sanitize_integration_error(
                result.get('reason') or result.get('error', '전송 실패'),
                'Discord Embed 전송에 실패했습니다.'
            )}), 400
        return jsonify({'ok': True})
    except Exception as e:
        return handle_error(str(e))


# ── Slack 알림 (F6-19) ──────────────────────────────────

@blog_bp.route('/api/integrations/slack/status', methods=['GET'])
@require_auth
def slack_status():
    """Slack 웹훅 설정 상태 조회"""
    from services.integrations.slack_service import SlackService
    svc = SlackService()
    return jsonify({'enabled': svc.is_enabled()})


@blog_bp.route('/api/integrations/slack/send', methods=['POST'])
@require_auth
def slack_send():
    """Slack 메시지 전송"""
    from services.integrations.slack_service import SlackService

    data = request.get_json(silent=True) or {}
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': '메시지 내용이 필요합니다.'}), 400

    try:
        svc = SlackService()
        result = svc.send(
            text=text,
            channel=data.get('channel', ''),
            username=data.get('username', 'Insight Engine'),
        )
        if not result.get('ok'):
            return jsonify({'error': sanitize_integration_error(
                result.get('reason') or result.get('error', '전송 실패'),
                'Slack 메시지 전송에 실패했습니다.'
            )}), 400
        return jsonify({'ok': True})
    except Exception as e:
        return handle_error(str(e))


@blog_bp.route('/api/integrations/slack/send-blocks', methods=['POST'])
@require_auth
def slack_send_blocks():
    """Slack Block Kit 메시지 전송"""
    from services.integrations.slack_service import SlackService

    data = request.get_json(silent=True) or {}
    blocks = data.get('blocks', [])
    if not blocks:
        return jsonify({'error': 'blocks가 필요합니다.'}), 400

    try:
        svc = SlackService()
        result = svc.send_blocks(blocks=blocks, text=data.get('text', ''))
        if not result.get('ok'):
            return jsonify({'error': sanitize_integration_error(
                result.get('reason') or result.get('error', '전송 실패'),
                'Slack Block 전송에 실패했습니다.'
            )}), 400
        return jsonify({'ok': True})
    except Exception as e:
        return handle_error(str(e))
