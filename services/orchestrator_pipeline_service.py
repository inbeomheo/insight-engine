"""
기획-병렬-합성 파이프라인 오케스트레이터.

파이프라인 단계(plan/parallel/synthesize)를 관리하고,
의존성 기반 실행 순서를 결정하며, 결과를 합성한다.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid


@dataclass
class PipelineStep:
    """파이프라인 개별 단계."""
    step_id: str
    name: str
    step_type: str  # plan / parallel / synthesize
    dependencies: list[str] = field(default_factory=list)
    status: str = "pending"  # pending / running / done / failed
    result: str = ""


@dataclass
class Pipeline:
    """파이프라인 전체 구조."""
    pipeline_id: str
    steps: list[PipelineStep] = field(default_factory=list)
    created_at: str = ""


def create_pipeline(steps_config: list[dict]) -> Pipeline:
    """
    파이프라인 생성.

    Args:
        steps_config: 각 단계 설정 리스트.
            예: [{"name": "기획", "step_type": "plan", "dependencies": []}]

    Returns:
        생성된 Pipeline 객체.
    """
    pipeline_id = uuid.uuid4().hex[:12]
    steps = []
    for cfg in steps_config:
        step = PipelineStep(
            step_id=cfg.get("step_id", uuid.uuid4().hex[:8]),
            name=cfg.get("name", ""),
            step_type=cfg.get("step_type", "plan"),
            dependencies=cfg.get("dependencies", []),
            status="pending",
            result="",
        )
        steps.append(step)

    return Pipeline(
        pipeline_id=pipeline_id,
        steps=steps,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def get_executable_steps(pipeline: Pipeline) -> list[PipelineStep]:
    """
    의존성이 충족된 실행 가능 단계를 반환.

    - status가 pending인 단계 중
    - 모든 dependencies가 done인 단계만 반환
    """
    done_ids = {s.step_id for s in pipeline.steps if s.status == "done"}

    executable = []
    for step in pipeline.steps:
        if step.status != "pending":
            continue
        # 모든 의존성이 완료되었는지 확인
        if all(dep in done_ids for dep in step.dependencies):
            executable.append(step)

    return executable


def execute_step(pipeline: Pipeline, step_id: str, result: str) -> Pipeline:
    """
    단계 실행 완료 처리.

    해당 step_id의 status를 done으로, result를 기록한다.

    Raises:
        ValueError: step_id가 존재하지 않을 때.
    """
    for step in pipeline.steps:
        if step.step_id == step_id:
            step.status = "done"
            step.result = result
            return pipeline

    raise ValueError(f"Step '{step_id}' not found in pipeline")


def synthesize_results(pipeline: Pipeline) -> str:
    """
    완료된 모든 단계 결과를 합성.

    done 상태인 단계의 result를 순서대로 합쳐서 반환.
    """
    results = []
    for step in pipeline.steps:
        if step.status == "done" and step.result:
            results.append(f"[{step.name}] {step.result}")

    if not results:
        return ""

    return "\n".join(results)


def get_pipeline_status(pipeline: Pipeline) -> dict:
    """
    전체 진행률 반환.

    Returns:
        {"total", "done", "running", "failed", "progress_pct"}
    """
    total = len(pipeline.steps)
    done = sum(1 for s in pipeline.steps if s.status == "done")
    running = sum(1 for s in pipeline.steps if s.status == "running")
    failed = sum(1 for s in pipeline.steps if s.status == "failed")
    progress_pct = (done / total * 100) if total > 0 else 0.0

    return {
        "total": total,
        "done": done,
        "running": running,
        "failed": failed,
        "progress_pct": round(progress_pct, 1),
    }
