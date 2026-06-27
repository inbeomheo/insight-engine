"""
Instagram 발행 플러그인 (F7-17)

Instagram Graph API를 통해 포스트를 게시합니다.
Instagram Business/Creator 계정 + Facebook Access Token 필요.
"""
import logging
import os
import urllib.parse

import requests

from ..plugin_interface import MCPPlugin

logger = logging.getLogger(__name__)

GRAPH_API_BASE = 'https://graph.facebook.com/v18.0'


class InstagramPlugin(MCPPlugin):
    """Instagram에 콘텐츠를 발행하는 플러그인"""

    @property
    def name(self) -> str:
        return "Instagram"

    @property
    def description(self) -> str:
        return "Instagram Business 계정에 포스트를 게시합니다"

    def schema(self) -> dict:
        return {
            'type': 'object',
            'properties': {
                'access_token': {
                    'type': 'string',
                    'description': 'Facebook Graph API 액세스 토큰',
                },
                'instagram_account_id': {
                    'type': 'string',
                    'description': 'Instagram Business 계정 ID',
                },
                'image_url': {
                    'type': 'string',
                    'description': '게시할 이미지 URL (필수 — Instagram은 이미지 필수)',
                },
            },
            'required': ['access_token', 'instagram_account_id', 'image_url'],
        }

    def execute(self, content: str, title: str, **kwargs) -> dict:
        access_token = kwargs.get('access_token') or os.getenv('INSTAGRAM_ACCESS_TOKEN', '')
        account_id = kwargs.get('instagram_account_id') or os.getenv('INSTAGRAM_ACCOUNT_ID', '')
        image_url = kwargs.get('image_url') or os.getenv('INSTAGRAM_DEFAULT_IMAGE_URL', '')

        if not access_token:
            return {'success': False, 'message': 'Instagram 액세스 토큰이 필요합니다.', 'url': None}
        if not account_id:
            return {'success': False, 'message': 'Instagram 계정 ID가 필요합니다.', 'url': None}
        if not image_url:
            return {'success': False, 'message': 'Instagram은 이미지 URL이 필요합니다.', 'url': None}

        # 캡션: 제목 + 내용 (최대 2200자)
        caption = f"{title}\n\n{content}"[:2200]

        # Step 1: 미디어 컨테이너 생성
        container_params = urllib.parse.urlencode({
            'image_url': image_url,
            'caption': caption,
            'access_token': access_token,
        })
        container_url = f'{GRAPH_API_BASE}/{account_id}/media?{container_params}'

        try:
            container_resp = requests.post(
                container_url,
                timeout=30,
                allow_redirects=False,
            )
            if 300 <= container_resp.status_code < 400:
                return {'success': False, 'message': f'Instagram 리다이렉트 차단: {container_resp.status_code}', 'url': None}
            if container_resp.status_code >= 400:
                logger.error(f"Instagram HTTP 오류: {container_resp.status_code} — {container_resp.text}")
                return {'success': False, 'message': f'Instagram API 오류: {container_resp.status_code}', 'url': None}
            container_data = container_resp.json()
            container_id = container_data.get('id', '')
            if not container_id:
                return {'success': False, 'message': 'Instagram 미디어 컨테이너 생성 실패', 'url': None}

            # Step 2: 발행
            publish_params = urllib.parse.urlencode({
                'creation_id': container_id,
                'access_token': access_token,
            })
            publish_url = f'{GRAPH_API_BASE}/{account_id}/media_publish?{publish_params}'
            publish_resp = requests.post(
                publish_url,
                timeout=30,
                allow_redirects=False,
            )
            if 300 <= publish_resp.status_code < 400:
                return {'success': False, 'message': f'Instagram 리다이렉트 차단: {publish_resp.status_code}', 'url': None}
            if publish_resp.status_code >= 400:
                logger.error(f"Instagram HTTP 오류: {publish_resp.status_code} — {publish_resp.text}")
                return {'success': False, 'message': f'Instagram API 오류: {publish_resp.status_code}', 'url': None}
            publish_data = publish_resp.json()

            media_id = publish_data.get('id', '')
            return {
                'success': True,
                'message': f"Instagram 포스트 게시 완료 (미디어 ID: {media_id})",
                'url': f'https://www.instagram.com/p/{media_id}/' if media_id else None,
            }

        except requests.RequestException as e:
            logger.error(f"Instagram 발행 실패: {e}")
            return {'success': False, 'message': f'Instagram 발행 실패: {str(e)}', 'url': None}
