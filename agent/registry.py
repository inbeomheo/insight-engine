"""
Tool Registry — 에이전트 도구 중앙 관리 싱글톤

Hermes Agent 패턴 참고:
- import 시 자동 등록 (registry.register())
- 스키마 수집, 디스패치, 가용성 체크, 에러 래핑
- Toolset 필터링 지원
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

from services.usage.usage_lock import UsageLockUnavailable

logger = logging.getLogger(__name__)

TOOL_BLOCKED_MESSAGE = "도구 사용 정책에 의해 차단되었습니다."
TOOL_EXECUTION_ERROR_MESSAGE = "도구 실행 중 문제가 발생했습니다."


def _sanitize_handler_result(result: Any) -> Any:
    """핸들러가 정상 반환으로 감싼 오류에서도 내부 정보를 제거한다.

    일부 자동 래퍼는 예외를 다시 던지지 않고 ``{"error": str(exc)}``로
    바꾼다. dispatch의 예외 경계만 보호하면 이 문자열이 그대로 LLM과 SSE
    콜백에 전달되므로, 직렬화 전 모든 오류 payload를 동일한 안전 응답으로
    정규화한다.
    """
    if isinstance(result, dict):
        if result.get("error"):
            if result.get("code") == "TOOL_BLOCKED":
                return {
                    "error": TOOL_BLOCKED_MESSAGE,
                    "code": "TOOL_BLOCKED",
                }
            return {
                "error": TOOL_EXECUTION_ERROR_MESSAGE,
                "code": "TOOL_EXECUTION_FAILED",
            }
        return {key: _sanitize_handler_result(value) for key, value in result.items()}
    if isinstance(result, list):
        return [_sanitize_handler_result(value) for value in result]
    if isinstance(result, str):
        try:
            parsed = json.loads(result)
        except (TypeError, ValueError, json.JSONDecodeError):
            return result
        sanitized = _sanitize_handler_result(parsed)
        if sanitized != parsed:
            logger.warning("도구 핸들러 오류 payload의 상세 정보를 숨겼습니다.")
        return json.dumps(sanitized, ensure_ascii=False, default=str)
    return result


@dataclass
class ToolEntry:
    """등록된 도구 하나의 메타데이터."""
    name: str
    toolset: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable[..., Any]
    check_fn: Optional[Callable[[], bool]] = None
    requires_env: List[str] = field(default_factory=list)
    is_async: bool = False
    tags: List[str] = field(default_factory=list)

    @property
    def schema(self) -> Dict[str, Any]:
        """OpenAI function-calling 호환 스키마."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    @property
    def available(self) -> bool:
        """런타임 가용성 체크."""
        if self.check_fn is None:
            return True
        try:
            return self.check_fn()
        except Exception:
            return False


