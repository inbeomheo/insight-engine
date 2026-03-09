"""
실험 캔버스 서비스 — A/B 테스트 실험 설계
"""

import uuid
import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Experiment:
    """실험"""
    exp_id: str
    name: str
    hypothesis: str
    variants: list[dict]
    metric: str
    status: str  # draft / running / completed
    sample_size: int


@dataclass
class ExperimentResult:
    """실험 결과"""
    exp_id: str
    winner: Optional[str]
    confidence: float
    variant_metrics: dict


def design_experiment(name: str, hypothesis: str, variants: list[dict], metric: str) -> Experiment:
    """실험 설계"""
    return Experiment(
        exp_id=str(uuid.uuid4())[:8],
        name=name,
        hypothesis=hypothesis,
        variants=variants,
        metric=metric,
        status='draft',
        sample_size=0
    )


def calculate_sample_size(baseline_rate: float, min_effect: float, confidence: float = 0.95) -> int:
    """필요 샘플 크기 계산 (비율 차이 기반 근사)"""
    if baseline_rate <= 0 or baseline_rate >= 1:
        return 0
    if min_effect <= 0:
        return 0

    # Z-score 근사
    z_scores = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    z = z_scores.get(confidence, 1.96)
    z_beta = 0.84  # 80% 파워

    p1 = baseline_rate
    p2 = baseline_rate + min_effect
    p_avg = (p1 + p2) / 2

    numerator = (z * math.sqrt(2 * p_avg * (1 - p_avg)) + z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    denominator = (p2 - p1) ** 2

    return math.ceil(numerator / denominator)


def evaluate_results(experiment: Experiment, data: dict) -> ExperimentResult:
    """실험 결과 평가 — 비율 비교"""
    variant_metrics = {}
    best_variant = None
    best_rate = -1.0

    for variant in experiment.variants:
        name = variant.get('name', '')
        v_data = data.get(name, {})
        total = v_data.get('total', 0)
        conversions = v_data.get('conversions', 0)
        rate = conversions / total if total > 0 else 0.0
        variant_metrics[name] = round(rate, 4)

        if rate > best_rate:
            best_rate = rate
            best_variant = name

    # 간단한 신뢰도: 샘플 크기 기반
    total_samples = sum(d.get('total', 0) for d in data.values())
    confidence = min(0.99, total_samples / max(experiment.sample_size, 1))

    rates = list(variant_metrics.values())
    winner = best_variant if len(rates) >= 2 and max(rates) - min(rates) > 0.01 else None

    return ExperimentResult(
        exp_id=experiment.exp_id,
        winner=winner,
        confidence=round(confidence, 3),
        variant_metrics=variant_metrics
    )


def is_significant(result: ExperimentResult, threshold: float = 0.95) -> bool:
    """통계 유의성 판단"""
    return result.confidence >= threshold and result.winner is not None
