"""
인라인 승인 서비스 — 파이프라인 단계별 승인/거절 관리
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Action:
    """승인 대기 액션"""
    action_id: str
    pipeline_id: str
    step_name: str
    content_preview: str
    status: str = "pending"  # 'pending' → 'approved' / 'rejected'
    created_at: float = field(default_factory=time.time)


@dataclass
class ActionResult:
    """승인/거절 결과"""
    action_id: str
    decision: str  # 'approve' / 'reject'
    decided_at: float = field(default_factory=time.time)
    next_step: Optional[str] = None


class InlineApprovalService:
    """인메모리 인라인 승인 관리"""

    def __init__(self):
        # action_id -> Action
        self._actions: dict[str, Action] = {}

    def create_action(
        self,
        pipeline_id: str,
        step_name: str,
        content_preview: str,
    ) -> Action:
        """승인 대기 액션 생성"""
        if not pipeline_id or not pipeline_id.strip():
            raise ValueError("pipeline_id는 필수입니다")
        if not step_name or not step_name.strip():
            raise ValueError("step_name은 필수입니다")

        action = Action(
            action_id=f"act_{uuid.uuid4().hex[:12]}",
            pipeline_id=pipeline_id,
            step_name=step_name,
            content_preview=content_preview,
        )
        self._actions[action.action_id] = action
        return action

    def submit_action(self, action_id: str, decision: str) -> ActionResult:
        """인라인 승인/거절 처리"""
        if action_id not in self._actions:
            raise KeyError(f"액션을 찾을 수 없습니다: {action_id}")

        action = self._actions[action_id]

        if action.status != "pending":
            raise ValueError(
                f"이미 결정된 액션입니다 (현재 상태: {action.status})"
            )

        if decision not in ("approve", "reject"):
            raise ValueError(
                f"잘못된 결정입니다: {decision} (approve 또는 reject만 가능)"
            )

        # 상태 전이
        action.status = "approved" if decision == "approve" else "rejected"

        # approve 시 next_step 자동 계산
        next_step = None
        if decision == "approve":
            next_step = f"{action.step_name}_next"

        return ActionResult(
            action_id=action_id,
            decision=decision,
            next_step=next_step,
        )

    def list_pending_actions(
        self, pipeline_id: Optional[str] = None
    ) -> list[Action]:
        """대기 중 액션 조회"""
        pending = [
            a for a in self._actions.values() if a.status == "pending"
        ]
        if pipeline_id is not None:
            pending = [a for a in pending if a.pipeline_id == pipeline_id]
        # 생성 시간 오름차순
        pending.sort(key=lambda a: a.created_at)
        return pending
