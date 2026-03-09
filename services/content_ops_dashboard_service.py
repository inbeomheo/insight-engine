"""
콘텐츠 운영 관제 대시보드 서비스 — 토큰 비용, 지연시간, 실패율, 품질 점수 등 운영 지표 집계
"""

from dataclasses import dataclass, field


@dataclass
class OpsDashboard:
    """운영 관제 대시보드 데이터"""
    token_cost: float = 0.0
    avg_latency_ms: float = 0.0
    failure_rate: float = 0.0  # 0 ~ 1
    quality_score: float = 0.0  # 0 ~ 100
    active_pipelines: int = 0
    alerts: list[str] = field(default_factory=list)


# 경고 임계값
_THRESHOLDS = {
    "failure_rate_warning": 0.05,   # 5% 이상이면 경고
    "failure_rate_critical": 0.15,  # 15% 이상이면 위험
    "latency_warning_ms": 5000,     # 5초 이상이면 경고
    "latency_critical_ms": 15000,   # 15초 이상이면 위험
    "cost_daily_warning": 10.0,     # 일 $10 이상이면 경고
    "quality_low": 50.0,            # 50점 미만이면 경고
}


def _compute_token_cost(ops_data: dict) -> float:
    """토큰 비용 계산"""
    # 직접 비용이 있으면 사용
    if "total_cost" in ops_data:
        return round(float(ops_data["total_cost"]), 4)

    # 토큰 수 + 단가로 계산
    input_tokens = ops_data.get("input_tokens", 0)
    output_tokens = ops_data.get("output_tokens", 0)
    input_price = ops_data.get("input_price_per_1k", 0.0)
    output_price = ops_data.get("output_price_per_1k", 0.0)

    cost = (input_tokens / 1000 * input_price) + (output_tokens / 1000 * output_price)
    return round(cost, 4)


def _compute_avg_latency(ops_data: dict) -> float:
    """평균 지연 시간 계산 (ms)"""
    if "avg_latency_ms" in ops_data:
        return round(float(ops_data["avg_latency_ms"]), 1)

    latencies = ops_data.get("latencies_ms", [])
    if not latencies:
        return 0.0

    return round(sum(latencies) / len(latencies), 1)


def _compute_failure_rate(ops_data: dict) -> float:
    """실패율 계산 (0~1)"""
    if "failure_rate" in ops_data:
        return round(min(max(float(ops_data["failure_rate"]), 0.0), 1.0), 4)

    total = ops_data.get("total_requests", 0)
    failures = ops_data.get("failed_requests", 0)

    if total <= 0:
        return 0.0

    return round(min(failures / total, 1.0), 4)


def _compute_quality_score(ops_data: dict) -> float:
    """품질 점수 계산 (0~100)"""
    if "quality_score" in ops_data:
        return round(min(max(float(ops_data["quality_score"]), 0.0), 100.0), 1)

    # 개별 품질 점수 평균
    scores = ops_data.get("quality_scores", [])
    if not scores:
        return 0.0

    return round(sum(scores) / len(scores), 1)


def _generate_alerts(
    token_cost: float,
    avg_latency_ms: float,
    failure_rate: float,
    quality_score: float,
    active_pipelines: int,
) -> list[str]:
    """운영 지표 기반 알림 생성"""
    alerts = []

    # 실패율 경고
    if failure_rate >= _THRESHOLDS["failure_rate_critical"]:
        alerts.append(f"[위험] 실패율 {failure_rate:.1%} — 즉시 점검 필요")
    elif failure_rate >= _THRESHOLDS["failure_rate_warning"]:
        alerts.append(f"[경고] 실패율 {failure_rate:.1%} — 모니터링 강화")

    # 지연 시간 경고
    if avg_latency_ms >= _THRESHOLDS["latency_critical_ms"]:
        alerts.append(f"[위험] 평균 응답 {avg_latency_ms:.0f}ms — 성능 저하 심각")
    elif avg_latency_ms >= _THRESHOLDS["latency_warning_ms"]:
        alerts.append(f"[경고] 평균 응답 {avg_latency_ms:.0f}ms — 최적화 검토")

    # 비용 경고
    if token_cost >= _THRESHOLDS["cost_daily_warning"]:
        alerts.append(f"[경고] 토큰 비용 ${token_cost:.2f} — 예산 초과 우려")

    # 품질 경고
    if quality_score > 0 and quality_score < _THRESHOLDS["quality_low"]:
        alerts.append(f"[경고] 품질 점수 {quality_score:.1f}/100 — 프롬프트 개선 필요")

    # 파이프라인 경고
    if active_pipelines > 10:
        alerts.append(f"[주의] 활성 파이프라인 {active_pipelines}개 — 리소스 관리 확인")

    return alerts


def get_ops_dashboard(ops_data: dict) -> OpsDashboard:
    """
    운영 관제 대시보드 데이터 생성.

    Args:
        ops_data: {
            "total_cost": N | "input_tokens": N + "output_tokens": N + "input_price_per_1k": N + "output_price_per_1k": N,
            "avg_latency_ms": N | "latencies_ms": [N, ...],
            "failure_rate": N | "total_requests": N + "failed_requests": N,
            "quality_score": N | "quality_scores": [N, ...],
            "active_pipelines": N,
        }

    Returns:
        OpsDashboard: 관제 대시보드 데이터
    """
    if not ops_data:
        return OpsDashboard(alerts=["운영 데이터 없음"])

    token_cost = _compute_token_cost(ops_data)
    avg_latency = _compute_avg_latency(ops_data)
    failure_rate = _compute_failure_rate(ops_data)
    quality_score = _compute_quality_score(ops_data)
    active_pipelines = int(ops_data.get("active_pipelines", 0))

    alerts = _generate_alerts(
        token_cost, avg_latency, failure_rate, quality_score, active_pipelines
    )

    return OpsDashboard(
        token_cost=token_cost,
        avg_latency_ms=avg_latency,
        failure_rate=failure_rate,
        quality_score=quality_score,
        active_pipelines=active_pipelines,
        alerts=alerts,
    )
