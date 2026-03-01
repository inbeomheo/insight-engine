"""
MCP 플러그인 레지스트리

플러그인 등록/조회/실행을 관리하는 싱글턴 레지스트리.
"""
from .plugin_interface import MCPPlugin


class PluginRegistry:
    """플러그인 등록 및 실행을 관리하는 레지스트리"""

    def __init__(self):
        self._plugins: dict[str, MCPPlugin] = {}

    def register(self, plugin_id: str, plugin: MCPPlugin) -> None:
        """플러그인을 등록합니다."""
        self._plugins[plugin_id] = plugin

    def get(self, plugin_id: str) -> MCPPlugin | None:
        """ID로 플러그인을 조회합니다."""
        return self._plugins.get(plugin_id)

    def list_plugins(self) -> list[dict]:
        """등록된 전체 플러그인 목록을 반환합니다."""
        return [
            {
                "id": pid,
                "name": plugin.name,
                "description": plugin.description,
            }
            for pid, plugin in self._plugins.items()
        ]

    def execute(self, plugin_id: str, content: str, title: str, **kwargs) -> dict:
        """지정된 플러그인으로 콘텐츠를 발행합니다."""
        plugin = self._plugins.get(plugin_id)
        if plugin is None:
            return {
                "success": False,
                "message": f"플러그인 '{plugin_id}'을(를) 찾을 수 없습니다.",
                "url": None,
            }
        return plugin.execute(content, title, **kwargs)


# 싱글턴 인스턴스
plugin_registry = PluginRegistry()
