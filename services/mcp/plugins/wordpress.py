"""
WordPress 발행 플러그인 (placeholder)

실제 WordPress REST API 연동은 추후 구현 예정.
"""
from ..plugin_interface import MCPPlugin


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
            },
        }

    def execute(self, content: str, title: str, **kwargs) -> dict:
        # TODO: 실제 WordPress REST API 연동
        return {
            "success": True,
            "message": f"'{title}' 발행 준비 완료 (WordPress API 연동 필요)",
            "url": None,
        }
