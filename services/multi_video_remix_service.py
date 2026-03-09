"""
멀티 비디오 리믹스 서비스

여러 영상 소스에서 클립을 추출하고 테마에 맞게 리믹스 계획을 생성합니다.
외부 API 없이 규칙 기반으로 동작합니다.
"""
import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict

logger = logging.getLogger(__name__)


@dataclass
class RemixClip:
    """리믹스에 포함될 클립"""
    source_id: str
    start: str   # "MM:SS" 형식
    end: str     # "MM:SS" 형식
    order: int


@dataclass
class RemixPlan:
    """멀티 비디오 리믹스 계획"""
    theme: str
    clips: List[RemixClip] = field(default_factory=list)
    total_duration: float = 0.0  # 초 단위
    transitions: List[str] = field(default_factory=list)


# 전환 효과 프리셋
_TRANSITION_EFFECTS = [
    'crossfade',
    'cut',
    'fade-to-black',
    'wipe-left',
    'zoom-in',
    'dissolve',
]


def _parse_timestamp(ts: str) -> float:
    """MM:SS 또는 HH:MM:SS 형식을 초 단위로 변환합니다."""
    parts = ts.strip().split(':')
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0.0


def _format_timestamp(seconds: float) -> str:
    """초를 MM:SS 형식으로 변환합니다."""
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f'{m}:{s:02d}'


def _validate_source(source: dict) -> bool:
    """비디오 소스의 유효성을 검증합니다."""
    if not isinstance(source, dict):
        return False
    if 'source_id' not in source:
        return False
    if 'start' not in source or 'end' not in source:
        return False
    # 시작이 끝보다 뒤면 무효
    start_s = _parse_timestamp(str(source['start']))
    end_s = _parse_timestamp(str(source['end']))
    if start_s >= end_s:
        return False
    return True


def _calculate_clip_duration(start: str, end: str) -> float:
    """클립의 길이(초)를 계산합니다."""
    return _parse_timestamp(end) - _parse_timestamp(start)


def _assign_transitions(clip_count: int) -> List[str]:
    """클립 사이에 전환 효과를 배정합니다."""
    if clip_count <= 1:
        return []
    transitions = []
    for i in range(clip_count - 1):
        effect = _TRANSITION_EFFECTS[i % len(_TRANSITION_EFFECTS)]
        transitions.append(effect)
    return transitions


def remix_videos(
    video_sources: List[Dict],
    theme: str = '',
) -> RemixPlan:
    """
    여러 비디오 소스로 리믹스 계획을 생성합니다.

    Args:
        video_sources: 비디오 소스 리스트
            각 항목: {"source_id": str, "start": "MM:SS", "end": "MM:SS"}
        theme: 리믹스 테마 (선택)

    Returns:
        RemixPlan 결과

    Raises:
        ValueError: 유효하지 않은 소스가 포함된 경우
    """
    if not video_sources:
        return RemixPlan(
            theme=theme or '(테마 미지정)',
            clips=[],
            total_duration=0.0,
            transitions=[],
        )

    # 유효성 검증
    invalid = []
    for i, src in enumerate(video_sources):
        if not _validate_source(src):
            invalid.append(i)
    if invalid:
        raise ValueError(
            f'유효하지 않은 소스 인덱스: {invalid}. '
            f'필수 필드: source_id, start(MM:SS), end(MM:SS), start < end'
        )

    effective_theme = theme.strip() if theme else '(테마 미지정)'

    # 클립 생성 — 입력 순서 기반
    clips = []
    total_duration = 0.0
    for i, src in enumerate(video_sources):
        start_str = str(src['start']).strip()
        end_str = str(src['end']).strip()
        clip_dur = _calculate_clip_duration(start_str, end_str)
        total_duration += clip_dur

        clips.append(RemixClip(
            source_id=str(src['source_id']),
            start=start_str,
            end=end_str,
            order=i,
        ))

    # 전환 효과 배정
    transitions = _assign_transitions(len(clips))

    return RemixPlan(
        theme=effective_theme,
        clips=clips,
        total_duration=round(total_duration, 2),
        transitions=transitions,
    )
