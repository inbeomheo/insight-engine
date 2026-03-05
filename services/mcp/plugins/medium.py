"""
Medium 발행 플러그인

Medium API로 Draft 포스트를 생성합니다.
"""
import logging

import requests

from ..plugin_interface import MCPPlugin

logger = logging.getLogger(__name__)

MEDIUM_API_URL = 'https://api.medium.com/v1'


class MediumPlugin(MCPPlugin):
    """Medium에 콘텐츠를 발행하는 플러그인"""

    @property
    def name(self) -> str:
        return "Medium"

    @property
    def description(self) -> str:
        return "Medium에 Draft 포스트를 생성합니다"

    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "api_token": {
                    "type": "string",
                    "description": "Medium Integration Token",
                },
                "publish_status": {
                    "type": "string",
                    "enum": ["draft", "public", "unlisted"],
                    "description": "발행 상태 (기본: draft)",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "태그 목록 (최대 5개)",
                },
            },
            "required": ["api_token"],
        }

    def execute(self, content: str, title: str, **kwargs) -> dict:
        api_token = kwargs.get('api_token', '')
        if not api_token:
            return {'success': False, 'message': 'Medium API 토큰이 필요합니다.', 'url': None}

        headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json',
        }

        # 사용자 ID 조회
        try:
            me_resp = requests.get(f'{MEDIUM_API_URL}/me', headers=headers, timeout=15)
            if me_resp.status_code != 200:
                return {'success': False, 'message': 'Medium 인증 실패', 'url': None}
            user_id = me_resp.json()['data']['id']
        except requests.RequestException as e:
            logger.error(f"Medium 사용자 조회 실패: {e}")
            return {'success': False, 'message': f'Medium 연결 실패: {str(e)}', 'url': None}

        # 포스트 생성
        tags = kwargs.get('tags', [])[:5]
        publish_status = kwargs.get('publish_status', 'draft')

        payload = {
            'title': title,
            'contentFormat': 'markdown',
            'content': f'# {title}\n\n{content}',
            'publishStatus': publish_status,
        }
        if tags:
            payload['tags'] = tags

        try:
            post_resp = requests.post(
                f'{MEDIUM_API_URL}/users/{user_id}/posts',
                json=payload,
                headers=headers,
                timeout=30,
            )
            if post_resp.status_code in (200, 201):
                post_data = post_resp.json()['data']
                return {
                    'success': True,
                    'message': f'Medium {publish_status} 포스트 생성 완료',
                    'url': post_data.get('url'),
                }
            else:
                error_msg = post_resp.json().get('errors', [{}])[0].get('message', post_resp.text)
                return {'success': False, 'message': f'Medium API 오류: {error_msg}', 'url': None}
        except requests.RequestException as e:
            logger.error(f"Medium 포스트 생성 실패: {e}")
            return {'success': False, 'message': f'Medium 연결 실패: {str(e)}', 'url': None}
