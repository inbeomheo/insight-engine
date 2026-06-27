"""
Discord 봇 서비스 (F7-03)

Discord Interactions Endpoint (webhook 기반)를 통해
/generate 슬래시 명령어로 콘텐츠를 생성합니다.
DISCORD_BOT_TOKEN, DISCORD_PUBLIC_KEY 환경변수 필요.
"""
import logging
import os
import re

import requests

logger = logging.getLogger(__name__)

YOUTUBE_URL_RE = re.compile(
    r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]+'
)

# Discord Interaction 타입
INTERACTION_PING = 1
INTERACTION_APPLICATION_COMMAND = 2

# Discord Interaction 응답 타입
RESPONSE_PONG = 1
RESPONSE_CHANNEL_MESSAGE = 4
RESPONSE_DEFERRED_MESSAGE = 5


class DiscordBotService:
    """Discord Interactions 웹훅 처리 서비스"""

    def __init__(self):
        self.bot_token: str = os.getenv('DISCORD_BOT_TOKEN', '')
        self.public_key: str = os.getenv('DISCORD_PUBLIC_KEY', '')

    def verify_signature(self, body: bytes, timestamp: str, signature: str) -> bool:
        """Ed25519 서명 검증"""
        if not self.public_key:
            return os.getenv('FLASK_ENV', '').strip().lower() != 'production'

        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

            import binascii

            pub_key = Ed25519PublicKey.from_public_bytes(
                binascii.unhexlify(self.public_key)
            )
            pub_key.verify(
                binascii.unhexlify(signature),
                (timestamp.encode() + body),
            )
            return True
        except ImportError:
            logger.warning("cryptography 패키지 미설치 — 서명 검증 건너뜀")
            return os.getenv('FLASK_ENV', '').strip().lower() != 'production'
        except Exception:
            return False

    def handle_interaction(self, payload: dict) -> dict:
        """Discord 인터랙션 처리

        Returns:
            Discord Interaction Response 형식의 dict
        """
        interaction_type = payload.get('type')

        # Ping 응답
        if interaction_type == INTERACTION_PING:
            return {'type': RESPONSE_PONG}

        # 슬래시 명령어
        if interaction_type == INTERACTION_APPLICATION_COMMAND:
            return self._handle_command(payload)

        return {'type': RESPONSE_CHANNEL_MESSAGE, 'data': {'content': '알 수 없는 인터랙션입니다.'}}

    def _handle_command(self, payload: dict) -> dict:
        """슬래시 명령어 처리"""
        data = payload.get('data', {})
        command_name = data.get('name', '')

        if command_name == 'generate':
            options = {opt['name']: opt['value'] for opt in data.get('options', [])}
            url = options.get('url', '')

            if not YOUTUBE_URL_RE.search(url):
                return {
                    'type': RESPONSE_CHANNEL_MESSAGE,
                    'data': {'content': '❌ YouTube URL을 입력해주세요.'},
                }

            style = options.get('style', 'blog_seo')
            logger.info(f"Discord 봇: /generate 명령어 — {url} (스타일: {style})")

            return {
                'type': RESPONSE_CHANNEL_MESSAGE,
                'data': {
                    'content': (
                        f'🎬 **콘텐츠 생성을 요청했습니다.**\n'
                        f'URL: `{url}`\n'
                        f'스타일: `{style}`\n\n'
                        f'Insight Engine 서버에서 결과를 확인하세요.'
                    ),
                },
            }

        return {
            'type': RESPONSE_CHANNEL_MESSAGE,
            'data': {'content': f'❓ 알 수 없는 명령어: `{command_name}`'},
        }

    def register_commands(self, application_id: str) -> bool:
        """Discord 슬래시 명령어 등록"""
        if not self.bot_token:
            logger.warning("DISCORD_BOT_TOKEN이 설정되지 않았습니다.")
            return False

        commands = [
            {
                'name': 'generate',
                'description': 'YouTube URL로 AI 콘텐츠를 생성합니다.',
                'options': [
                    {
                        'name': 'url',
                        'description': 'YouTube 영상 URL',
                        'type': 3,  # STRING
                        'required': True,
                    },
                    {
                        'name': 'style',
                        'description': '콘텐츠 스타일',
                        'type': 3,
                        'required': False,
                        'choices': [
                            {'name': '블로그 SEO', 'value': 'blog_seo'},
                            {'name': '요약', 'value': 'summary'},
                            {'name': 'SNS 포스트', 'value': 'sns_post'},
                        ],
                    },
                ],
            }
        ]

        try:
            resp = requests.put(
                f'https://discord.com/api/v10/applications/{application_id}/commands',
                json=commands,
                headers={
                    'Authorization': f'Bot {self.bot_token}',
                    'Content-Type': 'application/json',
                },
                timeout=15,
                allow_redirects=False,
            )
            if 300 <= resp.status_code < 400:
                logger.error("Discord 명령어 등록 리다이렉트 차단: %s", resp.status_code)
                return False
            resp.raise_for_status()
            logger.info(f"Discord 명령어 등록 완료: {resp.status_code}")
            return True
        except Exception as e:
            logger.error(f"Discord 명령어 등록 실패: {e}")
            return False

    @property
    def is_configured(self) -> bool:
        """Discord 봇 토큰 및 Public Key 설정 여부"""
        return bool(self.bot_token and self.public_key)


discord_bot_service = DiscordBotService()
