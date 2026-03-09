"""
사이니지 루프 생성 서비스

콘텐츠를 슬라이드로 분할하여 디지털 사이니지용 루프를 생성합니다.
외부 API 없이 텍스트 분할 규칙으로 동작합니다.
"""
import re
import hashlib
import logging
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)

# 슬라이드 전환 효과
_TRANSITIONS = ('fade', 'slide-left', 'slide-right', 'zoom', 'dissolve')

# 배경색 팔레트
_BACKGROUND_COLORS = (
    '#1A1A2E', '#16213E', '#0F3460', '#533483',
    '#2C3333', '#395B64', '#A5C9CA', '#E7F6F2',
)

# 슬라이드당 최대 글자 수
_MAX_CHARS_PER_SLIDE = 120

# 슬라이드당 최소 표시 시간 (초)
_MIN_SLIDE_DURATION = 3


@dataclass
class SignageSlide:
    """사이니지 슬라이드"""
    text: str
    duration_seconds: int
    transition: str
    background_color: str


@dataclass
class SignageLoop:
    """사이니지 루프"""
    loop_id: str
    slides: List[SignageSlide] = field(default_factory=list)
    total_duration: int = 0  # 초 단위
    loop_count: int = 1


def _generate_loop_id(content: str, duration: int) -> str:
    """콘텐츠와 시간 기반으로 고유 ID를 생성합니다."""
    raw = f'{content[:100]}_{duration}'
    return hashlib.md5(raw.encode('utf-8')).hexdigest()[:12]


def _split_into_slide_texts(content: str) -> List[str]:
    """콘텐츠를 슬라이드 텍스트로 분할합니다."""
    # 1차: 문단 분리
    paragraphs = re.split(r'\n\s*\n', content.strip())
    slides = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        # 마크다운 헤딩 제거
        para = re.sub(r'^#+\s*', '', para, flags=re.MULTILINE)
        para = para.strip()

        # 글자 수 초과 시 문장 단위로 재분할
        if len(para) <= _MAX_CHARS_PER_SLIDE:
            slides.append(para)
        else:
            sentences = re.split(r'(?<=[.!?。])\s+', para)
            current = ''
            for sentence in sentences:
                if len(current) + len(sentence) + 1 <= _MAX_CHARS_PER_SLIDE:
                    current = f'{current} {sentence}'.strip() if current else sentence
                else:
                    if current:
                        slides.append(current)
                    current = sentence
            if current:
                slides.append(current)

    return slides


def _assign_slide_durations(slide_count: int, total_seconds: int) -> List[int]:
    """전체 시간을 슬라이드에 배분합니다."""
    if slide_count == 0:
        return []

    base = max(_MIN_SLIDE_DURATION, total_seconds // slide_count)
    durations = [base] * slide_count

    # 남은 시간 분배
    remainder = total_seconds - sum(durations)
    if remainder > 0:
        for i in range(min(remainder, slide_count)):
            durations[i] += 1
    elif remainder < 0:
        # 시간이 부족하면 최소 시간 보장
        durations = [_MIN_SLIDE_DURATION] * slide_count

    return durations


def create_signage_loop(
    content: str,
    duration_seconds: int = 30,
) -> SignageLoop:
    """
    콘텐츠로 사이니지 루프를 생성합니다.

    Args:
        content: 콘텐츠 텍스트
        duration_seconds: 1회 루프 총 시간(초), 기본 30초

    Returns:
        SignageLoop 결과

    Raises:
        ValueError: duration_seconds가 0 이하인 경우
    """
    if duration_seconds <= 0:
        raise ValueError(f'duration_seconds는 양수여야 합니다: {duration_seconds}')

    if not content or not content.strip():
        loop_id = _generate_loop_id('', duration_seconds)
        return SignageLoop(
            loop_id=loop_id,
            slides=[],
            total_duration=0,
            loop_count=0,
        )

    slide_texts = _split_into_slide_texts(content)
    if not slide_texts:
        loop_id = _generate_loop_id(content, duration_seconds)
        return SignageLoop(
            loop_id=loop_id,
            slides=[],
            total_duration=0,
            loop_count=0,
        )

    durations = _assign_slide_durations(len(slide_texts), duration_seconds)

    slides = []
    for i, text in enumerate(slide_texts):
        transition = _TRANSITIONS[i % len(_TRANSITIONS)]
        bg_color = _BACKGROUND_COLORS[i % len(_BACKGROUND_COLORS)]
        dur = durations[i] if i < len(durations) else _MIN_SLIDE_DURATION

        slides.append(SignageSlide(
            text=text,
            duration_seconds=dur,
            transition=transition,
            background_color=bg_color,
        ))

    actual_duration = sum(s.duration_seconds for s in slides)
    # 루프 횟수: 목표 시간 / 실제 1회 시간 (최소 1)
    loop_count = max(1, duration_seconds // actual_duration) if actual_duration > 0 else 1
    loop_id = _generate_loop_id(content, duration_seconds)

    return SignageLoop(
        loop_id=loop_id,
        slides=slides,
        total_duration=actual_duration,
        loop_count=loop_count,
    )
