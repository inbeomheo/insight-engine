"""
Delegate — 서브에이전트 위임 시스템

Hermes 패턴:
- 부모→자식 일방향 위임
- 차단 도구 목록 (재귀 위임, 사용자 상호작용 금지)
- 최대 동시 3개, 깊이 제한 2
- 독립 이터레이션 예산
- 인터럽트 전파
- ThreadPoolExecutor 병렬 실행
"""
from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

# 자식 에이전트가 사용 불가한 도구
DELEGATE_BLOCKED_TOOLS = frozenset([
    "delegate_task",      # 재귀 위임 금지
    "clarify",            # 사용자 상호작용 금지
    "memory_write",       # 공유 메모리 쓰기 금지
    "create_schedule",    # 예약 생성 금지
    "cancel_schedule",    # 예약 취소 금지
    "mcp_publish_naver",  # 발행 금지
    "mcp_publish_wordpress",
])

MAX_CONCURRENT_CHILDREN = 3
MAX_DEPTH = 2  # 0=루트, 1=자식, 2=거부
DEFAULT_CHILD_MAX_ITERATIONS = 20


@dataclass
class DelegateTask:
    """위임 작업 정의."""
    task: str
    toolsets: Optional[List[str]] = None
    max_iterations: int = DEFAULT_CHILD_MAX_ITERATIONS
    context: Optional[Dict[str, Any]] = None
    model: Optional[str] = None


@dataclass
class DelegateResult:
    """위임 결과."""
    task: str
    content: str
    success: bool
    tool_calls_count: int
    elapsed_seconds: float
    error: Optional[str] = None


class DelegateManager:
    """서브에이전트 위임 관리자.

    사용법:
        manager = DelegateManager(
            parent_model="gemini/gemini-3-flash-preview",
            parent_toolsets=["full"],
            depth=0,
        )

        # 단일 위임
        result = manager.delegate(DelegateTask(
            task="이 콘텐츠의 SEO 점수를 분석해",
            toolsets=["seo"],
            context={"content": "..."},
        ))

        # 병렬 위임
        results = manager.delegate_parallel([
            DelegateTask(task="SEO 분석", toolsets=["seo"]),
            DelegateTask(task="가독성 분석", toolsets=["analysis"]),
            DelegateTask(task="품질 검증", toolsets=["quality"]),
        ])
    """

    def __init__(
        self,
        parent_model: str,
        parent_toolsets: Sequence[str],
        depth: int = 0,
        parent_interrupt: Optional[threading.Event] = None,
    ):
        self._parent_model = parent_model
        self._parent_toolsets = list(parent_toolsets)
        self._depth = depth
        self._parent_interrupt = parent_interrupt or threading.Event()
        self._active_children: List[Any] = []
        self._lock = threading.Lock()

    def delegate(self, task: DelegateTask) -> DelegateResult:
        """단일 서브에이전트에 작업을 위임합니다.

        Args:
            task: 위임할 작업

        Returns:
            DelegateResult
        """
        if self._depth >= MAX_DEPTH:
            return DelegateResult(
                task=task.task,
                content="",
                success=False,
                tool_calls_count=0,
                elapsed_seconds=0,
                error=f"최대 위임 깊이 초과 (depth={self._depth}, max={MAX_DEPTH})",
            )

        child = self._create_child_agent(task)

        with self._lock:
            self._active_children.append(child)

        try:
            response = child.run(
                user_message=task.task,
                context=task.context,
            )
            return DelegateResult(
                task=task.task,
                content=response.content,
                success=True,
                tool_calls_count=response.tool_calls_count,
                elapsed_seconds=response.elapsed_seconds,
            )
        except Exception as e:
            logger.error("서브에이전트 실패: %s — %s", task.task[:50], e)
            return DelegateResult(
                task=task.task,
                content="",
                success=False,
                tool_calls_count=0,
                elapsed_seconds=0,
                error=str(e),
            )
        finally:
            with self._lock:
                if child in self._active_children:
                    self._active_children.remove(child)

    def delegate_parallel(
        self, tasks: List[DelegateTask]
    ) -> List[DelegateResult]:
        """여러 작업을 병렬로 위임합니다.

        Args:
            tasks: 위임할 작업 목록 (최대 MAX_CONCURRENT_CHILDREN개)

        Returns:
            DelegateResult 목록 (입력 순서 유지)
        """
        if len(tasks) > MAX_CONCURRENT_CHILDREN:
            logger.warning(
                "최대 동시 자식 수 초과: %d → %d",
                len(tasks), MAX_CONCURRENT_CHILDREN,
            )
            tasks = tasks[:MAX_CONCURRENT_CHILDREN]

        results = [None] * len(tasks)

        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_CHILDREN) as pool:
            futures: Dict[Future, int] = {}
            for idx, task in enumerate(tasks):
                future = pool.submit(self.delegate, task)
                futures[future] = idx

            for future in as_completed(futures):
                idx = futures[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    results[idx] = DelegateResult(
                        task=tasks[idx].task,
                        content="",
                        success=False,
                        tool_calls_count=0,
                        elapsed_seconds=0,
                        error=str(e),
                    )

        return results

    def interrupt_all(self) -> None:
        """모든 활성 자식 에이전트를 중단합니다."""
        self._parent_interrupt.set()
        with self._lock:
            for child in self._active_children:
                child.interrupt()
        logger.info("모든 서브에이전트 인터럽트 전파")

    def _create_child_agent(self, task: DelegateTask):
        """자식 AIAgent 인스턴스를 생성합니다."""
        from agent.core import AIAgent

        # 도구셋 결정: 명시적 지정 > 부모 도구셋
        child_toolsets = task.toolsets or self._parent_toolsets

        # 차단 도구 제거를 위해 agent_control은 제외
        child_toolsets = [ts for ts in child_toolsets if ts != "agent_control"]

        # 시스템 프롬프트: 자식 역할 명시
        system_prompt = (
            f"당신은 상위 에이전트에게 위임받은 서브에이전트입니다.\n"
            f"작업: {task.task}\n"
            f"주어진 도구를 사용하여 작업을 완료하고 결과를 반환하세요.\n"
            f"사용자에게 직접 질문하지 마세요 (clarify 도구 없음).\n"
            f"다른 에이전트에게 재위임하지 마세요 (delegate_task 도구 없음).\n"
            f"간결하고 구조화된 결과를 반환하세요."
        )

        child = AIAgent(
            model=task.model or self._parent_model,
            toolsets=child_toolsets,
            system_prompt=system_prompt,
            max_iterations=task.max_iterations,
            # 자식은 콜백 없음 (부모가 결과만 수집)
            on_stream_delta=None,
            on_tool_start=None,
            on_tool_end=None,
        )

        return child
