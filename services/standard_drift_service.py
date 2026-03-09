"""
표준 드리프트 감지 서비스

현재 메트릭과 기준(baseline) 메트릭을 비교하여
드리프트(편차)를 감지하고 경고 수준을 산출합니다.
규칙 기반 (AI API 호출 없음).
"""
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class DriftedMetric:
    """드리프트가 감지된 개별 메트릭"""
    metric_name: str
    baseline_value: float
    current_value: float
    drift_pct: float
    direction: str  # "up", "down", "stable"


@dataclass
class DriftReport:
    """드리프트 감지 보고서"""
    drifted_metrics: List[DriftedMetric] = field(default_factory=list)
    overall_drift_score: float = 0.0
    alert_level: str = "normal"  # "normal", "warning", "critical"


# ── 임계값 설정 ──
_DRIFT_THRESHOLD_WARNING = 10.0   # 10% 이상 변화 시 warning
_DRIFT_THRESHOLD_CRITICAL = 25.0  # 25% 이상 변화 시 critical
_OVERALL_WARNING = 15.0           # 전체 드리프트 점수 warning 기준
_OVERALL_CRITICAL = 30.0          # 전체 드리프트 점수 critical 기준


def _calculate_drift_pct(baseline: float, current: float) -> float:
    """두 값 사이의 변화율(%)을 계산합니다."""
    if baseline == 0:
        if current == 0:
            return 0.0
        return 100.0  # 0에서 비영값으로 변화 → 100%
    return round(((current - baseline) / abs(baseline)) * 100, 2)


def _determine_direction(drift_pct: float) -> str:
    """변화 방향을 결정합니다."""
    if drift_pct > 1.0:
        return "up"
    if drift_pct < -1.0:
        return "down"
    return "stable"


def _determine_alert_level(overall_score: float) -> str:
    """전체 드리프트 점수에 따른 경고 수준을 결정합니다."""
    if overall_score >= _OVERALL_CRITICAL:
        return "critical"
    if overall_score >= _OVERALL_WARNING:
        return "warning"
    return "normal"


def detect_drift(current_metrics: dict, baseline: dict) -> DriftReport:
    """현재 메트릭과 기준 메트릭을 비교하여 드리프트를 감지합니다.

    Args:
        current_metrics: 현재 메트릭 dict ({"metric_name": float_value, ...})
        baseline: 기준 메트릭 dict (동일 형식)

    Returns:
        DriftReport 드리프트 감지 결과
    """
    if not current_metrics or not baseline:
        return DriftReport(
            drifted_metrics=[],
            overall_drift_score=0.0,
            alert_level="normal",
        )

    drifted: List[DriftedMetric] = []
    all_drifts: List[float] = []

    # 공통 메트릭에 대해 드리프트 계산
    common_keys = set(current_metrics.keys()) & set(baseline.keys())

    for key in sorted(common_keys):
        try:
            baseline_val = float(baseline[key])
            current_val = float(current_metrics[key])
        except (ValueError, TypeError):
            continue

        drift_pct = _calculate_drift_pct(baseline_val, current_val)
        abs_drift = abs(drift_pct)
        all_drifts.append(abs_drift)
        direction = _determine_direction(drift_pct)

        # 의미 있는 드리프트만 보고 (1% 이상 변화)
        if abs_drift > 1.0:
            drifted.append(DriftedMetric(
                metric_name=key,
                baseline_value=baseline_val,
                current_value=current_val,
                drift_pct=drift_pct,
                direction=direction,
            ))

    # 전체 드리프트 점수 (모든 메트릭 변화율의 RMS)
    if all_drifts:
        rms = (sum(d ** 2 for d in all_drifts) / len(all_drifts)) ** 0.5
        overall_score = round(rms, 2)
    else:
        overall_score = 0.0

    alert_level = _determine_alert_level(overall_score)

    # 드리프트 크기 내림차순 정렬
    drifted.sort(key=lambda m: abs(m.drift_pct), reverse=True)

    return DriftReport(
        drifted_metrics=drifted,
        overall_drift_score=overall_score,
        alert_level=alert_level,
    )
