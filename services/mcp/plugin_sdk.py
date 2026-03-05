"""
플러그인 SDK (F7-10)

서드파티 개발자가 Insight Engine MCP 플러그인을 쉽게 개발할 수 있도록
편의 기능과 데코레이터를 제공합니다.

사용 예:
    from services.mcp.plugin_sdk import plugin, PluginBase

    @plugin(plugin_id='my_platform', name='My Platform', description='My Platform에 발행')
    class MyPlatformPlugin(PluginBase):
        SCHEMA = {
            'type': 'object',
            'properties': {
                'api_key': {'type': 'string', 'description': 'API 키'},
            },
            'required': ['api_key'],
        }

        def publish(self, title: str, content: str, **kwargs) -> dict:
            # 발행 로직 구현
            return {'success': True, 'message': '발행 완료', 'url': None}
"""
import logging
from functools import wraps
from typing import Optional, Type

from .plugin_interface import MCPPlugin
from .registry import plugin_registry

logger = logging.getLogger(__name__)


class PluginBase(MCPPlugin):
    """플러그인 SDK 기본 클래스

    서브클래스에서 구현해야 하는 것:
    - SCHEMA: dict — 설정 JSON Schema
    - publish(title, content, **kwargs) -> dict — 실제 발행 로직

    선택적으로 오버라이드:
    - validate_config(**kwargs) -> Optional[str] — 설정 검증 (오류 문자열 반환)
    """

    # 서브클래스에서 정의
    SCHEMA: dict = {'type': 'object', 'properties': {}}
    _name: str = ''
    _description: str = ''

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def schema(self) -> dict:
        return self.SCHEMA

    def execute(self, content: str, title: str, **kwargs) -> dict:
        """플러그인 실행 — 검증 후 publish() 호출"""
        # 설정 검증
        error = self.validate_config(**kwargs)
        if error:
            return {'success': False, 'message': error, 'url': None}

        try:
            result = self.publish(title=title, content=content, **kwargs)
            # 반환 형식 보장
            if not isinstance(result, dict):
                return {'success': False, 'message': '잘못된 반환 형식', 'url': None}
            result.setdefault('success', True)
            result.setdefault('message', '발행 완료')
            result.setdefault('url', None)
            return result
        except Exception as e:
            logger.error(f"플러그인 [{self._name}] 실행 오류: {e}")
            return {'success': False, 'message': f'발행 중 오류: {str(e)}', 'url': None}

    def validate_config(self, **kwargs) -> Optional[str]:
        """설정 검증. 오류가 있으면 오류 메시지 반환, 없으면 None.

        기본 구현: SCHEMA의 required 필드 존재 여부만 확인.
        """
        required = self.SCHEMA.get('required', [])
        for field in required:
            if not kwargs.get(field):
                return f"'{field}' 설정이 필요합니다."
        return None

    def publish(self, title: str, content: str, **kwargs) -> dict:
        """실제 발행 로직. 서브클래스에서 구현 필요.

        Returns:
            {"success": bool, "message": str, "url": str | None}
        """
        raise NotImplementedError("publish() 메서드를 구현해주세요.")


def plugin(
    plugin_id: str,
    name: str,
    description: str,
    auto_register: bool = True,
) -> 'Callable':
    """플러그인 클래스 데코레이터

    Args:
        plugin_id: 고유 플러그인 ID (영문 소문자, 밑줄)
        name: 표시 이름
        description: 플러그인 설명
        auto_register: True면 plugin_registry에 자동 등록

    Usage:
        @plugin(plugin_id='tistory', name='Tistory', description='...')
        class TistoryPlugin(PluginBase):
            ...
    """
    def decorator(cls: Type[PluginBase]) -> Type[PluginBase]:
        cls._name = name
        cls._description = description

        if auto_register:
            instance = cls()
            plugin_registry.register(plugin_id, instance)
            logger.info(f"플러그인 자동 등록: {plugin_id} ({name})")

        return cls
    return decorator


def require_env(*env_vars: str):
    """환경변수 필수 설정 데코레이터 (publish 메서드용)

    Usage:
        @require_env('TISTORY_API_KEY', 'TISTORY_BLOG_NAME')
        def publish(self, title, content, **kwargs):
            ...
    """
    import os

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            missing = [v for v in env_vars if not os.getenv(v)]
            if missing:
                return {
                    'success': False,
                    'message': f"환경변수 미설정: {', '.join(missing)}",
                    'url': None,
                }
            return func(*args, **kwargs)
        return wrapper
    return decorator


class HttpPluginMixin:
    """HTTP 요청 편의 메서드를 제공하는 믹스인"""

    def _post_json(self, url: str, data: dict, headers: Optional[dict] = None,
                   timeout: int = 30) -> tuple[int, dict]:
        """JSON POST 요청

        Returns:
            (status_code, response_dict)
        """
        import json
        import urllib.request
        import urllib.error

        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode(),
            headers={'Content-Type': 'application/json', **(headers or {})},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            try:
                return e.code, json.loads(body)
            except Exception:
                return e.code, {'error': body}

    def _get_json(self, url: str, headers: Optional[dict] = None,
                  timeout: int = 15) -> tuple[int, dict]:
        """JSON GET 요청"""
        import json
        import urllib.request
        import urllib.error

        req = urllib.request.Request(url, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return e.code, {}


# 타입 힌트용
from typing import Callable  # noqa: E402
