"""
자가복구 파이프라인.

실패 단계를 자동 재시도하거나 대체 경로로 복구한다.
에러 유형 분류 → 복구 계획 → 복구 실행.
"""

from dataclasses import dataclass, field
import uuid


@dataclass
class HealingAction:
    """복구 액션."""
    action_id: str
    step_id: str
    action_type: str  # retry / fallback / skip
    max_retries: int
    current_attempt: int = 0
    status: str = "pending"  # pending / in_progress / success / exhausted


@dataclass
class HealingPolicy:
    """복구 정책."""
    policy_id: str
    rules: list[dict] = field(default_factory=list)
    # 각 rule: {"error_type": str, "action_type": str, "max_retries": int}


# 에러 메시지 → 유형 매핑 키워드
_ERROR_KEYWORDS = {
    "timeout": ["timeout", "timed out", "시간 초과", "deadline"],
    "invalid_input": ["invalid", "validation", "잘못된", "형식", "parse", "format"],
    "resource": ["memory", "disk", "cpu", "resource", "메모리", "리소스", "quota"],
}


def create_policy(rules: list[dict]) -> HealingPolicy:
    """
    복구 정책 생성.

    Args:
        rules: 규칙 리스트. 각 항목은 {"error_type", "action_type", "max_retries"}.

    Returns:
        생성된 HealingPolicy 객체.
    """
    return HealingPolicy(
        policy_id=uuid.uuid4().hex[:12],
        rules=rules,
    )


def diagnose_failure(step_id: str, error_msg: str) -> str:
    """
    에러 유형 분류.

    에러 메시지의 키워드를 분석하여 유형을 결정한다.

    Returns:
        "timeout" / "invalid_input" / "resource" / "unknown"
    """
    lower_msg = error_msg.lower()

    for error_type, keywords in _ERROR_KEYWORDS.items():
        for kw in keywords:
            if kw in lower_msg:
                return error_type

    return "unknown"


def plan_healing(policy: HealingPolicy, error_type: str) -> HealingAction:
    """
    복구 계획 수립.

    정책의 규칙에서 해당 error_type에 맞는 액션을 찾아
    HealingAction을 생성한다. 매칭 규칙이 없으면 기본 skip.
    """
    for rule in policy.rules:
        if rule.get("error_type") == error_type:
            return HealingAction(
                action_id=uuid.uuid4().hex[:12],
                step_id="",  # 호출자가 설정
                action_type=rule.get("action_type", "skip"),
                max_retries=rule.get("max_retries", 1),
                current_attempt=0,
                status="pending",
            )

    # 매칭 규칙 없으면 skip
    return HealingAction(
        action_id=uuid.uuid4().hex[:12],
        step_id="",
        action_type="skip",
        max_retries=0,
        current_attempt=0,
        status="pending",
    )


def apply_healing(action: HealingAction) -> HealingAction:
    """
    복구 실행.

    attempt를 증가시키고, 재시도 가능 여부에 따라 상태 변경.

    Returns:
        업데이트된 HealingAction.
    """
    action.current_attempt += 1
    action.status = "in_progress"

    if action.current_attempt >= action.max_retries:
        # 최대 재시도 도달 → exhausted
        action.status = "exhausted"
    else:
        # 재시도 성공 시뮬레이션 (순수 로직이므로 상태만 변경)
        action.status = "in_progress"

    return action


def is_recoverable(action: HealingAction) -> bool:
    """
    재시도 가능 여부.

    skip 타입이면 불가, exhausted 상태면 불가.
    """
    if action.action_type == "skip":
        return False
    if action.status == "exhausted":
        return False
    if action.current_attempt >= action.max_retries:
        return False
    return True
