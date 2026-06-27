"""
Threads 발행 플러그인 (F7-18)

Threads API (Meta Graph API 기반)를 통해 포스트를 게시합니다.
Threads API Access Token이 필요합니다.
"""
import logging
import os
import urllib.parse

import requests

from ..plugin_interface import MCPPlugin

logger = logging.getLogger(__name__)

THREADS_API_BASE = 'https://graph.threads.net/v1.0'


class ThreadsPlugin(MCPPlugin):
    """Threads에 콘텐츠를 발행하는 플러그인"""

    @property
    def name(self) -> str:
        return "Threads"

    @property
    def description(self) -> str:
        return "Meta Threads에 포스트를 게시합니다"

    def schema(self) -> dict:
        return {
            'type': 'object',
            'properties': {
                'access_token': {
                    'type': 'string',
                    'description': 'Threads API 액세스 토큰',
                },
                'user_id': {
                    'type': 'string',
                    'description': 'Threads 사용자 ID',
                },
                'media_type': {
                    'type': 'string',
                    'enum': ['TEXT', 'IMAGE'],
                    'description': '미디어 타입 (기본: TEXT)',
                    'default': 'TEXT',
                },
                'image_url': {
                    'type': 'string',
                    'description': '이미지 URL (media_type=IMAGE 시)',
                },
            },
            'required': ['access_token', 'user_id'],
        }

    def execute(self, content: str, title: str, **kwargs) -> dict:
        access_token = kwargs.get('access_token') or os.getenv('THREADS_ACCESS_TOKEN', '')
        user_id = kwargs.get('user_id') or os.getenv('THREADS_USER_ID', '')

        if not access_token:
            return {'success': False, 'message': 'Threads 액세스 토큰이 필요합니다.', 'url': None}
        if not user_id:
            return {'success': False, 'message': 'Threads 사용자 ID가 필요합니다.', 'url': None}

        media_type = kwargs.get('media_type', 'TEXT')
        image_url = kwargs.get('image_url', '')

        # 게시할 텍스트 (최대 500자)
        post_text = f"{title}\n\n{content}"[:500]

        # Step 1: 미디어 컨테이너 생성
        container_payload: dict = {
            'media_type': media_type,
            'text': post_text,
            'access_token': access_token,
        }
        if media_type == 'IMAGE' and image_url:
            container_payload['image_url'] = image_url

        container_url = f'{THREADS_API_BASE}/{user_id}/threads'
        encoded = urllib.parse.urlencode(container_payload)

        try:
            container_resp = requests.post(
                f'{container_url}?{encoded}',
                timeout=30,
                allow_redirects=False,
            )
            if 300 <= container_resp.status_code < 400:
                return {'success': False, 'message': f'Threads 리다이렉트 차단: {container_resp.status_code}', 'url': None}
            if container_resp.status_code >= 400:
                logger.error(f"Threads HTTP 오류: {container_resp.status_code} — {container_resp.text}")
                return {'success': False, 'message': f'Threads API 오류: {container_resp.status_code}', 'url': None}
            container_data = container_resp.json()
            container_id = container_data.get('id', '')
            if not container_id:
                return {'success': False, 'message': 'Threads 컨테이너 생성 실패', 'url': None}

            # Step 2: 발행
            publish_url = f'{THREADS_API_BASE}/{user_id}/threads_publish'
            publish_params = urllib.parse.urlencode({
                'creation_id': container_id,
                'access_token': access_token,
            })
            publish_resp = requests.post(
                f'{publish_url}?{publish_params}',
                timeout=30,
                allow_redirects=False,
            )
            if 300 <= publish_resp.status_code < 400:
                return {'success': False, 'message': f'Threads 리다이렉트 차단: {publish_resp.status_code}', 'url': None}
            if publish_resp.status_code >= 400:
                logger.error(f"Threads HTTP 오류: {publish_resp.status_code} — {publish_resp.text}")
                return {'success': False, 'message': f'Threads API 오류: {publish_resp.status_code}', 'url': None}
            publish_data = publish_resp.json()

            post_id = publish_data.get('id', '')
            return {
                'success': True,
                'message': f"Threads 포스트 게시 완료 (ID: {post_id})",
                'url': None,  # Threads API는 직접 URL 미제공
            }

        except requests.RequestException as e:
            logger.error(f"Threads 발행 실패: {e}")
            return {'success': False, 'message': f'Threads 발행 실패: {str(e)}', 'url': None}
