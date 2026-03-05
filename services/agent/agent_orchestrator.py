"""
에이전트 오케스트레이터 — 에이전트 순차/병렬 실행 관리
파이프라인 단계별 에이전트를 실행하고 결과를 체인으로 연결합니다.
"""
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from services.agent import AgentEvent, BaseAgent

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """에이전트 파이프라인을 순차 실행합니다.

    각 에이전트의 출력을 다음 에이전트의 context에 병합하여 전달합니다.
    """

    def __init__(self):
        self._event_listeners: List[Callable[[str, AgentEvent], None]] = []

    def on_event(self, listener: Callable[[str, AgentEvent], None]) -> None:
        """이벤트 리스너를 등록합니다.

        Args:
            listener: (agent_name, event) 콜백
        """
        self._event_listeners.append(listener)

    def _emit(self, agent_name: str, event: AgentEvent) -> None:
        for listener in self._event_listeners:
            try:
                listener(agent_name, event)
            except Exception as e:
                logger.warning(f"오케스트레이터 이벤트 오류: {e}")

    def run_pipeline(
        self,
        agents: List[BaseAgent],
        task: str,
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """에이전트 리스트를 순차 실행합니다.

        각 에이전트의 출력이 다음 에이전트의 context에 병합됩니다.

        Args:
            agents: 실행할 에이전트 리스트 (순서대로)
            task: 전체 작업 설명
            initial_context: 초기 컨텍스트

        Returns:
            최종 병합된 결과 딕셔너리
        """
        merged: Dict[str, Any] = dict(initial_context or {})
        merged["task"] = task

        results: List[Dict[str, Any]] = []
        total = len(agents)
        start_time = time.time()

        for idx, agent in enumerate(agents):
            agent_name = agent.name
            logger.info(f"파이프라인 단계 {idx + 1}/{total}: {agent_name} 시작")

            # 에이전트에 오케스트레이터 이벤트 포워딩 연결
            agent.on_event(lambda evt, name=agent_name: self._emit(name, evt))

            # 에이전트의 context에 이전 결과 전달 (run 내부에서 task만 사용)
            # plan()에서 context를 통해 이전 결과 접근
            # 단, BaseAgent.run()은 task만 받으므로 context를 에이전트 속성으로 전달
            agent._pipeline_context = merged

            # run() 대신 직접 단계 실행 (context 전달 위해)
            result = self._run_agent_with_context(agent, task, merged)
            results.append({"agent": agent_name, "result": result})

            # 결과를 다음 에이전트 context에 병합
            merged.update(result)

        elapsed = time.time() - start_time
        return {
            "pipeline_results": results,
            "final": merged,
            "elapsed_seconds": round(elapsed, 2),
            "agent_count": total,
        }

    def _run_agent_with_context(
        self, agent: BaseAgent, task: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """에이전트를 context와 함께 실행합니다."""
        final_result: Dict[str, Any] = {}

        for i in range(agent.max_iterations):
            try:
                plan_data = agent.plan(task, context)
                result = agent.execute(plan_data)
                final_result = result
                reflection = agent.reflect(result)

                if reflection.get("done", False):
                    return result

                context["feedback"] = reflection.get("feedback", "")
            except Exception as e:
                logger.error(f"[{agent.name}] 실행 오류: {e}")
                if final_result:
                    return final_result
                raise

        return final_result
