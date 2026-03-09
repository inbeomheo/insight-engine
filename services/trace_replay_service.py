"""
트레이스 리플레이 서비스 — 파이프라인 실행 기록 및 재생
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TraceStep:
    """파이프라인 단계별 실행 기록"""
    step_name: str
    start_time: float
    end_time: float
    tokens_used: int
    cost: float
    model: str
    status: str = "success"  # 'success' / 'error'
    error_message: Optional[str] = None


@dataclass
class TraceRecord:
    """파이프라인 실행 전체 트레이스"""
    trace_id: str
    pipeline_run_id: str
    steps: list[TraceStep] = field(default_factory=list)
    total_cost: float = 0.0
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    created_at: float = field(default_factory=time.time)


@dataclass
class TraceSummary:
    """트레이스 요약 통계"""
    trace_id: str
    step_count: int
    total_cost: float
    total_tokens: int
    avg_latency_ms: float
    success_rate: float  # 0.0 ~ 1.0


class TraceReplayService:
    """인메모리 트레이스 기록 및 재생"""

    def __init__(self):
        # trace_id -> TraceRecord
        self._traces: dict[str, TraceRecord] = {}

    def record_trace(
        self,
        pipeline_run_id: str,
        steps: list[dict],
    ) -> TraceRecord:
        """단계별 실행 기록 저장"""
        if not pipeline_run_id or not pipeline_run_id.strip():
            raise ValueError("pipeline_run_id는 필수입니다")
        if not steps:
            raise ValueError("steps는 비어 있을 수 없습니다")

        # dict → TraceStep 변환
        trace_steps = []
        for s in steps:
            step = TraceStep(
                step_name=s.get("step_name", "unknown"),
                start_time=s.get("start_time", 0.0),
                end_time=s.get("end_time", 0.0),
                tokens_used=s.get("tokens_used", 0),
                cost=s.get("cost", 0.0),
                model=s.get("model", "unknown"),
                status=s.get("status", "success"),
                error_message=s.get("error_message"),
            )
            trace_steps.append(step)

        # 합계 계산
        total_cost = sum(s.cost for s in trace_steps)
        total_tokens = sum(s.tokens_used for s in trace_steps)
        total_latency_ms = sum(
            (s.end_time - s.start_time) * 1000 for s in trace_steps
        )

        record = TraceRecord(
            trace_id=f"trace_{uuid.uuid4().hex[:12]}",
            pipeline_run_id=pipeline_run_id,
            steps=trace_steps,
            total_cost=total_cost,
            total_tokens=total_tokens,
            total_latency_ms=total_latency_ms,
        )
        self._traces[record.trace_id] = record
        return record

    def replay_trace(self, trace_id: str) -> list[TraceStep]:
        """트레이스 단계별 재생 (시간순)"""
        if trace_id not in self._traces:
            raise KeyError(f"트레이스를 찾을 수 없습니다: {trace_id}")

        record = self._traces[trace_id]
        # start_time 기준 정렬
        return sorted(record.steps, key=lambda s: s.start_time)

    def get_trace_summary(self, trace_id: str) -> TraceSummary:
        """트레이스 요약 통계"""
        if trace_id not in self._traces:
            raise KeyError(f"트레이스를 찾을 수 없습니다: {trace_id}")

        record = self._traces[trace_id]
        step_count = len(record.steps)

        # 성공률 계산
        if step_count > 0:
            success_count = sum(
                1 for s in record.steps if s.status == "success"
            )
            success_rate = success_count / step_count
            avg_latency_ms = record.total_latency_ms / step_count
        else:
            success_rate = 0.0
            avg_latency_ms = 0.0

        return TraceSummary(
            trace_id=trace_id,
            step_count=step_count,
            total_cost=record.total_cost,
            total_tokens=record.total_tokens,
            avg_latency_ms=avg_latency_ms,
            success_rate=success_rate,
        )
