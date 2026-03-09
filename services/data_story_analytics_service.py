"""
데이터 스토리 분석 서비스

메트릭 시계열 데이터를 분석하여 내러티브, 핵심 인사이트,
추세 방향, 이상치를 도출합니다.
"""
import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class DataStoryAnalytics:
    """데이터 스토리 분석 결과"""
    narrative: str
    key_insights: List[str] = field(default_factory=list)
    trend_direction: str = ""  # "increasing", "decreasing", "stable", "volatile"
    anomalies: List[Dict] = field(default_factory=list)


def _compute_stats(values: List[float]) -> Dict[str, float]:
    """기본 통계값을 계산합니다."""
    n = len(values)
    if n == 0:
        return {"mean": 0, "std": 0, "min": 0, "max": 0}

    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / max(n - 1, 1)
    std = math.sqrt(variance)

    return {
        "mean": round(mean, 2),
        "std": round(std, 2),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
    }


def _detect_trend(values: List[float]) -> str:
    """값 시리즈의 전반적 추세를 판별합니다."""
    if len(values) < 2:
        return "stable"

    # 단순 선형 회귀 기울기
    n = len(values)
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n

    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return "stable"

    slope = numerator / denominator

    # 기울기 기반 판별 (평균 대비 상대적 크기)
    stats = _compute_stats(values)
    relative_slope = slope / abs(stats["mean"]) if stats["mean"] != 0 else slope

    if abs(relative_slope) > 0.05:
        # 뚜렷한 추세가 있으면 추세 우선
        if relative_slope > 0.05:
            return "increasing"
        else:
            return "decreasing"

    # 추세 없이 변동성만 높은 경우
    cv = stats["std"] / abs(stats["mean"]) if stats["mean"] != 0 else 0
    if cv > 0.5:
        return "volatile"

    return "stable"


def _find_anomalies(
    metrics: List[dict],
    values: List[float],
    stats: Dict[str, float],
) -> List[Dict]:
    """Z-score 기반 이상치를 탐지합니다."""
    anomalies: List[Dict] = []
    if stats["std"] == 0:
        return anomalies

    for i, (metric, val) in enumerate(zip(metrics, values)):
        z_score = abs(val - stats["mean"]) / stats["std"]
        if z_score > 2.0:
            anomalies.append({
                "index": i,
                "label": metric.get("label", f"point_{i}"),
                "value": round(val, 2),
                "z_score": round(z_score, 2),
                "direction": "high" if val > stats["mean"] else "low",
            })

    return anomalies


def _build_narrative(
    stats: Dict[str, float],
    trend: str,
    anomaly_count: int,
    data_count: int,
) -> str:
    """분석 결과를 자연어 내러티브로 변환합니다."""
    trend_desc = {
        "increasing": "상승 추세",
        "decreasing": "하락 추세",
        "stable": "안정적",
        "volatile": "변동이 큰",
    }

    narrative = (
        f"총 {data_count}개 데이터 포인트 분석 결과, "
        f"평균 {stats['mean']}, 범위 {stats['min']}~{stats['max']}으로 "
        f"{trend_desc.get(trend, '판별 불가')} 패턴을 보입니다."
    )

    if anomaly_count > 0:
        narrative += f" {anomaly_count}개의 이상치가 감지되었습니다."

    return narrative


def _extract_insights(
    stats: Dict[str, float],
    trend: str,
    anomalies: List[Dict],
) -> List[str]:
    """핵심 인사이트를 추출합니다."""
    insights: List[str] = []

    # 추세 인사이트
    if trend == "increasing":
        insights.append("지표가 지속적으로 상승하고 있습니다.")
    elif trend == "decreasing":
        insights.append("지표가 하락세를 보이고 있어 원인 분석이 필요합니다.")
    elif trend == "volatile":
        insights.append("지표 변동성이 높아 안정화 전략이 필요합니다.")

    # 범위 인사이트
    range_val = stats["max"] - stats["min"]
    if stats["mean"] != 0 and range_val / abs(stats["mean"]) > 1.0:
        insights.append(f"최대-최소 차이({range_val})가 평균 대비 크므로 주의가 필요합니다.")

    # 이상치 인사이트
    high_anomalies = [a for a in anomalies if a["direction"] == "high"]
    low_anomalies = [a for a in anomalies if a["direction"] == "low"]
    if high_anomalies:
        insights.append(f"상위 이상치 {len(high_anomalies)}건이 발견되었습니다.")
    if low_anomalies:
        insights.append(f"하위 이상치 {len(low_anomalies)}건이 발견되었습니다.")

    return insights


def analyze_data_story(metrics: List[dict]) -> DataStoryAnalytics:
    """메트릭 데이터를 분석하여 데이터 스토리를 생성합니다.

    Args:
        metrics: 메트릭 데이터 리스트.
            각 항목은 {"label": str, "value": float} 형태.

    Returns:
        DataStoryAnalytics: 내러티브, 인사이트, 추세, 이상치 정보.
    """
    if not metrics:
        logger.warning("빈 메트릭 데이터가 전달되었습니다.")
        return DataStoryAnalytics(
            narrative="분석할 데이터가 없습니다.",
            trend_direction="stable",
        )

    values = [float(m.get("value", 0)) for m in metrics]
    stats = _compute_stats(values)
    trend = _detect_trend(values)
    anomalies = _find_anomalies(metrics, values, stats)
    insights = _extract_insights(stats, trend, anomalies)
    narrative = _build_narrative(stats, trend, len(anomalies), len(metrics))

    logger.info(
        "데이터 스토리 분석 완료: %d개 포인트, 추세=%s, 이상치 %d개",
        len(metrics), trend, len(anomalies),
    )

    return DataStoryAnalytics(
        narrative=narrative,
        key_insights=insights,
        trend_direction=trend,
        anomalies=anomalies,
    )
