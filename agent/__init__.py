"""
Insight Engine Agent 패키지

Hermes Agent 패턴 기반 에이전트 오케스트레이션 시스템.
기존 324개 서비스를 Tool로 래핑하고, AIAgent가 LLM을 통해 오케스트레이션합니다.

구조:
    agent/
    ├── __init__.py       # 패키지 초기화 + 공개 API
    ├── core.py           # AIAgent 코어 클래스 (while 루프 + LiteLLM)
    ├── registry.py       # ToolRegistry 싱글톤 (자동등록)
    ├── toolsets.py        # Toolset 정의 (20개 도메인 + 역할별 합성)
    ├── memory.py          # SQLite 상태 + 동결 스냅샷 메모리
    ├── compressor.py      # 5단계 컨텍스트 압축
    ├── delegate.py        # 서브에이전트 위임 (부모→자식)
    └── tools/             # 서비스 → Tool 래핑 (Phase 2에서 구현)

사용법:
    from agent import AIAgent, registry

    # 에이전트 실행
    agent = AIAgent(
        model="cliproxyapi/gpt-5.5",
        toolsets=["role_writer"],
        system_prompt="콘텐츠 작성 전문가",
    )
    response = agent.run("이 YouTube 영상으로 블로그 글을 써줘")

    # 도구 등록 (서비스 래핑)
    registry.register(
        name="analyze_readability",
        toolset="analysis",
        description="텍스트 가독성 분석",
        parameters={...},
        handler=my_handler,
    )
"""

from agent.core import AIAgent, AgentResponse
from agent.registry import ToolRegistry, registry
from agent.toolsets import (
    TOOLSETS,
    resolve_toolset,
    resolve_toolsets,
    list_toolset_names,
)
from agent.memory import AgentMemoryStore, memory_store
from agent.delegate import DelegateManager, DelegateTask, DelegateResult
from agent.compressor import compress_messages

__all__ = [
    # 코어
    "AIAgent",
    "AgentResponse",
    # 레지스트리
    "ToolRegistry",
    "registry",
    # 도구셋
    "TOOLSETS",
    "resolve_toolset",
    "resolve_toolsets",
    "list_toolset_names",
    # 메모리
    "AgentMemoryStore",
    "memory_store",
    # 위임
    "DelegateManager",
    "DelegateTask",
    "DelegateResult",
    # 압축
    "compress_messages",
]

__version__ = "0.1.0"
