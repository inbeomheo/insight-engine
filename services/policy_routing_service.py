"""
정책 기반 콘텐츠 라우팅 서비스.

콘텐츠 속성에 따라 적절한 처리 파이프라인으로 라우팅한다.
조건(eq/contains/gt/lt/in)을 평가하고 우선순위 높은 매칭 정책을 선택.
"""

import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RoutingPolicy:
    """라우팅 정책 정의."""
    policy_id: str
    name: str
    conditions: list  # list[dict] — {field, operator, value}
    target_pipeline: str
    priority: int  # 높을수록 우선


@dataclass
class RoutingDecision:
    """라우팅 결정 결과."""
    content_id: str
    matched_policy: str
    target_pipeline: str
    reason: str


def create_policy(
    name: str,
    conditions: list,
    target: str,
    priority: int = 0,
) -> RoutingPolicy:
    """새 라우팅 정책을 생성한다."""
    policy_id = f"pol_{uuid.uuid4().hex[:8]}"
    return RoutingPolicy(
        policy_id=policy_id,
        name=name,
        conditions=conditions,
        target_pipeline=target,
        priority=priority,
    )


def match_condition(content: dict, condition: dict) -> bool:
    """단일 조건을 평가한다.

    지원 연산자: eq, contains, gt, lt, in
    """
    field_name = condition.get("field", "")
    operator = condition.get("operator", "eq")
    value = condition.get("value")

    content_value = content.get(field_name)
    if content_value is None:
        return False

    if operator == "eq":
        return content_value == value
    elif operator == "contains":
        return str(value) in str(content_value)
    elif operator == "gt":
        try:
            return float(content_value) > float(value)
        except (ValueError, TypeError):
            return False
    elif operator == "lt":
        try:
            return float(content_value) < float(value)
        except (ValueError, TypeError):
            return False
    elif operator == "in":
        if isinstance(value, list):
            return content_value in value
        return False
    else:
        return False


def evaluate_content(
    content: dict,
    policies: list,
) -> RoutingDecision:
    """콘텐츠를 평가해 우선순위 높은 매칭 정책으로 라우팅한다."""
    content_id = content.get("id", "unknown")

    # 우선순위 내림차순 정렬
    sorted_policies = sorted(policies, key=lambda p: p.priority, reverse=True)

    for policy in sorted_policies:
        # 모든 조건이 충족되어야 매칭
        all_match = all(
            match_condition(content, cond) for cond in policy.conditions
        )
        if all_match:
            return RoutingDecision(
                content_id=content_id,
                matched_policy=policy.name,
                target_pipeline=policy.target_pipeline,
                reason=f"정책 '{policy.name}' 조건 {len(policy.conditions)}개 모두 충족 (우선순위: {policy.priority})",
            )

    # 매칭 정책 없으면 기본 라우트
    default = get_default_route(content)
    return RoutingDecision(
        content_id=content_id,
        matched_policy="default",
        target_pipeline=default,
        reason="매칭되는 정책 없음 — 기본 라우트 적용",
    )


def get_default_route(content: dict) -> str:
    """매칭 정책 없을 때 기본 라우트를 결정한다."""
    content_type = content.get("type", "")
    # 콘텐츠 유형별 기본 파이프라인
    defaults = {
        "blog": "standard_blog_pipeline",
        "video": "video_processing_pipeline",
        "social": "social_media_pipeline",
        "newsletter": "newsletter_pipeline",
    }
    return defaults.get(content_type, "general_pipeline")
