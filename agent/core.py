"""
AIAgent 코어 — 동기식 while 루프 + LiteLLM + Tool Registry

Hermes Agent 패턴 참고:
- 단일 AIAgent 클래스 (서브클래스 없이 설정으로 분화)
- 동기식 while 루프 (Flask 호환)
- 도구 호출 자동 처리 + 병렬 실행
- 스트리밍 콜백
- 이터레이션 예산
- 컨텍스트 압축
"""
from __future__ import annotations

import json
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

from agent.registry import registry
from agent.toolsets import resolve_toolsets
from agent.memory import AgentMemoryStore, memory_store

logger = logging.getLogger(__name__)

# 병렬 실행 안전한 도구 (읽기 전용, 부작용 없음)
PARALLEL_SAFE_TOOLS = frozenset([
    # 분석 도구 (전부 읽기 전용)
    "analyze_readability", "analyze_sentiment", "analyze_complexity",
    "check_heading_hierarchy",
    # 수집 도구
    "collect_webpage", "collect_youtube", "detect_source_type",
    # 검색
    "rag_query", "memory_search", "web_search",
])

# 절대 병렬 실행 불가 (사용자 상호작용, 상태 변경)
NEVER_PARALLEL = frozenset([
    "clarify", "delegate_task", "memory_write",
    "create_schedule", "cancel_schedule",
    "mcp_publish_naver", "mcp_publish_wordpress",
])

MAX_PARALLEL_WORKERS = 6


@dataclass
class IterationBudget:
    """스레드 세이프 이터레이션 예산."""
    max_iterations: int
    _used: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def remaining(self) -> int:
        with self._lock:
            return max(0, self.max_iterations - self._used)

    def consume(self, n: int = 1) -> bool:
        """예산 소비. 성공하면 True."""
        with self._lock:
            if self._used + n > self.max_iterations:
                return False
            self._used += n
            return True

    def refund(self, n: int = 1) -> None:
        """예산 환급 (execute_code 등)."""
        with self._lock:
            self._used = max(0, self._used - n)


