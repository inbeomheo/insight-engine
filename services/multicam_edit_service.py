"""
멀티캠 자동 편집 서비스

여러 카메라 스트림에서 화자 변경/장면 전환 시점을 감지해
자동으로 카메라 전환(컷) 결정을 생성하는 규칙 기반 서비스.
외부 API 호출 없음.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import uuid
import re


@dataclass
class StreamInfo:
    """개별 카메라 스트림 정보."""
    stream_id: str
    label: str
    priority: int  # 숫자가 낮을수록 높은 우선순위


@dataclass
class CutDecision:
    """카메라 전환 결정."""
    timestamp: str        # "MM:SS" 형식
    from_stream: str      # 전환 전 스트림 ID
    to_stream: str        # 전환 후 스트림 ID
    reason: str           # 전환 사유


@dataclass
class MulticamEdit:
    """멀티캠 편집 결과."""
    edit_id: str
    streams: List[StreamInfo]
    cuts: List[CutDecision]
    total_cuts: int


# ── 전환 사유 상수 ──
REASON_SPEAKER_CHANGE = "화자 변경"
REASON_SCENE_CHANGE = "장면 전환"
REASON_PRIORITY_SWITCH = "우선순위 기반 전환"
REASON_PERIODIC = "주기적 전환"

# ── 기본 설정 ──
_DEFAULT_CUT_INTERVAL = 30  # 초 — 이벤트 없을 때 주기적 전환 간격
_MIN_CUT_GAP = 5            # 초 — 연속 컷 최소 간격


def _parse_timestamp(ts: str) -> int:
    """'MM:SS' 또는 'HH:MM:SS' 형식을 초 단위로 변환."""
    parts = ts.strip().split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    raise ValueError(f"잘못된 타임스탬프 형식: {ts}")


def _format_timestamp(seconds: int) -> str:
    """초를 'MM:SS' 형식으로 변환."""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def _detect_speaker_changes(events: List[Dict]) -> List[Dict]:
    """이벤트 목록에서 화자 변경 시점 추출."""
    changes = []
    for event in events:
        if event.get("type") == "speaker_change":
            ts = event.get("timestamp", "00:00")
            speaker = event.get("speaker", "")
            changes.append({"seconds": _parse_timestamp(ts), "speaker": speaker, "timestamp": ts})
    return changes


def _detect_scene_changes(events: List[Dict]) -> List[Dict]:
    """이벤트 목록에서 장면 전환 시점 추출."""
    changes = []
    for event in events:
        if event.get("type") == "scene_change":
            ts = event.get("timestamp", "00:00")
            changes.append({"seconds": _parse_timestamp(ts), "timestamp": ts})
    return changes


def _build_stream_map(streams: List[StreamInfo]) -> Dict[str, StreamInfo]:
    """스트림 ID → StreamInfo 매핑."""
    return {s.stream_id: s for s in streams}


def _next_stream(current_id: str, streams: List[StreamInfo]) -> StreamInfo:
    """현재 스트림에서 다음 우선순위 스트림 반환. 라운드로빈."""
    sorted_streams = sorted(streams, key=lambda s: s.priority)
    current_idx = -1
    for i, s in enumerate(sorted_streams):
        if s.stream_id == current_id:
            current_idx = i
            break
    if current_idx == -1:
        return sorted_streams[0]
    next_idx = (current_idx + 1) % len(sorted_streams)
    return sorted_streams[next_idx]


def auto_multicam(video_streams: List[Dict]) -> MulticamEdit:
    """
    멀티캠 자동 편집 실행.

    Args:
        video_streams: 스트림 정보 목록. 각 dict에 필수 키:
            - stream_id (str)
            - label (str)
            - priority (int)
            - events (list[dict], 선택): type, timestamp, speaker 등

    Returns:
        MulticamEdit: 편집 결과 (스트림 목록, 컷 결정 목록)

    Raises:
        ValueError: 스트림이 2개 미만일 때
    """
    if not video_streams or len(video_streams) < 2:
        raise ValueError("멀티캠 편집에는 최소 2개의 스트림이 필요합니다")

    # 스트림 정보 구성
    streams: List[StreamInfo] = []
    all_events: List[Dict] = []

    for vs in video_streams:
        stream = StreamInfo(
            stream_id=vs.get("stream_id", str(uuid.uuid4())[:8]),
            label=vs.get("label", "Unknown"),
            priority=vs.get("priority", 99),
        )
        streams.append(stream)

        # 이벤트에 스트림 ID 태깅
        for event in vs.get("events", []):
            event_copy = dict(event)
            event_copy["_stream_id"] = stream.stream_id
            all_events.append(event_copy)

    # 우선순위 정렬
    streams.sort(key=lambda s: s.priority)

    # 이벤트 기반 컷 결정 생성
    cuts: List[CutDecision] = []
    current_stream = streams[0]
    last_cut_seconds = 0

    # 화자 변경 이벤트 처리
    speaker_changes = _detect_speaker_changes(all_events)
    scene_changes = _detect_scene_changes(all_events)

    # 모든 이벤트를 시간순 정렬
    timed_events = []
    for sc in speaker_changes:
        timed_events.append({"seconds": sc["seconds"], "type": "speaker", "data": sc})
    for sc in scene_changes:
        timed_events.append({"seconds": sc["seconds"], "type": "scene", "data": sc})
    timed_events.sort(key=lambda e: e["seconds"])

    for event in timed_events:
        seconds = event["seconds"]
        # 최소 간격 체크
        if seconds - last_cut_seconds < _MIN_CUT_GAP:
            continue

        next_s = _next_stream(current_stream.stream_id, streams)

        if event["type"] == "speaker":
            reason = REASON_SPEAKER_CHANGE
        else:
            reason = REASON_SCENE_CHANGE

        cuts.append(CutDecision(
            timestamp=_format_timestamp(seconds),
            from_stream=current_stream.stream_id,
            to_stream=next_s.stream_id,
            reason=reason,
        ))
        current_stream = next_s
        last_cut_seconds = seconds

    # 이벤트가 없으면 주기적 전환 추가
    if not timed_events:
        # 전체 길이 추정 (기본 300초 = 5분)
        total_duration = max(
            (vs.get("duration_seconds", 300) for vs in video_streams),
            default=300,
        )
        t = _DEFAULT_CUT_INTERVAL
        while t < total_duration:
            next_s = _next_stream(current_stream.stream_id, streams)
            cuts.append(CutDecision(
                timestamp=_format_timestamp(t),
                from_stream=current_stream.stream_id,
                to_stream=next_s.stream_id,
                reason=REASON_PERIODIC,
            ))
            current_stream = next_s
            t += _DEFAULT_CUT_INTERVAL

    return MulticamEdit(
        edit_id=str(uuid.uuid4())[:12],
        streams=streams,
        cuts=cuts,
        total_cuts=len(cuts),
    )
