"""
비디오 인터랙티브 타임라인 서비스
자막과 챕터 정보로 인터랙티브 타임라인 마커를 생성한다.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# 마커 타입 상수
VALID_MARKER_TYPES = {"chapter", "highlight", "question", "reference"}

# 질문 패턴 (한국어 + 영어)
QUESTION_PATTERNS = [
    re.compile(r'[?？]'),           # 물음표
    re.compile(r'어떻게|왜|무엇|뭐|어디|언제|누가', re.IGNORECASE),
    re.compile(r'\bhow\b|\bwhy\b|\bwhat\b|\bwhere\b|\bwhen\b|\bwho\b', re.IGNORECASE),
]

# 하이라이트 키워드
HIGHLIGHT_KEYWORDS = [
    "중요", "핵심", "결론", "요약", "정리", "포인트",
    "important", "key", "conclusion", "summary", "point",
]

# 참조 키워드
REFERENCE_KEYWORDS = [
    "참고", "출처", "연구", "논문", "데이터", "통계",
    "reference", "source", "study", "paper", "data", "statistic",
]


@dataclass
class TimelineMarker:
    """타임라인 마커"""
    timestamp: str
    label: str
    marker_type: str
    description: str


@dataclass
class InteractiveTimeline:
    """인터랙티브 타임라인"""
    video_id: str
    markers: List[TimelineMarker]
    total_duration: str
    chapter_count: int


def _validate_timestamp(ts: str) -> bool:
    """MM:SS 또는 HH:MM:SS 형식 검증"""
    return bool(re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', ts))


def _timestamp_to_seconds(ts: str) -> int:
    """타임스탬프를 초로 변환"""
    parts = ts.split(':')
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return 0


def _seconds_to_timestamp(seconds: int) -> str:
    """초를 MM:SS 또는 HH:MM:SS로 변환"""
    if seconds >= 3600:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}:{s:02d}"


def _detect_marker_type(text: str) -> str:
    """텍스트에서 마커 타입을 추론"""
    text_lower = text.lower()

    # 질문 패턴 검사
    for pattern in QUESTION_PATTERNS:
        if pattern.search(text):
            return "question"

    # 참조 키워드 검사
    for kw in REFERENCE_KEYWORDS:
        if kw in text_lower:
            return "reference"

    # 하이라이트 키워드 검사
    for kw in HIGHLIGHT_KEYWORDS:
        if kw in text_lower:
            return "highlight"

    return "chapter"


def _truncate(text: str, max_len: int = 80) -> str:
    """텍스트를 최대 길이로 자름"""
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def _markers_from_chapters(chapters: List[Dict]) -> List[TimelineMarker]:
    """챕터 목록에서 마커 생성"""
    markers = []
    for ch in chapters:
        ts = ch.get("timestamp", ch.get("start", ""))
        title = ch.get("title", ch.get("label", ""))
        if not ts or not _validate_timestamp(str(ts)):
            continue
        ts = str(ts)
        label = _truncate(title) if title else f"챕터 @ {ts}"
        description = ch.get("description", title or "")
        markers.append(TimelineMarker(
            timestamp=ts,
            label=label,
            marker_type="chapter",
            description=_truncate(description, 200),
        ))
    return markers


def _markers_from_transcript(transcript: str) -> List[TimelineMarker]:
    """자막 텍스트에서 타임스탬프 마커 추출"""
    markers = []
    # [MM:SS] 또는 [HH:MM:SS] 패턴으로 구분된 자막
    pattern = re.compile(r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*(.+?)(?=\[|$)', re.DOTALL)
    for match in pattern.finditer(transcript):
        ts = match.group(1)
        text = match.group(2).strip()
        if not text:
            continue
        marker_type = _detect_marker_type(text)
        markers.append(TimelineMarker(
            timestamp=ts,
            label=_truncate(text, 60),
            marker_type=marker_type,
            description=_truncate(text, 200),
        ))
    return markers


def _estimate_duration(markers: List[TimelineMarker]) -> str:
    """마커 목록에서 총 재생 시간 추정"""
    if not markers:
        return "00:00"
    max_seconds = 0
    for m in markers:
        s = _timestamp_to_seconds(m.timestamp)
        if s > max_seconds:
            max_seconds = s
    return _seconds_to_timestamp(max_seconds)


def build_interactive_timeline(
    video_id: str,
    transcript: str = '',
    chapters: Optional[List[Dict]] = None,
) -> InteractiveTimeline:
    """자막과 챕터로 인터랙티브 타임라인을 생성한다.

    Args:
        video_id: YouTube 영상 ID
        transcript: 자막 텍스트 ([MM:SS] 형식 포함 가능)
        chapters: 챕터 목록 [{"timestamp": "...", "title": "..."}]

    Returns:
        InteractiveTimeline
    """
    if not video_id or not video_id.strip():
        logger.warning("video_id가 비어 있습니다")
        return InteractiveTimeline(
            video_id="", markers=[], total_duration="00:00", chapter_count=0,
        )

    video_id = video_id.strip()
    markers: List[TimelineMarker] = []

    # 챕터에서 마커 생성
    if chapters:
        markers.extend(_markers_from_chapters(chapters))

    # 자막에서 마커 추출
    if transcript and transcript.strip():
        transcript_markers = _markers_from_transcript(transcript)
        # 챕터 마커와 중복 타임스탬프 제거
        existing_ts = {m.timestamp for m in markers}
        for tm in transcript_markers:
            if tm.timestamp not in existing_ts:
                markers.append(tm)
                existing_ts.add(tm.timestamp)

    # 타임스탬프순 정렬
    markers.sort(key=lambda m: _timestamp_to_seconds(m.timestamp))

    chapter_count = sum(1 for m in markers if m.marker_type == "chapter")
    total_duration = _estimate_duration(markers)

    logger.info(
        "video_id=%s: 타임라인 생성 완료 (마커 %d개, 챕터 %d개)",
        video_id, len(markers), chapter_count,
    )

    return InteractiveTimeline(
        video_id=video_id,
        markers=markers,
        total_duration=total_duration,
        chapter_count=chapter_count,
    )