@dataclass
class AgentResponse:
    """에이전트 실행 결과."""
    content: str
    messages: List[Dict[str, Any]]
    tool_calls_count: int
    iterations_used: int
    elapsed_seconds: float
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AIAgent:
    """범용 AI 에이전트.

    설정으로 역할을 분화합니다:
    - toolsets: 사용 가능한 도구 그룹
    - system_prompt: 역할별 시스템 프롬프트
    - model: LiteLLM 모델 ID
    - max_iterations: 최대 반복 횟수

    사용법:
        agent = AIAgent(
            model="gemini/gemini-3-flash-preview",
            toolsets=["role_writer"],
            system_prompt="당신은 콘텐츠 작성 전문가입니다.",
        )
        response = agent.run("YouTube 영상에서 블로그 글을 작성해주세요.")
    """

    def __init__(
        self,
        model: Optional[str] = None,
        toolsets: Optional[Sequence[str]] = None,
        system_prompt: str = "",
        max_iterations: int = 30,
        temperature: float = 0.7,
        max_tokens: int = 8000,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        memory_store_instance: Optional[AgentMemoryStore] = None,
        # 콜백
        on_stream_delta: Optional[Callable[[str], None]] = None,
        on_tool_start: Optional[Callable[[str, Dict], None]] = None,
        on_tool_end: Optional[Callable[[str, str, float], None]] = None,
        on_iteration: Optional[Callable[[int, int], None]] = None,
        # 설정
        enable_parallel_tools: bool = True,
        enable_compression: bool = True,
        compression_threshold: float = 0.5,
    ):
        # 모델 설정
        from config import coerce_deployment_model
        self.model = coerce_deployment_model(model or self._get_default_model())
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.user_id = user_id

        # 도구 설정
        self._toolset_names = list(toolsets or ["full"])
        self._resolved_tools = resolve_toolsets(self._toolset_names)

        # 시스템 프롬프트
        self._base_system_prompt = system_prompt or self._default_system_prompt()

        # 메모리
        self._memory = memory_store_instance or memory_store

        # 세션
        self._session_id = session_id
        self._session = None

        # 예산
        self._budget = IterationBudget(max_iterations=max_iterations)

        # 콜백
        self._on_stream_delta = on_stream_delta
        self._on_tool_start = on_tool_start
        self._on_tool_end = on_tool_end
        self._on_iteration = on_iteration

        # 설정
        self._enable_parallel = enable_parallel_tools
        self._enable_compression = enable_compression
        self._compression_threshold = compression_threshold

        # 인터럽트
        self._interrupt_requested = False
        self._interrupt_lock = threading.Lock()

    def run(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """에이전트 메인 루프를 실행합니다.

        Args:
            user_message: 사용자 입력 메시지
            context: 추가 컨텍스트 (이전 에이전트 결과 등)

        Returns:
            AgentResponse
        """
        start_time = time.time()

        # 세션 초기화: 기존 세션 로드 또는 새로 생성
        if not self._session:
            if self._session_id:
                # 기존 세션 복원
                self._session = self._memory.get_session(self._session_id)
            if not self._session:
                # 새 세션 생성 (동결 스냅샷)
                self._session = self._memory.create_session(
                    model=self.model,
                    base_system_prompt=self._base_system_prompt,
                    user_id=self.user_id,
                )
                self._session_id = self._session.session_id

        # 메시지 히스토리 구성
        messages = self._build_initial_messages(user_message, context)

        # 도구 스키마 준비
        tool_schemas = self._get_tool_schemas()

        # 메인 루프
        iterations_used = 0
        tool_calls_count = 0

        while self._budget.remaining > 0:
            # 인터럽트 체크
            with self._interrupt_lock:
                if self._interrupt_requested:
                    logger.info("에이전트 인터럽트 — 루프 중단")
                    break

            if not self._budget.consume():
                logger.warning("이터레이션 예산 소진")
                break

            iterations_used += 1

            # 콜백
            if self._on_iteration:
                self._on_iteration(iterations_used, self._budget.max_iterations)

            # LLM API 호출
            try:
                response = self._call_llm(messages, tool_schemas)
            except Exception as e:
                logger.error("LLM 호출 실패: %s", e)
                return AgentResponse(
                    content=f"AI 호출 실패: {e}",
                    messages=messages,
                    tool_calls_count=tool_calls_count,
                    iterations_used=iterations_used,
                    elapsed_seconds=time.time() - start_time,
                    session_id=self._session_id,
                    metadata={"error": str(e)},
                )

            assistant_message = response.choices[0].message

            # assistant 메시지 저장
            msg_dict = {"role": "assistant", "content": assistant_message.content or ""}
            if assistant_message.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in assistant_message.tool_calls
                ]
            messages.append(msg_dict)

            # 도구 호출이 없으면 완료
            if not assistant_message.tool_calls:
                final_content = assistant_message.content or ""

                # 세션에 메시지 저장
                self._memory.add_message(
                    self._session_id, "assistant", final_content,
                )

                elapsed = time.time() - start_time
                logger.info(
                    "에이전트 완료: %d회 반복, %d도구 호출, %.1f초",
                    iterations_used, tool_calls_count, elapsed,
                )

                return AgentResponse(
                    content=final_content,
                    messages=messages,
                    tool_calls_count=tool_calls_count,
                    iterations_used=iterations_used,
                    elapsed_seconds=elapsed,
                    session_id=self._session_id,
                )

            # 도구 호출 처리
            tool_calls = assistant_message.tool_calls
            tool_calls_count += len(tool_calls)

            tool_results = self._process_tool_calls(tool_calls)
            messages.extend(tool_results)

            # 컨텍스트 압축 체크
            if self._enable_compression:
                messages = self._maybe_compress(messages, response.usage)

        # 예산 소진 — 마지막 응답 반환
        elapsed = time.time() - start_time
        last_content = ""
        for msg in reversed(messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                last_content = msg["content"]
                break

        return AgentResponse(
            content=last_content or "이터레이션 예산이 소진되었습니다.",
            messages=messages,
            tool_calls_count=tool_calls_count,
            iterations_used=iterations_used,
            elapsed_seconds=elapsed,
            session_id=self._session_id,
            metadata={"budget_exhausted": True},
        )

    def interrupt(self) -> None:
        """에이전트 루프를 안전하게 중단합니다."""
        with self._interrupt_lock:
            self._interrupt_requested = True

    # ── LLM 호출 ──

    def _call_llm(self, messages: List[Dict], tools: List[Dict]) -> Any:
        """LiteLLM을 통해 LLM API를 호출합니다."""
        import os
        from litellm import completion

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": 180,
        }

        # 도구가 있으면 추가
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        # 모델별 특수 설정
        if self.model.startswith("gemini/") and "lite" not in self.model.lower():
            kwargs["reasoning_effort"] = "minimal"

        elif self.model.startswith("zhipuai/"):
            zhipuai_key = os.getenv("ZHIPUAI_API_KEY")
            if zhipuai_key:
                kwargs["model"] = f"openai/{self.model.replace('zhipuai/', '')}"
                kwargs["api_base"] = "https://open.bigmodel.cn/api/paas/v4/"
                kwargs["api_key"] = zhipuai_key

        elif self.model.startswith("cliproxy/"):
            kwargs["model"] = f"openai/{self.model.replace('cliproxy/', '', 1)}"
            kwargs["api_base"] = os.getenv("CLIPROXY_BASE_URL", "http://127.0.0.1:8317/v1")
            kwargs["api_key"] = os.getenv("CLIPROXY_API_KEY", "")
            kwargs["drop_params"] = True
            kwargs.pop("temperature", None)

        # 스트리밍 콜백이 있으면 스트리밍 모드
        if self._on_stream_delta:
            kwargs["stream"] = True
            response = completion(**kwargs)
            return self._collect_stream(response)

        return completion(**kwargs)

    def _collect_stream(self, stream) -> Any:
        """스트리밍 응답을 수집하며 델타 콜백을 호출합니다."""
        from litellm import ModelResponse
        from litellm.utils import StreamingChoices, Message, Delta

        collected_content = ""
        collected_tool_calls = []
        usage = None

        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue

            # 텍스트 델타
            if delta.content:
                collected_content += delta.content
                if self._on_stream_delta:
                    self._on_stream_delta(delta.content)

            # 도구 호출 델타
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    while len(collected_tool_calls) <= idx:
                        collected_tool_calls.append({
                            "id": "", "type": "function",
                            "function": {"name": "", "arguments": ""},
                        })
                    tc = collected_tool_calls[idx]
                    if tc_delta.id:
                        tc["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            tc["function"]["name"] += tc_delta.function.name
                        if tc_delta.function.arguments:
                            tc["function"]["arguments"] += tc_delta.function.arguments

            # 사용량
            if hasattr(chunk, "usage") and chunk.usage:
                usage = chunk.usage

        # ModelResponse 형태로 재조립
        response = ModelResponse()
        response.choices[0].message.content = collected_content or None

        if collected_tool_calls:
            tool_calls_objs = []
            for tc in collected_tool_calls:
                from types import SimpleNamespace
                fn = SimpleNamespace(
                    name=tc["function"]["name"],
                    arguments=tc["function"]["arguments"],
                )
                tool_calls_objs.append(SimpleNamespace(
                    id=tc["id"], type="function", function=fn,
                ))
            response.choices[0].message.tool_calls = tool_calls_objs

        if usage:
            response.usage = usage

        return response

    # ── 도구 호출 처리 ──

    def _process_tool_calls(self, tool_calls: list) -> List[Dict]:
        """도구 호출 배치를 처리합니다. 가능하면 병렬 실행."""
        if len(tool_calls) == 1 or not self._enable_parallel:
            return self._process_sequential(tool_calls)

        if self._should_parallelize(tool_calls):
            return self._process_parallel(tool_calls)

        return self._process_sequential(tool_calls)

    def _should_parallelize(self, tool_calls: list) -> bool:
        """배치를 병렬 실행해도 안전한지 판단."""
        names = [tc.function.name for tc in tool_calls]
        # 하나라도 병렬 불가 도구가 있으면 순차
        if any(n in NEVER_PARALLEL for n in names):
            return False
        # 전부 병렬 안전 도구면 병렬
        if all(n in PARALLEL_SAFE_TOOLS for n in names):
            return True
        # 미등록 도구는 보수적으로 순차
        return False

    def _process_sequential(self, tool_calls: list) -> List[Dict]:
        """도구 호출을 순차 실행합니다."""
        results = []
        for tc in tool_calls:
            result = self._execute_single_tool(tc)
            results.append(result)
        return results

    def _process_parallel(self, tool_calls: list) -> List[Dict]:
        """도구 호출을 병렬 실행합니다."""
        results = [None] * len(tool_calls)

        with ThreadPoolExecutor(max_workers=min(len(tool_calls), MAX_PARALLEL_WORKERS)) as pool:
            futures = {
                pool.submit(self._execute_single_tool, tc): idx
                for idx, tc in enumerate(tool_calls)
            }
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    results[idx] = {
                        "role": "tool",
                        "tool_call_id": tool_calls[idx].id,
                        "content": json.dumps({"error": str(e)}, ensure_ascii=False),
                    }

        return [r for r in results if r is not None]

    def _execute_single_tool(self, tool_call) -> Dict:
        """단일 도구를 실행합니다."""
        name = tool_call.function.name
        try:
            args = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            args = {}

        # 콜백
        if self._on_tool_start:
            self._on_tool_start(name, args)

        start = time.time()
        result = registry.dispatch(
            name, args,
            session_id=self._session_id,
            user_id=self.user_id,
        )
        elapsed = time.time() - start

        # 콜백
        if self._on_tool_end:
            self._on_tool_end(name, result[:200], elapsed)

        # 도구 사용 기록
        self._memory.log_tool_usage(
            session_id=self._session_id or "",
            tool_name=name,
            args=args,
            result_summary=result[:200] if result else None,
            elapsed_ms=int(elapsed * 1000),
            success="error" not in result.lower() if result else False,
        )

        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": result,
        }

    # ── 메시지 구성 ──

    def _build_initial_messages(
        self, user_message: str, context: Optional[Dict] = None
    ) -> List[Dict]:
        """초기 메시지 리스트를 구성합니다."""
        messages = []

        # 시스템 프롬프트 (동결 스냅샷 사용)
        system_prompt = self._session.system_prompt_snapshot if self._session else self._base_system_prompt

        # 컨텍스트 주입
        if context:
            context_block = "\n\n<context>\n"
            for k, v in context.items():
                if isinstance(v, str) and len(v) > 500:
                    context_block += f"## {k}\n{v[:2000]}...\n\n"
                else:
                    context_block += f"## {k}\n{v}\n\n"
            context_block += "</context>"
            system_prompt += context_block

        messages.append({"role": "system", "content": system_prompt})

        # 이전 세션 히스토리 복원
        if self._session_id:
            history = self._memory.get_messages(self._session_id)
            messages.extend(history)

        # 사용자 메시지 추가
        messages.append({"role": "user", "content": user_message})
        self._memory.add_message(self._session_id or "", "user", user_message)

        return messages

    def _get_tool_schemas(self) -> List[Dict]:
        """현재 Toolset에 맞는 도구 스키마 반환.

        toolsets.py의 하드코딩 이름 대신 registry의 toolset 그룹을 사용합니다.
        합성 Toolset(role_writer 등)은 leaf toolset 이름으로 풀어서 registry 조회.
        """
        from agent.toolsets import resolve_toolset_names

        # 합성 Toolset → leaf toolset 이름 해석
        leaf_names = resolve_toolset_names(self._toolset_names)

        # registry에서 해당 toolset에 속한 가용 도구 스키마 반환
        return registry.get_schemas(toolsets=leaf_names, available_only=True)

    # ── 컨텍스트 압축 ──

    def _maybe_compress(self, messages: List[Dict], usage: Any) -> List[Dict]:
        """필요 시 컨텍스트를 압축합니다."""
        if not usage or not hasattr(usage, "prompt_tokens"):
            return messages

        # 모델별 컨텍스트 윈도우 추정
        ctx_window = self._estimate_context_window()
        threshold = int(ctx_window * self._compression_threshold)

        if usage.prompt_tokens < threshold:
            return messages

        logger.info(
            "컨텍스트 압축 시작: %d tokens (임계값: %d)",
            usage.prompt_tokens, threshold,
        )

        try:
            from agent.compressor import compress_messages
            return compress_messages(messages, target_tokens=threshold)
        except ImportError:
            # compressor가 아직 없으면 단순 프루닝
            return self._simple_prune(messages)

    def _simple_prune(self, messages: List[Dict]) -> List[Dict]:
        """단순 프루닝: 오래된 도구 결과를 축약합니다."""
        pruned = []
        for i, msg in enumerate(messages):
            if msg.get("role") == "tool" and i < len(messages) - 10:
                content = msg.get("content", "")
                if len(content) > 200:
                    msg = {**msg, "content": content[:200] + "... [축약됨]"}
            pruned.append(msg)
        return pruned

    def _estimate_context_window(self) -> int:
        """모델의 컨텍스트 윈도우 크기를 추정합니다."""
        model = self.model.lower()
        if "gemini" in model:
            return 1_000_000
        if "claude" in model:
            return 200_000
        if "gpt-4" in model or "gpt-5" in model:
            return 128_000
        if "deepseek" in model:
            return 64_000
        return 32_000  # 기본값

    # ── 기본값 ──

    @staticmethod
    def _get_default_model() -> str:
        """사용 가능한 기본 모델을 반환합니다.

        우선순위: config.AGENT_DEFAULT_MODEL → 환경변수 기반 자동 선택
        """
        import os
        # config.py의 AGENT_DEFAULT_MODEL 우선
        try:
            from config import AGENT_DEFAULT_MODEL
            if AGENT_DEFAULT_MODEL:
                return AGENT_DEFAULT_MODEL
        except (ImportError, AttributeError):
            pass
        if os.getenv("GEMINI_API_KEY"):
            return "gemini/gemini-3-flash-preview"
        if os.getenv("DEEPSEEK_API_KEY"):
            return "deepseek/deepseek-chat"
        if os.getenv("ANTHROPIC_API_KEY"):
            return "anthropic/claude-sonnet-4-6"
        if os.getenv("OPENAI_API_KEY"):
            return "gpt-4o"
        return "gemini/gemini-3-flash-preview"

    @staticmethod
    def _default_system_prompt() -> str:
        return (
            "당신은 Insight Engine의 AI 에이전트입니다.\n"
            "사용자의 콘텐츠 생성 요청을 처리합니다.\n"
            "도구를 활용하여 URL에서 콘텐츠를 수집하고, 분석하고, "
            "고품질 콘텐츠를 작성합니다.\n"
            "항상 한국어로 응답합니다."
        )
