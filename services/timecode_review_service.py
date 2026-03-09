"""타임코드 리뷰 서비스 — 타임코드 주석 관리 (인메모리)"""
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

# 인메모리 저장소
_annotation_store: dict = {}

# 타임코드 형식: MM:SS 또는 HH:MM:SS
_TIMECODE_PATTERN = re.compile(
    r'^(?:(\d{1,2}):)?(\d{1,2}):(\d{2})$'
)


@dataclass
class Annotation:
    """타임코드 주석"""
    annotation_id: str = ""
    transcript_id: str = ""
    timecode: str = ""
    timecode_seconds: int = 0
    note: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def validate_timecode(timecode: str) -> bool:
    """타임코드 형식 검증

    Args:
        timecode: "MM:SS" 또는 "HH:MM:SS" 형식 문자열

    Returns:
        유효하면 True
    """
    if not timecode or not isinstance(timecode, str):
        return False
    return _TIMECODE_PATTERN.match(timecode.strip()) is not None


def _parse_timecode_to_seconds(timecode: str) -> int:
    """타임코드를 초 단위로 변환

    Args:
        timecode: "MM:SS" 또는 "HH:MM:SS" 형식

    Returns:
        초 단위 정수

    Raises:
        ValueError: 잘못된 형식
    """
    timecode = timecode.strip()
    match = _TIMECODE_PATTERN.match(timecode)
    if not match:
        raise ValueError(f"잘못된 타임코드 형식: '{timecode}' (MM:SS 또는 HH:MM:SS 필요)")

    hours_str, minutes_str, seconds_str = match.groups()
    hours = int(hours_str) if hours_str else 0
    minutes = int(minutes_str)
    seconds = int(seconds_str)

    # 초/분 범위 검증
    if seconds >= 60:
        raise ValueError(f"초는 0~59 범위여야 합니다: {seconds}")
    if minutes >= 60 and hours_str is not None:
        raise ValueError(f"분은 0~59 범위여야 합니다: {minutes}")

    return hours * 3600 + minutes * 60 + seconds


def add_timecode_annotation(transcript_id: str, timecode: str, note: str) -> Annotation:
    """타임코드 주석 추가

    Args:
        transcript_id: 자막 식별자
        timecode: "MM:SS" 또는 "HH:MM:SS" 형식
        note: 주석 내용

    Returns:
        생성된 Annotation

    Raises:
        ValueError: 잘못된 타임코드 형식 또는 빈 입력
    """
    if not transcript_id or not transcript_id.strip():
        raise ValueError("transcript_id는 비어있을 수 없습니다")
    if not note or not note.strip():
        raise ValueError("note는 비어있을 수 없습니다")

    timecode = timecode.strip()
    timecode_seconds = _parse_timecode_to_seconds(timecode)

    annotation = Annotation(
        annotation_id=str(uuid.uuid4()),
        transcript_id=transcript_id.strip(),
        timecode=timecode,
        timecode_seconds=timecode_seconds,
        note=note.strip(),
    )

    # 저장소에 추가
    if transcript_id not in _annotation_store:
        _annotation_store[transcript_id] = []
    _annotation_store[transcript_id].append(annotation)

    return annotation


def list_annotations(transcript_id: str) -> list:
    """해당 자막의 주석 목록 반환 (타임코드 순 정렬)

    Args:
        transcript_id: 자막 식별자

    Returns:
        Annotation 리스트 (타임코드 순)
    """
    annotations = _annotation_store.get(transcript_id, [])
    return sorted(annotations, key=lambda a: a.timecode_seconds)


def clear_annotations(transcript_id: str = None) -> int:
    """주석 삭제 (테스트/관리용)

    Args:
        transcript_id: 지정 시 해당 자막만, 미지정 시 전체 삭제

    Returns:
        삭제된 주석 수
    """
    if transcript_id:
        removed = len(_annotation_store.pop(transcript_id, []))
        return removed
    else:
        total = sum(len(v) for v in _annotation_store.values())
        _annotation_store.clear()
        return total
