"""
Twitter/X 발행 플러그인 (F7-16)

Twitter API v2를 통해 트윗을 게시합니다.
Bearer Token 또는 OAuth1 인증이 필요합니다.
"""
import json
import logging
import os
import urllib.error
import urllib.request

from ..plugin_interface import MCPPlugin

logger = logging.getLogger(__name__)

TWITTER_API_BASE = 'https://api.twitter.com/2'


class TwitterPlugin(MCPPlugin):
    """Twitter/X에 콘텐츠를 발행하는 플러그인"""

    @property
    def name(self) -> str:
        return "Twitter/X"

    @property
    def description(self) -> str:
        return "Twitter/X에 트윗 또는 스레드를 게시합니다"

    def schema(self) -> dict:
        return {
            'type': 'object',
            'properties': {
                'bearer_token': {
                    'type': 'string',
                    'description': 'Twitter API v2 Bearer Token',
                },
                'as_thread': {
                    'type': 'boolean',
                    'description': '280자 초과 시 스레드로 분할 (기본: true)',
                    'default': True,
                },
            },
            'required': ['bearer_token'],
        }

    def execute(self, content: str, title: str, **kwargs) -> dict:
        bearer_token = kwargs.get('bearer_token') or os.getenv('TWITTER_BEARER_TOKEN', '')

        if not bearer_token:
            return {'success': False, 'message': 'Twitter Bearer Token이 필요합니다.', 'url': None}

        as_thread = kwargs.get('as_thread', True)
        # 첫 트윗: 제목 포함
        first_tweet = f"{title}\n\n{content}"[:280]
        remaining = content[max(0, 280 - len(title) - 2):]

        tweet_id = self._post_tweet(bearer_token, first_tweet)
        if not tweet_id:
            return {'success': False, 'message': 'Twitter 트윗 게시 실패', 'url': None}

        # 스레드 처리
        if as_thread and remaining:
            chunks = [remaining[i:i+280] for i in range(0, len(remaining), 280)]
            reply_to = tweet_id
            for chunk in chunks[:10]:  # 최대 10개 스레드
                next_id = self._post_tweet(bearer_token, chunk, reply_to_id=reply_to)
                if next_id:
                    reply_to = next_id

        tweet_url = f'https://twitter.com/i/web/status/{tweet_id}'
        return {
            'success': True,
            'message': f"Twitter 트윗 게시 완료 (ID: {tweet_id})",
            'url': tweet_url,
        }

    def _post_tweet(self, bearer_token: str, text: str, reply_to_id: str = None) -> str:
        """트윗 게시 후 트윗 ID 반환"""
        payload: dict = {'text': text}
        if reply_to_id:
            payload['reply'] = {'in_reply_to_tweet_id': reply_to_id}

        req = urllib.request.Request(
            f'{TWITTER_API_BASE}/tweets',
            data=json.dumps(payload).encode(),
            headers={
                'Authorization': f'Bearer {bearer_token}',
                'Content-Type': 'application/json',
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                return data.get('data', {}).get('id', '')
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='replace')
            logger.error(f"Twitter HTTP 오류: {e.code} — {error_body}")
            return ''
        except Exception as e:
            logger.error(f"Twitter 트윗 게시 실패: {e}")
            return ''
