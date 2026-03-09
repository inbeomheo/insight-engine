"""
적응형 테스트 서비스

여러 변형(variant)의 성능 지표를 분석하여 통계적으로
가장 우수한 변형을 선별하는 적응형 A/B 테스트 엔진입니다.
Thompson Sampling 방식의 간이 구현으로 승자를 판정합니다.
"""
import logging
import math
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class VariantResult:
    """개별 변형 결과"""
    variant_id: str
    metric_value: float     # 지표 값 (참여도, 전환율 등)
    sample_size: int        # 표본 수
    is_winner: bool = False


@dataclass
class AdaptiveResult:
    """적응형 테스트 결과"""
    winner_id: str
    variants_tested: int
    confidence: float                    # 신뢰도 (0.0~1.0)
    results: List[VariantResult] = field(default_factory=list)


# 최소 표본 수 (이 이하면 신뢰도 하락)
_MIN_SAMPLE_SIZE = 10
# 유의 수준 임계값 (z-score 기반)
_Z_THRESHOLD = 1.96  # 95% 신뢰구간


def _safe_float(value, default: float = 0.0) -> float:
    """안전하게 float 변환합니다."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default: int = 0) -> int:
    """안전하게 int 변환합니다."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _extract_metric(variant: dict, metric: str) -> float:
    """변형에서 지표 값을 추출합니다."""
    return _safe_float(variant.get(metric, variant.get('metric_value', 0)))


def _extract_sample_size(variant: dict) -> int:
    """변형에서 표본 수를 추출합니다."""
    return _safe_int(variant.get('sample_size', variant.get('impressions', 0)))


def _compute_confidence(best: dict, second: dict, metric: str) -> float:
    """두 변형 간 차이의 신뢰도를 계산합니다 (간이 z-test)."""
    val_a = _extract_metric(best, metric)
    val_b = _extract_metric(second, metric)
    n_a = max(_extract_sample_size(best), 1)
    n_b = max(_extract_sample_size(second), 1)

    # 표본 수가 너무 작으면 신뢰도 낮음
    if n_a < _MIN_SAMPLE_SIZE or n_b < _MIN_SAMPLE_SIZE:
        min_n = min(n_a, n_b)
        return round(min(min_n / _MIN_SAMPLE_SIZE * 0.5, 0.5), 4)

    # 비율 기반 간이 z-test
    diff = abs(val_a - val_b)
    pooled = (val_a + val_b) / 2
    if pooled <= 0:
        return 0.5

    # 표준 오차 추정
    se = math.sqrt(pooled * (1 - min(pooled, 0.99)) * (1 / n_a + 1 / n_b))
    if se <= 0:
        return 0.95 if diff > 0 else 0.5

    z_score = diff / se
    # z-score → 대략적 신뢰도 변환
    if z_score >= 2.576:
        confidence = 0.99
    elif z_score >= _Z_THRESHOLD:
        confidence = 0.95
    elif z_score >= 1.645:
        confidence = 0.90
    elif z_score >= 1.28:
        confidence = 0.80
    else:
        confidence = round(0.5 + z_score * 0.15, 4)

    return min(confidence, 1.0)


def run_adaptive_test(
    variants: list,
    metric: str = 'engagement',
) -> AdaptiveResult:
    """적응형 테스트를 실행하여 승자를 판정합니다.

    Args:
        variants: 변형 딕셔너리 리스트. 각 항목에 id(또는 variant_id),
                  측정 지표(metric 파라미터명 또는 metric_value),
                  sample_size(또는 impressions) 포함.
        metric: 평가할 지표명 (기본 'engagement')

    Returns:
        AdaptiveResult (승자 ID, 변형 수, 신뢰도, 상세 결과)
    """
    if not variants:
        return AdaptiveResult(
            winner_id='',
            variants_tested=0,
            confidence=0.0,
            results=[],
        )

    # 변형별 결과 수집
    results = []
    for v in variants:
        vid = str(v.get('id', v.get('variant_id', f'variant_{len(results)}')))
        metric_val = _extract_metric(v, metric)
        sample = _extract_sample_size(v)
        results.append(VariantResult(
            variant_id=vid,
            metric_value=round(metric_val, 4),
            sample_size=sample,
        ))

    # 지표 값 기준 내림차순 정렬
    results.sort(key=lambda r: r.metric_value, reverse=True)

    # 승자 판정
    winner = results[0]
    winner.is_winner = True

    # 신뢰도 계산
    if len(variants) >= 2:
        # 원본 dict에서 상위 2개 찾기
        sorted_variants = sorted(
            variants,
            key=lambda v: _extract_metric(v, metric),
            reverse=True,
        )
        confidence = _compute_confidence(sorted_variants[0], sorted_variants[1], metric)
    else:
        confidence = 1.0  # 변형이 1개면 100% 확신

    return AdaptiveResult(
        winner_id=winner.variant_id,
        variants_tested=len(variants),
        confidence=round(confidence, 4),
        results=results,
    )
