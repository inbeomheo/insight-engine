"""
오토스케일러 서비스.

부하에 따른 리소스 스케일링 시뮬레이션.
CPU/메모리/요청률/지연 시간 지표를 분석하여
인스턴스 증감 결정을 내린다.
"""

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class ResourceMetrics:
    """리소스 지표."""
    cpu_usage: float       # 0.0 ~ 100.0 (%)
    memory_usage: float    # 0.0 ~ 100.0 (%)
    request_rate: float    # 초당 요청 수
    avg_latency: float     # 밀리초
    timestamp: str = ""


@dataclass
class ScaleDecision:
    """스케일링 결정."""
    action: str  # scale_up / scale_down / maintain
    current_instances: int
    target_instances: int
    reason: str


# 부하 수준 임계값
_THRESHOLDS = {
    "cpu_high": 80.0,
    "cpu_low": 20.0,
    "memory_high": 85.0,
    "memory_low": 25.0,
    "latency_high": 1000.0,  # 1초
    "request_rate_high": 100.0,
}


def evaluate_load(metrics: ResourceMetrics) -> str:
    """
    부하 수준 판단.

    Returns:
        "low" / "normal" / "high" / "critical"
    """
    # critical: CPU 90% 이상 또는 메모리 95% 이상
    if metrics.cpu_usage >= 90.0 or metrics.memory_usage >= 95.0:
        return "critical"

    # high: CPU 또는 메모리 임계값 초과, 또는 지연 시간 높음
    if (metrics.cpu_usage >= _THRESHOLDS["cpu_high"]
            or metrics.memory_usage >= _THRESHOLDS["memory_high"]
            or metrics.avg_latency >= _THRESHOLDS["latency_high"]):
        return "high"

    # low: CPU와 메모리 모두 낮음
    if (metrics.cpu_usage <= _THRESHOLDS["cpu_low"]
            and metrics.memory_usage <= _THRESHOLDS["memory_low"]):
        return "low"

    return "normal"


def decide_scaling(
    metrics: ResourceMetrics,
    current_instances: int,
    min_inst: int,
    max_inst: int,
) -> ScaleDecision:
    """
    스케일링 결정.

    부하 수준에 따라 인스턴스 증감을 결정한다.
    """
    load = evaluate_load(metrics)

    if load == "critical":
        # 즉시 2배 증가 (max 제한)
        target = min(current_instances * 2, max_inst)
        return ScaleDecision(
            action="scale_up" if target > current_instances else "maintain",
            current_instances=current_instances,
            target_instances=target,
            reason=f"부하 위험: CPU {metrics.cpu_usage}%, 메모리 {metrics.memory_usage}%",
        )

    if load == "high":
        # 1개 추가
        target = min(current_instances + 1, max_inst)
        return ScaleDecision(
            action="scale_up" if target > current_instances else "maintain",
            current_instances=current_instances,
            target_instances=target,
            reason=f"부하 높음: CPU {metrics.cpu_usage}%, 지연 {metrics.avg_latency}ms",
        )

    if load == "low":
        # 1개 감소
        target = max(current_instances - 1, min_inst)
        return ScaleDecision(
            action="scale_down" if target < current_instances else "maintain",
            current_instances=current_instances,
            target_instances=target,
            reason=f"부하 낮음: CPU {metrics.cpu_usage}%, 메모리 {metrics.memory_usage}%",
        )

    # normal → 유지
    return ScaleDecision(
        action="maintain",
        current_instances=current_instances,
        target_instances=current_instances,
        reason="부하 정상 범위",
    )


def calculate_cooldown(last_scale_time: str, cooldown_seconds: int) -> bool:
    """
    쿨다운 체크.

    마지막 스케일링 이후 cooldown_seconds가 경과했는지 확인.

    Returns:
        True면 쿨다운 중 (스케일링 불가), False면 스케일링 가능.
    """
    if not last_scale_time:
        return False  # 스케일링 이력 없음 → 즉시 가능

    try:
        last_time = datetime.fromisoformat(last_scale_time)
        # timezone-aware로 통일
        if last_time.tzinfo is None:
            last_time = last_time.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        elapsed = (now - last_time).total_seconds()
        return elapsed < cooldown_seconds
    except (ValueError, TypeError):
        return False


def predict_load(metrics_history: list[ResourceMetrics]) -> str:
    """
    부하 추세 예측.

    최근 지표의 CPU 사용률 추이를 분석.

    Returns:
        "increasing" / "stable" / "decreasing"
    """
    if len(metrics_history) < 2:
        return "stable"

    # 전반부 vs 후반부 CPU 평균 비교
    mid = len(metrics_history) // 2
    first_half = metrics_history[:mid]
    second_half = metrics_history[mid:]

    avg_first = sum(m.cpu_usage for m in first_half) / len(first_half)
    avg_second = sum(m.cpu_usage for m in second_half) / len(second_half)

    diff = avg_second - avg_first

    if diff > 10.0:
        return "increasing"
    elif diff < -10.0:
        return "decreasing"
    else:
        return "stable"
