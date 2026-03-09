"""
리퍼포즈 기여도 서비스

원본 콘텐츠에서 파생된 콘텐츠들의 성과를 측정하고
플랫폼별 기여도와 도달 배수를 계산합니다.
"""
import logging
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class DerivativePerf:
    """파생 콘텐츠 성과"""
    derivative_id: str
    platform: str
    reach: int
    engagement: float
    contribution_pct: float


@dataclass
class RepurposeReport:
    """리퍼포즈 기여도 보고서"""
    original_id: str
    derivatives: List[DerivativePerf] = field(default_factory=list)
    total_reach: int = 0
    multiplier: float = 0.0


def _compute_contribution(derivatives: List[dict], total_reach: int) -> List[DerivativePerf]:
    """파생 콘텐츠별 기여도 백분율을 계산합니다."""
    results: List[DerivativePerf] = []

    for d in derivatives:
        reach = int(d.get("reach", 0))
        engagement = float(d.get("engagement", 0.0))
        pct = (reach / total_reach * 100) if total_reach > 0 else 0.0

        results.append(DerivativePerf(
            derivative_id=d.get("derivative_id", "unknown"),
            platform=d.get("platform", "unknown"),
            reach=reach,
            engagement=round(engagement, 4),
            contribution_pct=round(pct, 2),
        ))

    # 기여도 내림차순 정렬
    results.sort(key=lambda x: x.contribution_pct, reverse=True)
    return results


def attribute_repurpose(
    original_id: str,
    derivatives: List[dict],
) -> RepurposeReport:
    """파생 콘텐츠 기여도를 분석합니다.

    Args:
        original_id: 원본 콘텐츠 식별자.
        derivatives: 파생 콘텐츠 리스트.
            각 항목은 {"derivative_id", "platform", "reach", "engagement"} 형태.

    Returns:
        RepurposeReport: 총 도달, 배수, 파생별 기여도 정보.
    """
    if not derivatives:
        logger.warning("파생 콘텐츠가 없습니다: original_id=%s", original_id)
        return RepurposeReport(original_id=original_id)

    total_reach = sum(int(d.get("reach", 0)) for d in derivatives)

    derivative_perfs = _compute_contribution(derivatives, total_reach)

    # 원본 도달 대비 파생 도달 배수
    # 원본 reach가 없으면 첫 번째 파생(가장 큰 reach)을 원본 기준으로 사용
    original_reach = int(derivatives[0].get("original_reach", 0))
    if original_reach <= 0:
        # 원본 reach 정보가 없으면 파생 평균 대비 총합 비율
        avg_reach = total_reach / max(len(derivatives), 1)
        multiplier = total_reach / avg_reach if avg_reach > 0 else 0.0
    else:
        multiplier = total_reach / original_reach

    logger.info(
        "리퍼포즈 기여도 분석 완료: original=%s, 파생 %d개, 총 도달 %d, 배수 %.1fx",
        original_id, len(derivative_perfs), total_reach, multiplier,
    )

    return RepurposeReport(
        original_id=original_id,
        derivatives=derivative_perfs,
        total_reach=total_reach,
        multiplier=round(multiplier, 2),
    )
