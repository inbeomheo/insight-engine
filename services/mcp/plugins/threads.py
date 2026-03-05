"""
Threads 발행 플러그인 (F7-18)

Threads API (Meta Graph API 기반)를 통해 포스트를 게시합니다.
Threads API Access Token이 필요합니다.
"""
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request

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
        req = urllib.request.Request(f'{container_url}?{encoded}', method='POST')

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                container_data = json.loads(resp.read())
            container_id = container_data.get('id', '')
            if not container_id:
                return {'success': False, 'message': 'Threads 컨테이너 생성 실패', 'url': None}

            # Step 2: 발행
            publish_url = f'{THREADS_API_BASE}/{user_id}/threads_publish'
            publish_params = urllib.parse.urlencode({
                'creation_id': container_id,
                'access_token': access_token,
            })
            req2 = urllib.request.Request(f'{publish_url}?{publish_params}', method='POST')
            with urllib.request.urlopen(req2, timeout=30) as resp2:
                publish_data = json.loads(resp2.read())

            post_id = publish_data.get('id', '')
            return {
                'success': True,
                'message': f"Threads 포스트 게시 완료 (ID: {post_id})",
                'url': None,  # Threads API는 직접 URL 미제공
            }

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='replace')
            logger.error(f"Threads HTTP 오류: {e.code} — {error_body}")
            return {'success': False, 'message': f'Threads API 오류: {e.code}', 'url': None}
        except Exception as e:
            logger.error(f"Threads 발행 실패: {e}")
            return {'success': False, 'message': f'Threads 발행 실패: {str(e)}', 'url': None}
