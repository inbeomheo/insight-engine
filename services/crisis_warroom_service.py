"""
위기 워룸 서비스.

콘텐츠 위기 상황을 탐지/에스컬레이션/대응/해결 처리한다.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class CrisisEvent:
    """위기 이벤트."""
    event_id: str
    title: str
    severity: str  # low / medium / high / critical
    status: str  # detected / assessing / responding / resolved
    affected_content: list  # list[str] — 영향받는 콘텐츠 ID
    timeline: list  # list[dict] — {timestamp, action, actor, detail}


@dataclass
class Warroom:
    """위기 워룸."""
    warroom_id: str
    events: list  # list[CrisisEvent]
    responders: list  # list[str]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# 심각도 자동 분류 키워드
_SEVERITY_KEYWORDS = {
    "critical": ["데이터 유출", "법적 소송", "서비스 중단", "보안 침해", "대규모"],
    "high": ["명예훼손", "저작권 위반", "개인정보", "고객 불만 폭주"],
    "medium": ["오류", "부정확", "지연", "품질 저하"],
}


def _classify_severity(issue: str) -> str:
    """이슈 설명으로 심각도를 자동 분류한다."""
    issue_lower = issue.lower()
    for severity, keywords in _SEVERITY_KEYWORDS.items():
        for kw in keywords:
            if kw in issue_lower:
                return severity
    return "low"


def detect_crisis(content_id: str, issue: str) -> CrisisEvent:
    """위기를 탐지하고 자동 심각도를 분류한다."""
    event_id = f"ce_{uuid.uuid4().hex[:8]}"
    severity = _classify_severity(issue)

    timeline_entry = {
        "timestamp": _now_iso(),
        "action": "detected",
        "actor": "system",
        "detail": issue,
    }

    return CrisisEvent(
        event_id=event_id,
        title=issue,
        severity=severity,
        status="detected",
        affected_content=[content_id],
        timeline=[timeline_entry],
    )


def escalate(event: CrisisEvent, new_severity: str) -> CrisisEvent:
    """위기 심각도를 에스컬레이션한다."""
    valid_severities = {"low", "medium", "high", "critical"}
    if new_severity not in valid_severities:
        raise ValueError(f"유효하지 않은 심각도: {new_severity}")

    new_timeline = list(event.timeline) + [{
        "timestamp": _now_iso(),
        "action": "escalated",
        "actor": "system",
        "detail": f"심각도 변경: {event.severity} → {new_severity}",
    }]

    return CrisisEvent(
        event_id=event.event_id,
        title=event.title,
        severity=new_severity,
        status="assessing",
        affected_content=list(event.affected_content),
        timeline=new_timeline,
    )


def add_response(event: CrisisEvent, responder: str, action: str) -> CrisisEvent:
    """대응 기록을 추가한다."""
    new_timeline = list(event.timeline) + [{
        "timestamp": _now_iso(),
        "action": "response",
        "actor": responder,
        "detail": action,
    }]

    return CrisisEvent(
        event_id=event.event_id,
        title=event.title,
        severity=event.severity,
        status="responding",
        affected_content=list(event.affected_content),
        timeline=new_timeline,
    )


def resolve_crisis(event: CrisisEvent, resolution: str) -> CrisisEvent:
    """위기를 해결 처리한다."""
    new_timeline = list(event.timeline) + [{
        "timestamp": _now_iso(),
        "action": "resolved",
        "actor": "system",
        "detail": resolution,
    }]

    return CrisisEvent(
        event_id=event.event_id,
        title=event.title,
        severity=event.severity,
        status="resolved",
        affected_content=list(event.affected_content),
        timeline=new_timeline,
    )


def get_active_crises(warroom: Warroom) -> list:
    """미해결 위기 목록을 반환한다."""
    return [e for e in warroom.events if e.status != "resolved"]
