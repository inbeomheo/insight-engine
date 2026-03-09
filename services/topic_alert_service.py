"""
토픽 알림 서비스 — 토픽 모니터링 알림 설정 및 트리거 체크
"""

from dataclasses import dataclass


@dataclass
class Alert:
    """토픽 알림 정의"""
    topic: str
    alert_type: str  # "spike" | "decline" | "new_entry"
    threshold: float
    current_value: float
    triggered: bool
    message: str


def set_topic_alert(
    topic: str,
    threshold: float = 0.5,
    alert_type: str = "spike",
) -> Alert:
    """
    토픽 알림 설정.

    Args:
        topic: 모니터링할 토픽 키워드
        threshold: 트리거 임계값 (0~1)
        alert_type: "spike" | "decline" | "new_entry"

    Returns:
        Alert: 초기 상태 (triggered=False)
    """
    valid_types = {"spike", "decline", "new_entry"}
    if alert_type not in valid_types:
        raise ValueError(f"지원하지 않는 alert_type: {alert_type}. 가능: {valid_types}")

    if not (0 <= threshold <= 1):
        raise ValueError(f"threshold는 0~1 범위여야 합니다: {threshold}")

    if not topic or not topic.strip():
        raise ValueError("topic은 빈 문자열일 수 없습니다")

    return Alert(
        topic=topic.strip(),
        alert_type=alert_type,
        threshold=threshold,
        current_value=0.0,
        triggered=False,
        message=f"알림 설정됨: '{topic}' ({alert_type}, 임계값={threshold})",
    )


def _check_single_alert(alert: Alert, topic_data: dict) -> Alert:
    """단일 알림의 트리거 여부 판별"""
    current = topic_data.get(alert.topic, 0.0)
    triggered = False
    message = alert.message

    if alert.alert_type == "spike":
        # 현재 값이 임계값 이상이면 급등 트리거
        if current >= alert.threshold:
            triggered = True
            message = f"급등 감지: '{alert.topic}' 값 {current:.2f} ≥ 임계값 {alert.threshold}"

    elif alert.alert_type == "decline":
        # 현재 값이 임계값 이하이면 하락 트리거
        if current <= alert.threshold:
            triggered = True
            message = f"하락 감지: '{alert.topic}' 값 {current:.2f} ≤ 임계값 {alert.threshold}"

    elif alert.alert_type == "new_entry":
        # 토픽이 데이터에 존재하면 신규 진입 트리거
        if alert.topic in topic_data and current > 0:
            triggered = True
            message = f"신규 진입: '{alert.topic}' 감지됨 (값: {current:.2f})"

    return Alert(
        topic=alert.topic,
        alert_type=alert.alert_type,
        threshold=alert.threshold,
        current_value=current,
        triggered=triggered,
        message=message,
    )


def check_alerts(alerts: list[Alert], current_data: dict) -> list[Alert]:
    """
    알림 트리거 체크.

    Args:
        alerts: 설정된 알림 목록
        current_data: {"토픽명": 현재값, ...} 형태의 최신 데이터

    Returns:
        list[Alert]: 트리거 여부가 업데이트된 알림 목록
    """
    if not alerts:
        return []

    return [_check_single_alert(alert, current_data) for alert in alerts]
