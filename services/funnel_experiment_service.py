"""
퍼널 실험 서비스 — 전환 퍼널 A/B 테스트
"""

import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FunnelStep:
    """퍼널 단계"""
    step_id: str
    name: str
    visitors: int
    conversions: int
    conversion_rate: float


@dataclass
class FunnelExperiment:
    """퍼널 실험"""
    exp_id: str
    name: str
    control_funnel: list[FunnelStep]
    variant_funnel: list[FunnelStep]
    winner: Optional[str]


def create_funnel(steps_config: list[dict]) -> list[FunnelStep]:
    """퍼널 생성 — conversion_rate 자동 계산"""
    steps = []
    for sc in steps_config:
        visitors = sc.get('visitors', 0)
        conversions = sc.get('conversions', 0)
        rate = round(conversions / max(visitors, 1), 4)

        steps.append(FunnelStep(
            step_id=str(uuid.uuid4())[:8],
            name=sc.get('name', ''),
            visitors=visitors,
            conversions=conversions,
            conversion_rate=rate
        ))

    return steps


def compare_funnels(control: list[FunnelStep], variant: list[FunnelStep]) -> FunnelExperiment:
    """퍼널 비교"""
    # 전체 전환율 비교
    control_overall = _overall_rate(control)
    variant_overall = _overall_rate(variant)

    if variant_overall > control_overall + 0.01:
        winner = 'variant'
    elif control_overall > variant_overall + 0.01:
        winner = 'control'
    else:
        winner = None

    return FunnelExperiment(
        exp_id=str(uuid.uuid4())[:8],
        name='퍼널 비교 실험',
        control_funnel=control,
        variant_funnel=variant,
        winner=winner
    )


def find_bottleneck(funnel: list[FunnelStep]) -> FunnelStep:
    """병목 단계 — 최저 전환율"""
    if not funnel:
        raise ValueError("빈 퍼널")

    return min(funnel, key=lambda s: s.conversion_rate)


def calculate_lift(control_rate: float, variant_rate: float) -> float:
    """리프트 계산 (%)"""
    if control_rate <= 0:
        return 0.0
    return round((variant_rate - control_rate) / control_rate * 100, 2)


def _overall_rate(funnel: list[FunnelStep]) -> float:
    """퍼널 전체 전환율"""
    if not funnel:
        return 0.0
    rate = 1.0
    for step in funnel:
        rate *= step.conversion_rate
    return rate
