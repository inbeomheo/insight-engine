"""인용 신선도 알림 서비스 -- 오래된 인용 감지 및 갱신 권고"""
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class DecayAlert:
    """인용 부패 알림"""
    citation_url: str = ""
    age_days: int = 0
    severity: str = "info"       # info / warning / critical
    recommendation: str = ""


def _calculate_age_days(date_str: str) -> int:
    """ISO 형식 날짜 문자열로부터 경과 일수를 계산한다."""
    try:
        # ISO 형식 파싱 (YYYY-MM-DD 또는 YYYY-MM-DDTHH:MM:SS)
        if "T" in date_str:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        else:
            dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return max(0, (now - dt).days)
    except (ValueError, TypeError):
        return -1


def _determine_severity(age_days: int, max_age_days: int) -> str:
    """경과 일수에 따라 심각도를 판단한다."""
    if age_days > max_age_days:
        return "critical"
    if age_days > max_age_days * 0.7:
        return "warning"
    return "info"


def _build_recommendation(severity: str, age_days: int, url: str) -> str:
    """심각도에 따른 권장 조치를 생성한다."""
    if severity == "critical":
        return f"인용이 {age_days}일 경과하여 만료 상태입니다. 최신 자료로 교체하거나 제거하세요."
    if severity == "warning":
        return f"인용이 {age_days}일 경과하여 갱신이 필요합니다. 원본 링크를 확인하세요."
    return f"인용이 {age_days}일 경과했습니다. 현재는 유효합니다."


def alert_citation_decay(
    citations: list[dict],
    max_age_days: int = 365,
) -> list[DecayAlert]:
    """인용 목록의 신선도를 분석하고 부패 알림을 생성한다.

    Args:
        citations: [{"url": "https://...", "date": "2024-01-15"}, ...]
        max_age_days: 최대 허용 경과일 (기본 365일)

    Returns:
        list[DecayAlert] — severity가 높은 순 정렬
    """
    if max_age_days <= 0:
        max_age_days = 365

    alerts: list[DecayAlert] = []

    for citation in citations:
        url = str(citation.get("url", ""))
        date_str = str(citation.get("date", ""))

        if not url:
            continue

        age_days = _calculate_age_days(date_str)

        if age_days < 0:
            # 날짜 파싱 실패 — 날짜 불명으로 경고
            alerts.append(DecayAlert(
                citation_url=url,
                age_days=0,
                severity="warning",
                recommendation="인용 날짜를 확인할 수 없습니다. 수동으로 검토하세요.",
            ))
            continue

        severity = _determine_severity(age_days, max_age_days)
        recommendation = _build_recommendation(severity, age_days, url)

        alerts.append(DecayAlert(
            citation_url=url,
            age_days=age_days,
            severity=severity,
            recommendation=recommendation,
        ))

    # critical > warning > info 순 정렬
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: (severity_order.get(a.severity, 3), -a.age_days))

    return alerts
