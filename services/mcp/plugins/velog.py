"""
Velog 발행 플러그인 (F7-12)

Velog GraphQL API를 통해 포스트를 작성합니다.
Velog Access Token이 필요합니다.
"""
import json
import logging
import os
import urllib.error
import urllib.request

from ..plugin_interface import MCPPlugin

logger = logging.getLogger(__name__)

VELOG_GQL_URL = 'https://v3.velog.io/graphql'


class VelogPlugin(MCPPlugin):
    """Velog에 콘텐츠를 발행하는 플러그인"""

    @property
    def name(self) -> str:
        return "Velog"

    @property
    def description(self) -> str:
        return "Velog에 포스트를 발행합니다"

    def schema(self) -> dict:
        return {
            'type': 'object',
            'properties': {
                'access_token': {
                    'type': 'string',
                    'description': 'Velog 액세스 토큰',
                },
                'tags': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': '태그 목록',
                },
                'is_private': {
                    'type': 'boolean',
                    'description': '비공개 여부 (기본: 공개)',
                    'default': False,
                },
                'series_id': {
                    'type': 'string',
                    'description': '시리즈 ID (선택)',
                },
            },
            'required': ['access_token'],
        }

    def execute(self, content: str, title: str, **kwargs) -> dict:
        access_token = kwargs.get('access_token') or os.getenv('VELOG_ACCESS_TOKEN', '')

        if not access_token:
            return {'success': False, 'message': 'Velog 액세스 토큰이 필요합니다.', 'url': None}

        tags = kwargs.get('tags', [])
        is_private = kwargs.get('is_private', False)
        series_id = kwargs.get('series_id')

        mutation = """
        mutation WritePost($input: WritePostInput!) {
          writePost(input: $input) {
            id
            url_slug
            user {
              username
            }
          }
        }
        """

        variables = {
            'input': {
                'title': title,
                'body': content,
                'tags': tags,
                'is_private': is_private,
                'is_temp': False,
            }
        }
        if series_id:
            variables['input']['series_id'] = series_id

        payload = json.dumps({'query': mutation, 'variables': variables}).encode()
        req = urllib.request.Request(
            VELOG_GQL_URL,
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'Authorization': access_token,
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())

            if 'errors' in data:
                error_msg = data['errors'][0].get('message', '알 수 없는 오류')
                return {'success': False, 'message': f'Velog API 오류: {error_msg}', 'url': None}

            post_data = data.get('data', {}).get('writePost', {})
            username = post_data.get('user', {}).get('username', '')
            url_slug = post_data.get('url_slug', '')
            post_id = post_data.get('id', '')

            post_url = f'https://velog.io/@{username}/{url_slug}' if username and url_slug else None

            return {
                'success': True,
                'message': f"Velog 발행 완료 (ID: {post_id})",
                'url': post_url,
            }

        except urllib.error.HTTPError as e:
            logger.error(f"Velog HTTP 오류: {e.code}")
            return {'success': False, 'message': f'Velog HTTP 오류: {e.code}', 'url': None}
        except Exception as e:
            logger.error(f"Velog 발행 실패: {e}")
            return {'success': False, 'message': f'Velog 발행 실패: {str(e)}', 'url': None}
