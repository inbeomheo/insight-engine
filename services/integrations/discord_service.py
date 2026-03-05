"""
Discord Webhook 알림 서비스 (F6-20)
Discord Incoming Webhook으로 알림 전송
"""
import os
from typing import Any

import requests

from services.logging_config import ServiceLogger

logger = ServiceLogger('DiscordService')

DISCORD_WEBHOOK_URL: str = os.getenv('DISCORD_WEBHOOK_URL', '')
DISCORD_TIMEOUT_SEC: int = int(os.getenv('DISCORD_TIMEOUT_SEC', '5'))


class DiscordService:
    """Discord Incoming Webhook 클라이언트"""

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or DISCORD_WEBHOOK_URL

    def is_enabled(self) -> bool:
        return bool(self.webhook_url)

    def send(self, content: str, username: str = 'Insight Engine') -> dict[str, Any]:
        """단순 텍스트 메시지 전송"""
        if not self.is_enabled():
            return {'ok': False, 'reason': 'DISCORD_WEBHOOK_URL 미설정'}

        payload = {'content': content, 'username': username}
        try:
            resp = requests.post(
                self.webhook_url, json=payload, timeout=DISCORD_TIMEOUT_SEC
            )
            # Discord는 성공 시 204 반환
            if resp.status_code in (200, 204):
                return {'ok': True}
            return {'ok': False, 'status': resp.status_code, 'body': resp.text}
        except Exception as e:
            logger.error(f'Discord 전송 실패: {e}')
            return {'ok': False, 'error': str(e)}

    def send_embed(self, title: str, description: str,
                   color: int = 0x5865F2,
                   fields: list[dict] | None = None) -> dict[str, Any]:
        """Embed 메시지 전송"""
        if not self.is_enabled():
            return {'ok': False, 'reason': 'DISCORD_WEBHOOK_URL 미설정'}

        embed: dict[str, Any] = {
            'title': title,
            'description': description,
            'color': color,
        }
        if fields:
            embed['fields'] = fields

        payload = {'embeds': [embed]}
        try:
            resp = requests.post(
                self.webhook_url, json=payload, timeout=DISCORD_TIMEOUT_SEC
            )
            if resp.status_code in (200, 204):
                return {'ok': True}
            return {'ok': False, 'status': resp.status_code, 'body': resp.text}
        except Exception as e:
            logger.error(f'Discord Embed 전송 실패: {e}')
            return {'ok': False, 'error': str(e)}

    def notify_generation_complete(self, title: str, style: str,
                                   model: str, tokens: int) -> dict[str, Any]:
        """콘텐츠 생성 완료 알림 (Embed 형식)"""
        return self.send_embed(
            title='콘텐츠 생성 완료',
            description=f'**{title}**',
            color=0x57F287,
            fields=[
                {'name': '스타일', 'value': style, 'inline': True},
                {'name': '모델', 'value': model, 'inline': True},
                {'name': '토큰', 'value': f'{tokens:,}', 'inline': True},
            ],
        )

    def notify_anomaly(self, metric: str, value: float, z_score: float) -> dict[str, Any]:
        """이상 탐지 알림"""
        return self.send_embed(
            title='이상 탐지',
            description=f'지표 `{metric}` 이상값 감지',
            color=0xED4245,
            fields=[
                {'name': '값', 'value': str(value), 'inline': True},
                {'name': 'Z-score', 'value': str(z_score), 'inline': True},
            ],
        )
