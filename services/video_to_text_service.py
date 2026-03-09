"""
비디오 투 텍스트 내레이션 서비스

영상 자막을 기반으로 스타일별 내레이션 텍스트를 생성합니다.
descriptive / action / documentary 세 가지 스타일을 지원하며,
외부 API 없이 자막 텍스트 변환만 수행합니다.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)

# 지원 스타일 목록
SUPPORTED_STYLES = ("descriptive", "action", "documentary")


@dataclass
class NarrationSegment:
    """내레이션의 개별 세그먼트를 나타내는 데이터 클래스."""
    timestamp: str    # "MM:SS" 형식
    text: str         # 변환된 내레이션 텍스트
    scene_type: str   # "narration", "transition", "highlight"


@dataclass
class NarrationResult:
    """비디오 내레이션 생성 결과를 나타내는 데이터 클래스."""
    video_id: str
    narration: str                       # 전체 내레이션 텍스트
    segments: List[NarrationSegment]     # 세그먼트 목록
    word_count: int                      # 전체 단어 수
    style: str                           # 적용된 스타일


def _format_timestamp(seconds: int) -> str:
    """초 단위를 MM:SS 형식 문자열로 변환합니다."""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def _split_sentences(transcript: str) -> List[str]:
    """자막 텍스트를 문장 단위로 분리합니다."""
    if not transcript or not transcript.strip():
        return []
    sentences = re.split(r'[.\n!?]+', transcript)
    return [s.strip() for s in sentences if s.strip()]


def _count_words(text: str) -> int:
    """텍스트의 단어 수를 계산합니다 (한국어: 공백 기준)."""
    if not text:
        return 0
    return len(text.split())


def _transform_descriptive(sentence: str) -> str:
    """서술형 스타일로 문장을 변환합니다."""
    return f"이 장면에서는 {sentence}에 대해 설명하고 있습니다."


def _transform_action(sentence: str) -> str:
    """액션형 스타일로 문장을 변환합니다."""
    return f"[액션] {sentence} — 주목할 포인트입니다."


def _transform_documentary(sentence: str) -> str:
    """다큐멘터리형 스타일로 문장을 변환합니다."""
    return f"내레이터: \"{sentence}\""


# 스타일별 변환 함수 매핑
_STYLE_TRANSFORMERS = {
    "descriptive": _transform_descriptive,
    "action": _transform_action,
    "documentary": _transform_documentary,
}


def _assign_scene_type(index: int, total: int) -> str:
    """세그먼트 인덱스에 따라 장면 타입을 지정합니다.

    첫 번째와 마지막 세그먼트는 transition,
    중간 세그먼트 중 3의 배수는 highlight,
    나머지는 narration으로 분류합니다.
    """
    if index == 0 or index == total - 1:
        return "transition"
    if index % 3 == 0:
        return "highlight"
    return "narration"


def narrate_video(
    video_id: str,
    transcript: str = '',
    style: str = 'descriptive',
) -> NarrationResult:
    """비디오 자막을 스타일별 내레이션 텍스트로 변환합니다.

    Args:
        video_id: YouTube 영상 ID
        transcript: 영상 자막 텍스트
        style: 내레이션 스타일 ("descriptive", "action", "documentary")

    Returns:
        NarrationResult — 전체 내레이션 + 세그먼트 목록

    Raises:
        ValueError: 지원하지 않는 스타일인 경우
    """
    if style not in SUPPORTED_STYLES:
        raise ValueError(
            f"지원하지 않는 스타일: '{style}'. "
            f"사용 가능: {', '.join(SUPPORTED_STYLES)}"
        )

    if not transcript or not transcript.strip():
        logger.info("빈 자막 — 빈 내레이션 반환 (video_id=%s)", video_id)
        return NarrationResult(
            video_id=video_id,
            narration="",
            segments=[],
            word_count=0,
            style=style,
        )

    sentences = _split_sentences(transcript)
    if not sentences:
        return NarrationResult(
            video_id=video_id,
            narration="",
            segments=[],
            word_count=0,
            style=style,
        )

    transformer = _STYLE_TRANSFORMERS[style]
    segments: List[NarrationSegment] = []
    total = len(sentences)

    for idx, sentence in enumerate(sentences):
        transformed = transformer(sentence)
        timestamp = _format_timestamp(idx * 10)
        scene_type = _assign_scene_type(idx, total)

        segments.append(NarrationSegment(
            timestamp=timestamp,
            text=transformed,
            scene_type=scene_type,
        ))

    # 전체 내레이션 텍스트 조합
    narration = "\n".join(seg.text for seg in segments)

    result = NarrationResult(
        video_id=video_id,
        narration=narration,
        segments=segments,
        word_count=_count_words(narration),
        style=style,
    )

    logger.info(
        "내레이션 생성 완료 (video_id=%s, style=%s, segments=%d, words=%d)",
        video_id, style, len(segments), result.word_count,
    )
    return result
