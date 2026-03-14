"""
에이전트 베이스 클래스 — plan -> execute -> reflect 루프
각 에이전트는 BaseAgent를 상속하여 단계별 로직을 구현합니다.
"""
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# 에이전트 상태 이벤트 타입
EVENT_PLAN = "plan"
EVENT_EXECUTE = "execute"
EVENT_REFLECT = "reflect"
EVENT_DONE = "done"
EVENT_ERROR = "error"

# 최대 반복 횟수 (무한 루프 방지)
MAX_ITERATIONS = 5


class AgentEvent:
    """에이전트 진행 상태 이벤트 (SSE 전송용)"""

    def __init__(self, phase: str, message: str, data: Optional[Dict] = None,
                 iteration: int = 0, progress: float = 0.0):
        self.phase = phase
        self.message = message
        self.data = data or {}
        self.iteration = iteration
        self.progress = progress  # 0.0 ~ 1.0
        self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "message": self.message,
            "data": self.data,
            "iteration": self.iteration,
            "progress": self.progress,
            "timestamp": self.timestamp,
        }


class BaseAgent(ABC):
    """에이전트 베이스 클래스 — plan/execute/reflect 루프를 실행합니다.

    서브클래스는 plan(), execute(), reflect()를 구현해야 합니다.
    """

    def __init__(self, name: str, model: str, max_iterations: int = MAX_ITERATIONS):
        self.name = name
        self.model = model
        self.max_iterations = max_iterations
        self._event_listeners: List[Callable[[AgentEvent], None]] = []

    def on_event(self, listener: Callable[[AgentEvent], None]) -> None:
        """이벤트 리스너를 등록합니다."""
        self._event_listeners.append(listener)

    def _emit(self, event: AgentEvent) -> None:
        """이벤트를 모든 리스너에 전달합니다."""
        for listener in self._event_listeners:
            try:
                listener(event)
            except Exception as e:
                logger.warning(f"[{self.name}] 이벤트 리스너 오류: {e}")

    @abstractmethod
    def plan(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """작업 계획을 수립합니다.

        Args:
            task: 수행할 작업 설명
            context: 이전 반복의 결과 등 컨텍스트

        Returns:
            계획 데이터 (execute에 전달)
        """

    @abstractmethod
    def execute(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """계획을 실행합니다.

        Args:
            plan: plan()이 반환한 계획 데이터

        Returns:
            실행 결과 데이터
        """

    @abstractmethod
    def reflect(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """실행 결과를 평가합니다.

        Args:
            result: execute()가 반환한 결과

        Returns:
            {"done": bool, "feedback": str, ...}
            done=True이면 루프 종료
        """

    def run(self, task: str) -> Dict[str, Any]:
        """에이전트 메인 루프: plan -> execute -> reflect 반복.

        Args:
            task: 수행할 작업 설명

        Returns:
            최종 결과 딕셔너리
        """
        context: Dict[str, Any] = {"task": task, "iterations": []}
        final_result: Dict[str, Any] = {}

        for i in range(self.max_iterations):
            progress = i / self.max_iterations
            try:
                # Plan
                self._emit(AgentEvent(EVENT_PLAN, f"계획 수립 중 (반복 {i + 1})", iteration=i, progress=progress))
                plan_data = self.plan(task, context)

                # Execute
                self._emit(AgentEvent(
                    EVENT_EXECUTE, f"실행 중 (반복 {i + 1})",
                    data={"plan_summary": str(plan_data.get("summary", ""))[:200]},
                    iteration=i, progress=progress + 0.3 / self.max_iterations,
                ))
                result = self.execute(plan_data)
                final_result = result

                # Reflect
                self._emit(AgentEvent(
                    EVENT_REFLECT, f"결과 평가 중 (반복 {i + 1})",
                    iteration=i, progress=progress + 0.7 / self.max_iterations,
                ))
                reflection = self.reflect(result)

                # 반복 기록
                context["iterations"].append({
                    "plan": plan_data,
                    "result": result,
                    "reflection": reflection,
                })

                if reflection.get("done", False):
                    self._emit(AgentEvent(EVENT_DONE, "완료", data=result, iteration=i, progress=1.0))
                    return result

                # 다음 반복을 위해 피드백을 context에 추가
                context["feedback"] = reflection.get("feedback", "")

            except Exception as e:
                logger.error(f"[{self.name}] 반복 {i + 1} 오류: {e}")
                self._emit(AgentEvent(EVENT_ERROR, f"오류 발생: {e}", iteration=i, progress=progress))
                if final_result:
                    return final_result
                raise

        # 최대 반복 도달 — 마지막 결과 반환
        self._emit(AgentEvent(EVENT_DONE, "최대 반복 도달, 결과 반환", data=final_result, progress=1.0))
        return final_result
