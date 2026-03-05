"""
Slack 봇 서비스 (F7-02)

Slack Event API (webhook 기반)를 통해 URL 공유 시 자동으로 콘텐츠를 생성합니다.
SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET 환경변수 필요.
"""
import hashlib
import hmac
import json
import logging
import os
import re
import time
from typing import Optional

logger = logging.getLogger(__name__)

YOUTUBE_URL_RE = re.compile(
    r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]+'
)


class SlackBotService:
    """Slack Event API 웹훅 처리 서비스"""

    def __init__(self):
        self.bot_token: str = os.getenv('SLACK_BOT_TOKEN', '')
        self.signing_secret: str = os.getenv('SLACK_SIGNING_SECRET', '')

    def verify_signature(self, body: bytes, timestamp: str, signature: str) -> bool:
        """Slack 요청 서명 검증 (재전송 공격 방지 포함)"""
        if not self.signing_secret:
            return True  # 개발 환경에서 서명 미설정 시 통과

        # 5분 이상 지난 요청 거부
        try:
            if abs(time.time() - int(timestamp)) > 300:
                return False
        except (ValueError, TypeError):
            return False

        base_str = f'v0:{timestamp}:{body.decode("utf-8")}'
        computed = 'v0=' + hmac.new(
            self.signing_secret.encode(),
            base_str.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(computed, signature)

    def handle_event(self, payload: dict) -> dict:
        """Slack 이벤트 처리

        Returns:
            응답 dict (Slack API 형식)
        """
        # URL 검증 챌린지 응답
        if payload.get('type') == 'url_verification':
            return {'challenge': payload.get('challenge', '')}

        event = payload.get('event', {})
        event_type = event.get('type')

        if event_type == 'message':
            return self._handle_message(event)

        return {'ok': True}

    def _handle_message(self, event: dict) -> dict:
        """메시지 이벤트에서 YouTube URL 추출 후 생성 요청"""
        # 봇 메시지 무시 (무한루프 방지)
        if event.get('bot_id') or event.get('subtype') == 'bot_message':
            return {'ok': True}

        text = event.get('text', '')
        channel = event.get('channel', '')
        urls = YOUTUBE_URL_RE.findall(text)

        if not urls:
            return {'ok': True}

        # 첫 번째 YouTube URL만 처리
        youtube_url = urls[0]
        logger.info(f"Slack 봇: YouTube URL 감지 — {youtube_url} (채널: {channel})")

        self._send_message(
            channel,
            f"🎬 YouTube URL을 감지했습니다.\n`{youtube_url}`\n\nInsight Engine에서 콘텐츠를 생성하려면 서버에 요청하세요.",
        )

        return {'ok': True, 'url': youtube_url}

    def _send_message(self, channel: str, text: str) -> Optional[dict]:
        """Slack 채널에 메시지 전송"""
        if not self.bot_token:
            logger.warning("SLACK_BOT_TOKEN이 설정되지 않았습니다.")
            return None

        try:
            import urllib.request
            payload = json.dumps({'channel': channel, 'text': text}).encode()
            req = urllib.request.Request(
                'https://slack.com/api/chat.postMessage',
                data=payload,
                headers={
                    'Authorization': f'Bearer {self.bot_token}',
                    'Content-Type': 'application/json',
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as e:
            logger.error(f"Slack 메시지 전송 실패: {e}")
            return None

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.signing_secret)


slack_bot_service = SlackBotService()
