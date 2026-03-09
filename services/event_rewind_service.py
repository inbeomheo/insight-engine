"""
이벤트 리와인드 서비스 — 이벤트 타임라인 되감기/재생
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TimelineEvent:
    """타임라인 이벤트"""
    event_id: str
    timestamp: str
    event_type: str
    description: str
    data: dict


@dataclass
class Timeline:
    """타임라인"""
    timeline_id: str
    events: list[TimelineEvent] = field(default_factory=list)


def record_event(timeline: Timeline, event_type: str, description: str, data: dict) -> Timeline:
    """이벤트 기록"""
    event = TimelineEvent(
        event_id=str(uuid.uuid4())[:8],
        timestamp=datetime.now().isoformat(),
        event_type=event_type,
        description=description,
        data=data
    )
    new_events = timeline.events + [event]
    return Timeline(timeline_id=timeline.timeline_id, events=new_events)


def rewind_to(timeline: Timeline, timestamp: str) -> Timeline:
    """특정 시점까지 되감기 — timestamp 이전 이벤트만 보존"""
    rewound = [e for e in timeline.events if e.timestamp <= timestamp]
    return Timeline(timeline_id=timeline.timeline_id, events=rewound)


def replay_range(timeline: Timeline, start: str, end: str) -> list[TimelineEvent]:
    """범위 내 이벤트 재생"""
    return [e for e in timeline.events if start <= e.timestamp <= end]


def summarize_timeline(timeline: Timeline) -> dict:
    """타임라인 요약"""
    if not timeline.events:
        return {'total_events': 0, 'event_types': {}, 'first': None, 'last': None}

    type_counts: dict[str, int] = {}
    for e in timeline.events:
        type_counts[e.event_type] = type_counts.get(e.event_type, 0) + 1

    sorted_events = sorted(timeline.events, key=lambda e: e.timestamp)
    return {
        'total_events': len(timeline.events),
        'event_types': type_counts,
        'first': sorted_events[0].timestamp,
        'last': sorted_events[-1].timestamp
    }
