"""
업스트림 경보 서비스 — 상위 소스/의존성 변경 감지
"""

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass
class UpstreamSource:
    """업스트림 소스"""
    source_id: str
    name: str
    url: str
    last_checked: str
    hash: str


@dataclass
class AlertEvent:
    """경보 이벤트"""
    event_id: str
    source_id: str
    change_type: str  # content_changed / unavailable / schema_changed
    severity: str     # info / warning / critical
    detected_at: str


def check_source(source: UpstreamSource, new_hash: str) -> 'AlertEvent | None':
    """소스 변경 감지 — 해시 비교"""
    if new_hash == '':
        # 빈 해시 = 접근 불가
        return AlertEvent(
            event_id=str(uuid.uuid4())[:8],
            source_id=source.source_id,
            change_type='unavailable',
            severity=classify_severity('unavailable'),
            detected_at=datetime.now().isoformat()
        )

    if new_hash != source.hash:
        return AlertEvent(
            event_id=str(uuid.uuid4())[:8],
            source_id=source.source_id,
            change_type='content_changed',
            severity=classify_severity('content_changed'),
            detected_at=datetime.now().isoformat()
        )

    return None


def batch_check(sources: list[UpstreamSource], new_hashes: dict[str, str]) -> list[AlertEvent]:
    """일괄 변경 감지"""
    events = []
    for source in sources:
        new_hash = new_hashes.get(source.source_id, source.hash)
        event = check_source(source, new_hash)
        if event is not None:
            events.append(event)
    return events


def classify_severity(change_type: str) -> str:
    """변경 유형 기반 심각도 분류"""
    severity_map = {
        'content_changed': 'info',
        'unavailable': 'critical',
        'schema_changed': 'warning'
    }
    return severity_map.get(change_type, 'info')


def get_critical_alerts(events: list[AlertEvent]) -> list[AlertEvent]:
    """심각 경보만 필터링"""
    return [e for e in events if e.severity == 'critical']
