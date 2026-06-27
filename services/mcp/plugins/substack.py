"""
Substack 발행 플러그인

Substack API로 Draft 포스트를 생성합니다.
Substack은 공식 API가 제한적이므로 이메일 기반 발행도 지원합니다.
"""
import logging

import requests

from ..plugin_interface import MCPPlugin

logger = logging.getLogger(__name__)


class SubstackPlugin(MCPPlugin):
    """Substack에 콘텐츠를 발행하는 플러그인"""

    @property
    def name(self) -> str:
        return "Substack"

    @property
    def description(self) -> str:
        return "Substack에 Draft 포스트를 생성합니다"

    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "subdomain": {
                    "type": "string",
                    "description": "Substack 서브도메인 (예: mysite → mysite.substack.com)",
                },
                "api_key": {
                    "type": "string",
                    "description": "Substack API 키 (또는 세션 쿠키)",
                },
                "publish_status": {
                    "type": "string",
                    "enum": ["draft", "published"],
                    "description": "발행 상태 (기본: draft)",
                },
            },
            "required": ["subdomain", "api_key"],
        }

    def execute(self, content: str, title: str, **kwargs) -> dict:
        subdomain = kwargs.get('subdomain', '')
        api_key = kwargs.get('api_key', '')

        if not subdomain or not api_key:
            return {
                'success': False,
                'message': 'Substack 서브도메인과 API 키가 필요합니다.',
                'url': None,
            }

        base_url = f'https://{subdomain}.substack.com'
        publish_status = kwargs.get('publish_status', 'draft')

        headers = {
            'Cookie': f'substack.sid={api_key}',
            'Content-Type': 'application/json',
        }

        # 마크다운 → HTML 변환
        import markdown as md_lib
        html_body = md_lib.markdown(content, extensions=['tables', 'fenced_code'])

        payload = {
            'title': title,
            'body_html': html_body,
            'draft': publish_status == 'draft',
        }

        try:
            resp = requests.post(
                f'{base_url}/api/v1/drafts',
                json=payload,
                headers=headers,
                timeout=30,
                allow_redirects=False,
            )
            if 300 <= resp.status_code < 400:
                return {
                    'success': False,
                    'message': f'Substack 리다이렉트 차단: {resp.status_code}',
                    'url': None,
                }
            if resp.status_code in (200, 201):
                data = resp.json()
                post_id = data.get('id', '')
                post_url = f'{base_url}/p/{post_id}' if post_id else None
                return {
                    'success': True,
                    'message': f'Substack {publish_status} 포스트 생성 완료',
                    'url': post_url,
                }
            else:
                return {
                    'success': False,
                    'message': f'Substack API 오류: {resp.status_code}',
                    'url': None,
                }
        except requests.RequestException as e:
            logger.error(f"Substack 연결 실패: {e}")
            return {
                'success': False,
                'message': f'Substack 연결 실패: {str(e)}',
                'url': None,
            }
