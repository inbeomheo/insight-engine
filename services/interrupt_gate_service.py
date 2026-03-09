"""인터럽트 게이트 서비스 — 파이프라인 일시정지 및 결정 관리"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class GateState:
    """게이트 상태 객체"""
    gate_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    pipeline_id: str = ""
    step: str = ""
    status: str = "pending"  # pending → approved / rejected / edited
    decision: str | None = None  # approve / reject / edit
    edits: dict | None = None  # edit 결정 시 수정 내용
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    decided_at: str | None = None


# 유효한 결정 값
_VALID_DECISIONS = {"approve", "reject", "edit"}

# 유효한 상태 전이: decision → 결과 status
_DECISION_TO_STATUS = {
    "approve": "approved",
    "reject": "rejected",
    "edit": "edited",
}

# 인메모리 저장소
_gates: dict[str, GateState] = {}


def _reset_store():
    """테스트용: 저장소 초기화"""
    _gates.clear()


def create_gate(pipeline_id: str, step: str) -> GateState:
    """파이프라인 일시정지 게이트를 생성합니다.

    Args:
        pipeline_id: 파이프라인 식별자
        step: 정지할 단계명

    Returns:
        생성된 GateState (status='pending')

    Raises:
        ValueError: pipeline_id 또는 step이 비어있을 때
    """
    if not pipeline_id or not pipeline_id.strip():
        raise ValueError("pipeline_id는 비어있을 수 없습니다")
    if not step or not step.strip():
        raise ValueError("step은 비어있을 수 없습니다")

    gate = GateState(pipeline_id=pipeline_id.strip(), step=step.strip())
    _gates[gate.gate_id] = gate
    return gate


def get_gate(gate_id: str) -> GateState | None:
    """게이트 조회. 없으면 None 반환."""
    return _gates.get(gate_id)


def submit_gate_decision(gate_id: str, decision: str, edits: dict | None = None) -> GateState:
    """게이트에 결정을 제출합니다.

    Args:
        gate_id: 게이트 식별자
        decision: 'approve', 'reject', 'edit' 중 하나
        edits: 'edit' 결정 시 수정 내용 dict (선택)

    Returns:
        결정이 반영된 GateState

    Raises:
        ValueError: gate_id가 존재하지 않거나, decision이 유효하지 않거나,
                    이미 결정된 게이트에 재결정 시도 시
    """
    gate = _gates.get(gate_id)
    if gate is None:
        raise ValueError(f"게이트를 찾을 수 없습니다: {gate_id}")

    if gate.status != "pending":
        raise ValueError(f"이미 결정된 게이트입니다 (현재 상태: {gate.status})")

    if decision not in _VALID_DECISIONS:
        raise ValueError(f"유효하지 않은 결정입니다: {decision} (허용: {', '.join(sorted(_VALID_DECISIONS))})")

    if decision == "edit" and not edits:
        raise ValueError("edit 결정 시 edits는 필수입니다")

    gate.status = _DECISION_TO_STATUS[decision]
    gate.decision = decision
    gate.edits = edits if decision == "edit" else None
    gate.decided_at = datetime.now(timezone.utc).isoformat()

    return gate


def list_gates(pipeline_id: str | None = None, status: str | None = None) -> list[GateState]:
    """게이트 목록 조회 (필터 선택적).

    Args:
        pipeline_id: 특정 파이프라인으로 필터 (선택)
        status: 특정 상태로 필터 (선택)

    Returns:
        조건에 맞는 GateState 리스트
    """
    result = list(_gates.values())
    if pipeline_id:
        result = [g for g in result if g.pipeline_id == pipeline_id]
    if status:
        result = [g for g in result if g.status == status]
    return result
