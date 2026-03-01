"""
MCP 플러그인 추상 인터페이스

모든 외부 발행 플러그인은 이 클래스를 상속하여 구현합니다.
"""
from abc import ABC, abstractmethod


class MCPPlugin(ABC):
    """외부 서비스에 콘텐츠를 발행하는 플러그인의 기본 인터페이스"""

    @property
    @abstractmethod
    def name(self) -> str:
        """플러그인 표시 이름"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """플러그인 설명"""
        ...

    @abstractmethod
    def schema(self) -> dict:
        """플러그인 설정 JSON Schema 반환"""
        ...

    @abstractmethod
    def execute(self, content: str, title: str, **kwargs) -> dict:
        """콘텐츠 발행

        Returns:
            {"success": bool, "message": str, "url": str | None}
        """
        ...
