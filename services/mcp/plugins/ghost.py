"""
Ghost CMS 발행 플러그인 (F7-13)

Ghost Admin API를 통해 포스트/페이지를 발행합니다.
GHOST_API_URL, GHOST_ADMIN_API_KEY 환경변수 또는 kwargs 사용.
"""
import json
import logging
import os
import time

import requests

from utils.url_safety import is_production, public_url_error
from ..plugin_interface import MCPPlugin

logger = logging.getLogger(__name__)


def _create_ghost_jwt(admin_api_key: str) -> str:
    """Ghost Admin API JWT 토큰 생성 (HS256)"""
    import base64
    import hashlib
    import hmac

    try:
        key_id, secret_hex = admin_api_key.split(':')
    except ValueError:
        raise ValueError("Ghost Admin API Key 형식이 잘못되었습니다. (형식: id:secret)")

    now = int(time.time())
    header = base64.urlsafe_b64encode(
        json.dumps({'alg': 'HS256', 'typ': 'JWT', 'kid': key_id}).encode()
    ).rstrip(b'=').decode()

    payload = base64.urlsafe_b64encode(
        json.dumps({'iat': now, 'exp': now + 300, 'aud': '/admin/'}).encode()
    ).rstrip(b'=').decode()

    signing_input = f'{header}.{payload}'
    secret_bytes = bytes.fromhex(secret_hex)
    signature = base64.urlsafe_b64encode(
        hmac.new(secret_bytes, signing_input.encode(), hashlib.sha256).digest()
    ).rstrip(b'=').decode()

    return f'{signing_input}.{signature}'


class GhostPlugin(MCPPlugin):
    """Ghost CMS에 콘텐츠를 발행하는 플러그인"""

    @property
    def name(self) -> str:
        return "Ghost CMS"

    @property
    def description(self) -> str:
        return "Ghost CMS에 포스트를 발행합니다"

    def schema(self) -> dict:
        return {
            'type': 'object',
            'properties': {
                'api_url': {
                    'type': 'string',
                    'description': 'Ghost 사이트 URL (예: https://myblog.ghost.io)',
                },
                'admin_api_key': {
                    'type': 'string',
                    'description': 'Ghost Admin API Key (id:secret 형식)',
                },
                'status': {
                    'type': 'string',
                    'enum': ['draft', 'published', 'scheduled'],
                    'description': '발행 상태 (기본: draft)',
                    'default': 'draft',
                },
                'tags': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': '태그 목록',
                },
            },
            'required': ['api_url', 'admin_api_key'],
        }

    def execute(self, content: str, title: str, **kwargs) -> dict:
        api_url = (kwargs.get('api_url') or os.getenv('GHOST_API_URL', '')).rstrip('/')
        admin_api_key = kwargs.get('admin_api_key') or os.getenv('GHOST_ADMIN_API_KEY', '')

        if not api_url:
            return {'success': False, 'message': 'Ghost API URL이 필요합니다.', 'url': None}
        if not admin_api_key:
            return {'success': False, 'message': 'Ghost Admin API Key가 필요합니다.', 'url': None}

        try:
            token = _create_ghost_jwt(admin_api_key)
        except ValueError as e:
            return {'success': False, 'message': str(e), 'url': None}

        status = kwargs.get('status', 'draft')
        tags = [{'name': t} for t in kwargs.get('tags', [])]

        # Mobiledoc 형식으로 변환
        mobiledoc = json.dumps({
            'version': '0.3.1',
            'markups': [],
            'atoms': [],
            'cards': [['markdown', {'markdown': content}]],
            'sections': [[10, 0]],
        })

        post_data = {
            'posts': [
                {
                    'title': title,
                    'mobiledoc': mobiledoc,
                    'status': status,
                    'tags': tags,
                }
            ]
        }

        posts_url = f'{api_url}/ghost/api/admin/posts/'
        url_error = public_url_error(posts_url, require_https=is_production(), label='Ghost API URL')
        if url_error:
            return {'success': False, 'message': url_error, 'url': None}

        try:
            resp = requests.post(
                posts_url,
                json=post_data,
                headers={
                'Authorization': f'Ghost {token}',
                'Content-Type': 'application/json',
                'Accept-Version': 'v5.0',
                },
                timeout=30,
                allow_redirects=False,
            )
            if 300 <= resp.status_code < 400:
                return {'success': False, 'message': f'Ghost 리다이렉트 차단: {resp.status_code}', 'url': None}
            resp.raise_for_status()
            data = resp.json()

            post = data.get('posts', [{}])[0]
            post_url = post.get('url')
            post_id = post.get('id', '')

            return {
                'success': True,
                'message': f"Ghost CMS {status} 포스트 생성 완료 (ID: {post_id})",
                'url': post_url,
            }

        except requests.HTTPError as e:
            response = e.response
            status = response.status_code if response is not None else 'unknown'
            error_body = response.text if response is not None else str(e)
            logger.error(f"Ghost HTTP 오류: {status} — {error_body}")
            try:
                err_data = json.loads(error_body)
                msg = err_data.get('errors', [{}])[0].get('message', error_body)
            except Exception:
                msg = error_body
            return {'success': False, 'message': f'Ghost API 오류: {msg}', 'url': None}
        except Exception as e:
            logger.error(f"Ghost 발행 실패: {e}")
            return {'success': False, 'message': f'Ghost 발행 실패: {str(e)}', 'url': None}
