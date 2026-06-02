"""
WordPress 발행 플러그인.

WordPress REST API로 글을 생성합니다.
"""
import base64
import logging
import os

import requests

from ..plugin_interface import MCPPlugin

logger = logging.getLogger(__name__)


class WordPressPlugin(MCPPlugin):
    """WordPress에 콘텐츠를 발행하는 플러그인"""

    @property
    def name(self) -> str:
        return "WordPress"

    @property
    def description(self) -> str:
        return "WordPress 사이트에 콘텐츠를 발행합니다"

    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "site_url": {
                    "type": "string",
                    "description": "WordPress 사이트 URL",
                },
                "username": {
                    "type": "string",
                    "description": "WordPress 사용자명",
                },
                "app_password": {
                    "type": "string",
                    "description": "WordPress Application Password",
                },
                "status": {
                    "type": "string",
                    "enum": ["draft", "publish", "private", "pending"],
                    "description": "발행 상태 (기본: draft)",
                },
            },
            "required": ["site_url", "username", "app_password"],
        }

    def execute(self, content: str, title: str, **kwargs) -> dict:
        site_url = (kwargs.get('site_url') or os.getenv('WORDPRESS_SITE_URL', '')).rstrip('/')
        username = kwargs.get('username') or os.getenv('WORDPRESS_USERNAME', '')
        app_password = kwargs.get('app_password') or os.getenv('WORDPRESS_APP_PASSWORD', '')

        if not site_url or not username or not app_password:
            return {
                "success": False,
                "message": "WordPress site_url, username, app_password가 필요합니다.",
                "url": None,
            }

        token = base64.b64encode(f"{username}:{app_password}".encode()).decode()
        payload = {
            "title": title,
            "content": content,
            "status": kwargs.get('status', 'draft'),
        }
        if kwargs.get('excerpt'):
            payload["excerpt"] = kwargs["excerpt"]
        if kwargs.get('categories'):
            payload["categories"] = kwargs["categories"]
        if kwargs.get('tags'):
            payload["tags"] = kwargs["tags"]

        try:
            logger.info('WordPress 발행 요청: %s', title)
            resp = requests.post(
                f"{site_url}/wp-json/wp/v2/posts",
                json=payload,
                headers={
                    "Authorization": f"Basic {token}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                return {
                    "success": True,
                    "message": f"WordPress {payload['status']} 글 생성 완료",
                    "url": data.get("link"),
                }
            try:
                error_msg = resp.json().get("message", resp.text)
            except Exception:
                error_msg = resp.text
            return {
                "success": False,
                "message": f"WordPress API 오류: {error_msg}",
                "url": None,
            }
        except requests.RequestException as e:
            logger.error('WordPress 연결 실패: %s', e)
            return {
                "success": False,
                "message": f"WordPress 연결 실패: {e}",
                "url": None,
            }
        except Exception as e:
            logger.error('WordPress 발행 실패: %s', e)
            return {
                "success": False,
                "message": f"발행 중 오류: {e}",
                "url": None,
            }
