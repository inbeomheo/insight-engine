"""
Slack Webhook 알림 서비스 (F6-19)
Slack Incoming Webhook으로 알림 전송
"""
import os
from typing import Any

import requests

from services.core.logging_config import ServiceLogger
from services.integrations._shared import disabled_result, webhook_result

logger = ServiceLogger('SlackService')

SLACK_WEBHOOK_URL: str = os.getenv('SLACK_WEBHOOK_URL', '')
SLACK_TIMEOUT_SEC: int = int(os.getenv('SLACK_TIMEOUT_SEC', '5'))


class SlackService:
    """Slack Incoming Webhook 클라이언트"""

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or SLACK_WEBHOOK_URL

    def is_enabled(self) -> bool:
        """Slack 웹훅 URL 설정 여부"""
        return bool(self.webhook_url)

    def send(self, text: str, channel: str = '', username: str = 'Insight Engine',
             icon_emoji: str = ':robot_face:') -> dict[str, Any]:
        """단순 텍스트 메시지 전송"""
        if not self.is_enabled():
            return disabled_result('SLACK_WEBHOOK_URL 미설정')

        payload: dict[str, Any] = {
            'text': text,
            'username': username,
            'icon_emoji': icon_emoji,
        }
        if channel:
            payload['channel'] = channel

        try:
            resp = requests.post(
                self.webhook_url, json=payload, timeout=SLACK_TIMEOUT_SEC
            )
            return webhook_result(resp, (200,))
        except Exception as e:
            logger.error(f'Slack 전송 실패: {e}')
            return {'ok': False, 'error': str(e)}

    def send_blocks(self, blocks: list[dict], text: str = '') -> dict[str, Any]:
        """Block Kit 메시지 전송"""
        if not self.is_enabled():
            return disabled_result('SLACK_WEBHOOK_URL 미설정')

        payload = {'blocks': blocks}
        if text:
            payload['text'] = text

        try:
            resp = requests.post(
                self.webhook_url, json=payload, timeout=SLACK_TIMEOUT_SEC
            )
            return webhook_result(resp, (200,))
        except Exception as e:
            logger.error(f'Slack Block 전송 실패: {e}')
            return {'ok': False, 'error': str(e)}

    def notify_generation_complete(self, title: str, style: str,
                                   model: str, tokens: int) -> dict[str, Any]:
        """콘텐츠 생성 완료 알림 (포맷된 메시지)"""
        text = (
            f':white_check_mark: *콘텐츠 생성 완료*\n'
            f'• 제목: {title}\n'
            f'• 스타일: `{style}` | 모델: `{model}`\n'
            f'• 토큰: {tokens:,}'
        )
        return self.send(text)

    def notify_anomaly(self, metric: str, value: float, z_score: float) -> dict[str, Any]:
        """이상 탐지 알림"""
        text = (
            f':warning: *이상 탐지*\n'
            f'• 지표: `{metric}`\n'
            f'• 값: {value} (z-score: {z_score})'
        )
        return self.send(text)