class ToolRegistry:
    """도구 레지스트리 싱글톤.

    사용법:
        from agent.registry import registry

        # 도구 등록 (import 시 자동 실행)
        registry.register(
            name="analyze_readability",
            toolset="analysis",
            description="텍스트 가독성 분석",
            parameters={"type": "object", "properties": {"content": {"type": "string"}}, "required": ["content"]},
            handler=lambda args, **kw: analyze_readability(args["content"]),
        )

        # 도구 목록 조회
        schemas = registry.get_schemas(toolsets=["analysis", "seo"])

        # 도구 실행
        result = registry.dispatch("analyze_readability", {"content": "..."})
    """

    _instance: Optional[ToolRegistry] = None

    def __new__(cls) -> ToolRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: Dict[str, ToolEntry] = {}
            cls._instance._toolset_map: Dict[str, List[str]] = {}
            cls._instance._initialized = False
        return cls._instance

    def register(
        self,
        name: str,
        toolset: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable[..., Any],
        check_fn: Optional[Callable[[], bool]] = None,
        requires_env: Optional[List[str]] = None,
        is_async: bool = False,
        tags: Optional[List[str]] = None,
    ) -> None:
        """도구를 레지스트리에 등록합니다.

        Args:
            name: 도구 고유 이름 (예: "analyze_readability")
            toolset: 소속 도구셋 (예: "analysis")
            description: 도구 설명 (LLM이 읽는 텍스트)
            parameters: JSON Schema 형식 파라미터 정의
            handler: 실행 함수 (args: dict, **kwargs) -> Any
            check_fn: 런타임 가용성 체크 함수
            requires_env: 필요한 환경변수 목록
            is_async: 비동기 핸들러 여부
            tags: 검색/필터용 태그
        """
        if name in self._tools:
            logger.debug("도구 재등록: %s (덮어쓰기)", name)

        entry = ToolEntry(
            name=name,
            toolset=toolset,
            description=description,
            parameters=parameters,
            handler=handler,
            check_fn=check_fn,
            requires_env=requires_env or [],
            is_async=is_async,
            tags=tags or [],
        )
        self._tools[name] = entry

        # toolset → tool names 매핑 갱신
        if toolset not in self._toolset_map:
            self._toolset_map[toolset] = []
        if name not in self._toolset_map[toolset]:
            self._toolset_map[toolset].append(name)

    def unregister(self, name: str) -> bool:
        """도구를 레지스트리에서 제거합니다."""
        entry = self._tools.pop(name, None)
        if entry:
            names = self._toolset_map.get(entry.toolset, [])
            if name in names:
                names.remove(name)
            return True
        return False

    def get(self, name: str) -> Optional[ToolEntry]:
        """이름으로 도구 조회."""
        return self._tools.get(name)

    def list_tools(
        self,
        toolsets: Optional[Sequence[str]] = None,
        available_only: bool = True,
        tags: Optional[Sequence[str]] = None,
        excluded_tools: Optional[Sequence[str]] = None,
    ) -> List[ToolEntry]:
        """조건에 맞는 도구 목록 반환.

        Args:
            toolsets: 포함할 toolset 이름 목록 (None이면 전체)
            available_only: True면 가용한 도구만 반환
            tags: 하나라도 매칭되는 태그가 있는 도구만 반환
            excluded_tools: 정책상 제외할 도구 이름 목록
        """
        entries = self._tools.values()

        if toolsets is not None:
            toolset_set = set(toolsets)
            entries = [e for e in entries if e.toolset in toolset_set]
        else:
            entries = list(entries)

        if available_only:
            entries = [e for e in entries if e.available]

        if tags:
            tag_set = set(tags)
            entries = [e for e in entries if tag_set & set(e.tags)]

        if excluded_tools:
            excluded_set = set(excluded_tools)
            entries = [e for e in entries if e.name not in excluded_set]

        return entries

    def get_schemas(
        self,
        toolsets: Optional[Sequence[str]] = None,
        available_only: bool = True,
        excluded_tools: Optional[Sequence[str]] = None,
    ) -> List[Dict[str, Any]]:
        """LLM API에 전달할 도구 스키마 목록 반환."""
        return [
            entry.schema
            for entry in self.list_tools(
                toolsets=toolsets,
                available_only=available_only,
                excluded_tools=excluded_tools,
            )
        ]

    def get_tool_names(self, toolsets: Optional[Sequence[str]] = None) -> List[str]:
        """가용한 도구 이름 목록 반환."""
        return [e.name for e in self.list_tools(toolsets=toolsets)]

    def dispatch(
        self,
        name: str,
        args: Dict[str, Any],
        **kwargs: Any,
    ) -> str:
        """도구를 실행하고 결과를 JSON 문자열로 반환합니다.

        Args:
            name: 도구 이름
            args: 도구 인자 딕셔너리
            **kwargs: 추가 컨텍스트 (task_id, user_id 등)

        Returns:
            JSON 문자열 결과

        Raises:
            KeyError: 등록되지 않은 도구
            RuntimeError: 도구 실행 실패
        """
        # 스키마에서 숨기는 것만으로는 충분하지 않다. 모델이 도구 이름을 직접
        # 만들어 호출하거나 합성 toolset을 악용해도 dispatch 경계에서 거부한다.
        blocked_tools = kwargs.get("blocked_tools")
        allowed_tools = kwargs.get("allowed_tools")
        if (
            (blocked_tools is not None and name in set(blocked_tools))
            or (allowed_tools is not None and name not in set(allowed_tools))
        ):
            logger.warning("정책상 차단된 도구 호출: %s", name)
            return json.dumps({
                "error": TOOL_BLOCKED_MESSAGE,
                "code": "TOOL_BLOCKED",
            }, ensure_ascii=False)

        entry = self._tools.get(name)
        if not entry:
            raise KeyError(f"등록되지 않은 도구: {name}")

        if not entry.available:
            return json.dumps({
                "error": f"도구 '{name}'을 사용할 수 없습니다. "
                         f"필요한 환경변수: {entry.requires_env}",
            })

        start = time.time()
        try:
            if entry.is_async:
                result = self._run_async(entry.handler, args, **kwargs)
            else:
                result = entry.handler(args, **kwargs)

            result = _sanitize_handler_result(result)

            elapsed = time.time() - start
            logger.debug("도구 실행 완료: %s (%.2f초)", name, elapsed)

            # 결과 정규화: 문자열이면 그대로, dict/list면 JSON 직렬화
            if isinstance(result, str):
                return result
            return json.dumps(result, ensure_ascii=False, default=str)

        except UsageLockUnavailable:
            raise
        except Exception as exc:
            elapsed = time.time() - start
            # 예외 원문과 traceback은 비밀을 담을 수 있어 로깅하지 않는다.
            # 공급자 키, 내부 URL, Authorization 헤더가 섞일 수 있어 포함하지 않는다.
            logger.error(
                "도구 실행 실패: %s (%.2f초, type=%s)",
                name,
                elapsed,
                type(exc).__name__,
            )
            return json.dumps({
                "error": TOOL_EXECUTION_ERROR_MESSAGE,
                "code": "TOOL_EXECUTION_FAILED",
            }, ensure_ascii=False)

    def _run_async(self, handler: Callable, args: Dict, **kwargs) -> Any:
        """비동기 핸들러를 동기적으로 실행합니다."""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # 이미 이벤트 루프가 실행 중이면 새 스레드에서 실행
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, handler(args, **kwargs))
                return future.result(timeout=180)
        else:
            return asyncio.run(handler(args, **kwargs))

    @property
    def tool_count(self) -> int:
        return len(self._tools)

    @property
    def toolset_names(self) -> List[str]:
        return list(self._toolset_map.keys())

    def stats(self) -> Dict[str, Any]:
        """레지스트리 통계."""
        available = sum(1 for e in self._tools.values() if e.available)
        return {
            "total_tools": len(self._tools),
            "available_tools": available,
            "toolsets": {
                name: len(tools)
                for name, tools in self._toolset_map.items()
            },
        }

    def reset(self) -> None:
        """테스트용: 레지스트리 초기화."""
        self._tools.clear()
        self._toolset_map.clear()
        self._initialized = False


# 싱글톤 인스턴스
registry = ToolRegistry()
