"""
LinkedIn 발행 플러그인 (F7-15)

LinkedIn API v2를 통해 텍스트 포스트를 게시합니다.
LinkedIn OAuth2 액세스 토큰이 필요합니다.
"""
import json
import logging
import os
import urllib.error
import urllib.request

from ..plugin_interface import MCPPlugin

logger = logging.getLogger(__name__)

LINKEDIN_API_BASE = 'https://api.linkedin.com/v2'


class LinkedInPlugin(MCPPlugin):
    """LinkedIn에 콘텐츠를 발행하는 플러그인"""

    @property
    def name(self) -> str:
        return "LinkedIn"

    @property
    def description(self) -> str:
        return "LinkedIn 프로필/페이지에 포스트를 게시합니다"

    def schema(self) -> dict:
        return {
            'type': 'object',
            'properties': {
                'access_token': {
                    'type': 'string',
                    'description': 'LinkedIn OAuth2 액세스 토큰',
                },
                'author_urn': {
                    'type': 'string',
                    'description': '작성자 URN (예: urn:li:person:ABC123)',
                },
                'visibility': {
                    'type': 'string',
                    'enum': ['PUBLIC', 'CONNECTIONS', 'LOGGED_IN'],
                    'description': '공개 범위 (기본: PUBLIC)',
                    'default': 'PUBLIC',
                },
            },
            'required': ['access_token'],
        }

    def execute(self, content: str, title: str, **kwargs) -> dict:
        access_token = kwargs.get('access_token') or os.getenv('LINKEDIN_ACCESS_TOKEN', '')
        author_urn = kwargs.get('author_urn') or os.getenv('LINKEDIN_AUTHOR_URN', '')

        if not access_token:
            return {'success': False, 'message': 'LinkedIn 액세스 토큰이 필요합니다.', 'url': None}

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0',
        }

        # author_urn이 없으면 /me에서 조회
        if not author_urn:
            try:
                req = urllib.request.Request(f'{LINKEDIN_API_BASE}/me', headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    me = json.loads(resp.read())
                    author_urn = f"urn:li:person:{me.get('id', '')}"
            except Exception as e:
                logger.error(f"LinkedIn 사용자 조회 실패: {e}")
                return {'success': False, 'message': 'LinkedIn 사용자 정보를 가져올 수 없습니다.', 'url': None}

        visibility = kwargs.get('visibility', 'PUBLIC')
        # 콘텐츠 앞에 제목 추가, 최대 3000자 제한
        post_text = f"{title}\n\n{content}"[:3000]

        post_data = {
            'author': author_urn,
            'lifecycleState': 'PUBLISHED',
            'specificContent': {
                'com.linkedin.ugc.ShareContent': {
                    'shareCommentary': {'text': post_text},
                    'shareMediaCategory': 'NONE',
                }
            },
            'visibility': {'com.linkedin.ugc.MemberNetworkVisibility': visibility},
        }

        req = urllib.request.Request(
            f'{LINKEDIN_API_BASE}/ugcPosts',
            data=json.dumps(post_data).encode(),
            headers=headers,
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                post_id = resp.headers.get('x-restli-id', '')
                post_url = f'https://www.linkedin.com/feed/update/{post_id}' if post_id else None
                return {
                    'success': True,
                    'message': f"LinkedIn 포스트 게시 완료 (ID: {post_id})",
                    'url': post_url,
                }

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='replace')
            logger.error(f"LinkedIn HTTP 오류: {e.code} — {error_body}")
            return {'success': False, 'message': f'LinkedIn API 오류: {e.code}', 'url': None}
        except Exception as e:
            logger.error(f"LinkedIn 발행 실패: {e}")
            return {'success': False, 'message': f'LinkedIn 발행 실패: {str(e)}', 'url': None}
