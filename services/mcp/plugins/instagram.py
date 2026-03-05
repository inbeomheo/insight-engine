"""
Instagram 발행 플러그인 (F7-17)

Instagram Graph API를 통해 포스트를 게시합니다.
Instagram Business/Creator 계정 + Facebook Access Token 필요.
"""
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request

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
        req = urllib.request.Request(container_url, method='POST')

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                container_data = json.loads(resp.read())
            container_id = container_data.get('id', '')
            if not container_id:
                return {'success': False, 'message': 'Instagram 미디어 컨테이너 생성 실패', 'url': None}

            # Step 2: 발행
            publish_params = urllib.parse.urlencode({
                'creation_id': container_id,
                'access_token': access_token,
            })
            publish_url = f'{GRAPH_API_BASE}/{account_id}/media_publish?{publish_params}'
            req2 = urllib.request.Request(publish_url, method='POST')
            with urllib.request.urlopen(req2, timeout=30) as resp2:
                publish_data = json.loads(resp2.read())

            media_id = publish_data.get('id', '')
            return {
                'success': True,
                'message': f"Instagram 포스트 게시 완료 (미디어 ID: {media_id})",
                'url': f'https://www.instagram.com/p/{media_id}/' if media_id else None,
            }

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='replace')
            logger.error(f"Instagram HTTP 오류: {e.code} — {error_body}")
            return {'success': False, 'message': f'Instagram API 오류: {e.code}', 'url': None}
        except Exception as e:
            logger.error(f"Instagram 발행 실패: {e}")
            return {'success': False, 'message': f'Instagram 발행 실패: {str(e)}', 'url': None}
