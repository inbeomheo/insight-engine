"""
Tistory 발행 플러그인 (F7-11)

Tistory Open API를 통해 블로그 포스트를 작성합니다.
OAuth2 액세스 토큰이 필요합니다.
"""
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request

from ..plugin_interface import MCPPlugin

logger = logging.getLogger(__name__)

TISTORY_API_BASE = 'https://www.tistory.com/apis'


class TistoryPlugin(MCPPlugin):
    """Tistory 블로그에 콘텐츠를 발행하는 플러그인"""

    @property
    def name(self) -> str:
        return "Tistory"

    @property
    def description(self) -> str:
        return "Tistory 블로그에 포스트를 발행합니다"

    def schema(self) -> dict:
        return {
            'type': 'object',
            'properties': {
                'access_token': {
                    'type': 'string',
                    'description': 'Tistory OAuth2 액세스 토큰',
                },
                'blog_name': {
                    'type': 'string',
                    'description': '블로그 이름 (tistory.com 앞부분)',
                },
                'visibility': {
                    'type': 'string',
                    'enum': ['0', '1', '3'],
                    'description': '공개 설정 (0: 비공개, 1: 보호, 3: 공개)',
                    'default': '3',
                },
                'category': {
                    'type': 'string',
                    'description': '카테고리 ID',
                    'default': '0',
                },
                'tag': {
                    'type': 'string',
                    'description': '태그 (쉼표 구분)',
                },
            },
            'required': ['access_token', 'blog_name'],
        }

    def execute(self, content: str, title: str, **kwargs) -> dict:
        access_token = kwargs.get('access_token') or os.getenv('TISTORY_ACCESS_TOKEN', '')
        blog_name = kwargs.get('blog_name') or os.getenv('TISTORY_BLOG_NAME', '')

        if not access_token:
            return {'success': False, 'message': 'Tistory 액세스 토큰이 필요합니다.', 'url': None}
        if not blog_name:
            return {'success': False, 'message': 'Tistory 블로그 이름이 필요합니다.', 'url': None}

        params = {
            'access_token': access_token,
            'output': 'json',
            'blogName': blog_name,
            'title': title,
            'content': f'<p>{content.replace(chr(10), "</p><p>")}</p>',
            'visibility': kwargs.get('visibility', '3'),
            'categoryId': kwargs.get('category', '0'),
            'tag': kwargs.get('tag', ''),
        }

        url = f'{TISTORY_API_BASE}/post/write?' + urllib.parse.urlencode(params)

        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())

            tistory = data.get('tistory', {})
            status = tistory.get('status', '0')

            if status == '200':
                post_url = tistory.get('url', '')
                post_id = tistory.get('postId', '')
                return {
                    'success': True,
                    'message': f"Tistory 발행 완료 (포스트 ID: {post_id})",
                    'url': post_url,
                }
            else:
                error_msg = tistory.get('error_message', '알 수 없는 오류')
                return {'success': False, 'message': f'Tistory API 오류: {error_msg}', 'url': None}

        except urllib.error.HTTPError as e:
            logger.error(f"Tistory HTTP 오류: {e.code}")
            return {'success': False, 'message': f'Tistory HTTP 오류: {e.code}', 'url': None}
        except Exception as e:
            logger.error(f"Tistory 발행 실패: {e}")
            return {'success': False, 'message': f'Tistory 발행 실패: {str(e)}', 'url': None}
