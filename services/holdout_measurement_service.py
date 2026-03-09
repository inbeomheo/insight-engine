"""
홀드아웃 측정 서비스

실험 데이터에서 처리 효과(treatment effect)를 계산하고
신뢰 구간 및 통계적 유의성을 판별합니다.
"""
import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


@dataclass
class HoldoutResult:
    """홀드아웃 측정 결과"""
    experiment_id: str
    treatment_effect: float
    confidence_interval: Tuple[float, float]
    significant: bool
    sample_sizes: Dict[str, int] = field(default_factory=dict)


# 95% 신뢰수준 z-값
_Z_95 = 1.96


def _mean(values: List[float]) -> float:
    """평균 계산"""
    if not values:
        return 0.0
    return sum(values) / len(values)


def _std(values: List[float], mean_val: float) -> float:
    """표준편차 계산 (표본)"""
    n = len(values)
    if n < 2:
        return 0.0
    variance = sum((x - mean_val) ** 2 for x in values) / (n - 1)
    return math.sqrt(variance)


def _compute_confidence_interval(
    mean_diff: float,
    std_treat: float,
    std_control: float,
    n_treat: int,
    n_control: int,
) -> Tuple[float, float]:
    """두 그룹 평균 차이의 신뢰구간을 계산합니다."""
    if n_treat < 1 or n_control < 1:
        return (mean_diff, mean_diff)

    se = math.sqrt(
        (std_treat ** 2 / max(n_treat, 1))
        + (std_control ** 2 / max(n_control, 1))
    )
    margin = _Z_95 * se
    return (round(mean_diff - margin, 6), round(mean_diff + margin, 6))


def measure_holdout(experiment: dict) -> HoldoutResult:
    """실험 데이터로 홀드아웃 측정을 수행합니다.

    Args:
        experiment: 실험 데이터 딕셔너리.
            - experiment_id (str): 실험 식별자
            - treatment (list[float]): 처리군 측정값
            - control (list[float]): 대조군 측정값

    Returns:
        HoldoutResult: 처리 효과, 신뢰구간, 유의성 판별 결과.
    """
    exp_id = experiment.get("experiment_id", "unknown")
    treatment = experiment.get("treatment", [])
    control = experiment.get("control", [])

    if not treatment and not control:
        logger.warning("실험 '%s': 처리군과 대조군 모두 비어있습니다.", exp_id)
        return HoldoutResult(
            experiment_id=exp_id,
            treatment_effect=0.0,
            confidence_interval=(0.0, 0.0),
            significant=False,
            sample_sizes={"treatment": 0, "control": 0},
        )

    treatment_vals = [float(v) for v in treatment]
    control_vals = [float(v) for v in control]

    mean_treat = _mean(treatment_vals)
    mean_control = _mean(control_vals)
    treatment_effect = round(mean_treat - mean_control, 6)

    std_treat = _std(treatment_vals, mean_treat)
    std_control = _std(control_vals, mean_control)

    ci = _compute_confidence_interval(
        treatment_effect,
        std_treat,
        std_control,
        len(treatment_vals),
        len(control_vals),
    )

    # 신뢰구간이 0을 포함하지 않으면 유의함
    significant = (ci[0] > 0 and ci[1] > 0) or (ci[0] < 0 and ci[1] < 0)

    sample_sizes = {
        "treatment": len(treatment_vals),
        "control": len(control_vals),
    }

    logger.info(
        "홀드아웃 측정 완료: experiment=%s, effect=%.4f, significant=%s",
        exp_id, treatment_effect, significant,
    )

    return HoldoutResult(
        experiment_id=exp_id,
        treatment_effect=treatment_effect,
        confidence_interval=ci,
        significant=significant,
        sample_sizes=sample_sizes,
    )
