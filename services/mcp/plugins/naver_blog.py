"""
네이버 블로그 발행 플러그인.

공식 글쓰기 API가 제한적이므로 n8n/Make/사내 자동화 웹훅으로 발행 요청을 전달합니다.
"""
import logging
import os

import requests

from ..plugin_interface import MCPPlugin

logger = logging.getLogger(__name__)


class NaverBlogPlugin(MCPPlugin):
    """네이버 블로그에 콘텐츠를 발행하는 플러그인"""

    @property
    def name(self) -> str:
        return "네이버 블로그"

    @property
    def description(self) -> str:
        return "네이버 블로그에 콘텐츠를 발행합니다"

    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "blog_id": {
                    "type": "string",
                    "description": "네이버 블로그 ID",
                },
                "webhook_url": {
                    "type": "string",
                    "description": "네이버 발행 자동화 웹훅 URL",
                },
                "category": {
                    "type": "string",
                    "description": "카테고리명",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "태그 목록",
                },
            },
            "required": ["webhook_url"],
        }

    def execute(self, content: str, title: str, **kwargs) -> dict:
        webhook_url = kwargs.get('webhook_url') or os.getenv('NAVER_BLOG_WEBHOOK_URL', '')
        if not webhook_url:
            return {
                "success": False,
                "message": "네이버 블로그 발행 웹훅 URL이 필요합니다.",
                "url": None,
            }

        payload = {
            "title": title,
            "content": content,
            "blog_id": kwargs.get('blog_id') or os.getenv('NAVER_BLOG_ID', ''),
            "category": kwargs.get('category', ''),
            "tags": kwargs.get('tags', []),
        }

        try:
            logger.info('네이버 블로그 발행 요청: %s', title)
            resp = requests.post(webhook_url, json=payload, timeout=30)
            if resp.status_code in (200, 201, 202):
                data = resp.json() if resp.content else {}
                post_url = data.get('url') or data.get('post_url')
                return {
                    "success": True,
                    "message": "네이버 블로그 발행 요청 완료",
                    "url": post_url,
                }
            return {
                "success": False,
                "message": f"네이버 블로그 웹훅 오류: HTTP {resp.status_code}",
                "url": None,
            }
        except requests.RequestException as e:
            logger.error('네이버 블로그 웹훅 연결 실패: %s', e)
            return {
                "success": False,
                "message": f"네이버 블로그 웹훅 연결 실패: {e}",
                "url": None,
            }
        except Exception as e:
            logger.error('네이버 블로그 발행 실패: %s', e)
            return {
                "success": False,
                "message": f"발행 중 오류: {e}",
                "url": None,
            }
