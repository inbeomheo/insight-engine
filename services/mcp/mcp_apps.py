"""
MCP Apps SDK — 인터랙티브 UI 앱 추상 인터페이스

콘텐츠 미리보기·인라인 편집처럼 발행 전 사용자가 상호작용하는
'앱' 단위를 정의합니다. 플러그인(발행)과는 별개 레이어입니다.
"""
from abc import ABC, abstractmethod
from typing import List


class BaseMCPApp(ABC):
    """MCP 인터랙티브 앱의 기본 인터페이스"""

    @abstractmethod
    def get_name(self) -> str:
        """앱 식별자 (영문 소문자, 언더스코어)"""
        ...

    @abstractmethod
    def get_description(self) -> str:
        """앱 설명 (한국어)"""
        ...

    @abstractmethod
    def render(self, content: dict) -> dict:
        """앱 화면을 렌더링합니다.

        Args:
            content: 콘텐츠 딕셔너리 {"title": str, "content": str, "html": str, ...}

        Returns:
            {"html": str, "actions": List[Dict[str, str]]}
            actions 항목 형식: {"action": str, "label": str, "style": str}
        """
        ...

    @abstractmethod
    def handle_action(self, action: str, data: dict) -> dict:
        """사용자 액션을 처리합니다.

        Args:
            action: 액션 식별자 문자열
            data:   액션에 필요한 추가 데이터

        Returns:
            {"success": bool, "message": str, "updated_content": dict | None}
        """
        ...


class MCPAppRegistry:
    """MCP 앱 등록 및 조회를 관리하는 레지스트리"""

    def __init__(self):
        self._apps: dict[str, BaseMCPApp] = {}

    def register(self, app: BaseMCPApp) -> None:
        """앱을 이름 기준으로 등록합니다."""
        self._apps[app.get_name()] = app

    def get(self, name: str) -> BaseMCPApp | None:
        """이름으로 앱을 조회합니다."""
        return self._apps.get(name)

    def list_apps(self) -> List[dict]:
        """등록된 전체 앱 목록을 반환합니다."""
        return [
            {"name": app.get_name(), "description": app.get_description()}
            for app in self._apps.values()
        ]


# 싱글턴 레지스트리
app_registry = MCPAppRegistry()
