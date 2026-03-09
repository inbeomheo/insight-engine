"""
에이전트 핸드오프 서비스 — 에이전트 간 컨텍스트 전달 및 이력 관리
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AgentContext:
    """에이전트 컨텍스트 정보"""
    agent_name: str
    capabilities: list[str] = field(default_factory=list)
    state: dict = field(default_factory=dict)


@dataclass
class HandoffResult:
    """핸드오프 결과"""
    handoff_id: str
    session_id: str
    current_agent: str
    next_agent: str
    context: dict
    timestamp: float = field(default_factory=time.time)
    status: str = "completed"  # "completed" | "failed" | "pending"


# 핸드오프 시 context에 반드시 포함되어야 하는 키
_REQUIRED_CONTEXT_KEYS = {"task", "progress"}


class AgentHandoffService:
    """인메모리 에이전트 핸드오프 관리"""

    def __init__(self):
        # session_id -> list[HandoffResult] (시간순)
        self._handoff_store: dict[str, list[HandoffResult]] = {}
        # 등록된 에이전트 이름 -> AgentContext
        self._agents: dict[str, AgentContext] = {}

    def register_agent(self, context: AgentContext) -> None:
        """에이전트 등록"""
        if not context.agent_name or not context.agent_name.strip():
            raise ValueError("에이전트 이름은 비어 있을 수 없습니다")
        self._agents[context.agent_name] = context

    def unregister_agent(self, agent_name: str) -> bool:
        """에이전트 등록 해제. 성공 시 True 반환."""
        if agent_name in self._agents:
            del self._agents[agent_name]
            return True
        return False

    def get_agent(self, agent_name: str) -> Optional[AgentContext]:
        """등록된 에이전트 조회"""
        return self._agents.get(agent_name)

    def list_agents(self) -> list[AgentContext]:
        """등록된 에이전트 목록"""
        return list(self._agents.values())

    def handoff(
        self,
        current_agent: str,
        next_agent: str,
        context: dict,
        session_id: Optional[str] = None,
    ) -> HandoffResult:
        """
        에이전트 간 컨텍스트 전달.

        Args:
            current_agent: 현재 에이전트 이름
            next_agent: 다음 에이전트 이름
            context: 전달할 컨텍스트 (task, progress 키 필수)
            session_id: 세션 ID (미지정 시 자동 생성)

        Returns:
            HandoffResult

        Raises:
            ValueError: 에이전트명이 비어있거나, 동일하거나, 필수 키 누락 시
        """
        # 에이전트명 검증
        if not current_agent or not current_agent.strip():
            raise ValueError("current_agent는 비어 있을 수 없습니다")
        if not next_agent or not next_agent.strip():
            raise ValueError("next_agent는 비어 있을 수 없습니다")
        if current_agent == next_agent:
            raise ValueError("current_agent와 next_agent는 서로 달라야 합니다")

        # 컨텍스트 검증
        if not isinstance(context, dict):
            raise ValueError("context는 dict 타입이어야 합니다")
        missing = _REQUIRED_CONTEXT_KEYS - set(context.keys())
        if missing:
            raise ValueError(f"context에 필수 키가 누락되었습니다: {missing}")

        sid = session_id or f"session_{uuid.uuid4().hex[:12]}"

        result = HandoffResult(
            handoff_id=f"handoff_{uuid.uuid4().hex[:12]}",
            session_id=sid,
            current_agent=current_agent,
            next_agent=next_agent,
            context=dict(context),  # 방어적 복사
            status="completed",
        )

        if sid not in self._handoff_store:
            self._handoff_store[sid] = []
        self._handoff_store[sid].append(result)

        return result

    def get_handoff_history(self, session_id: str) -> list[HandoffResult]:
        """핸드오프 이력 조회 (시간순)"""
        return list(self._handoff_store.get(session_id, []))

    def get_handoff_by_id(self, handoff_id: str) -> Optional[HandoffResult]:
        """특정 핸드오프 결과 조회"""
        for results in self._handoff_store.values():
            for r in results:
                if r.handoff_id == handoff_id:
                    return r
        return None

    def get_session_ids(self) -> list[str]:
        """모든 세션 ID 목록"""
        return list(self._handoff_store.keys())

    def clear_session(self, session_id: str) -> int:
        """세션의 핸드오프 이력 삭제. 삭제된 항목 수 반환."""
        removed = self._handoff_store.pop(session_id, [])
        return len(removed)
