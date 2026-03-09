"""
다국어 더빙 팩 서비스 (T12.3)
영상 자막을 다국어로 번역하여 더빙 팩을 생성합니다.
시뮬레이션된 번역 (언어별 접두사 추가 방식).
"""
import re
import uuid
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 언어별 접두사 (시뮬레이션 번역)
LANGUAGE_PREFIXES = {
    'en': '[EN] ',
    'ja': '[JA] ',
    'ko': '[KO] ',
    'zh': '[ZH] ',
    'es': '[ES] ',
    'fr': '[FR] ',
    'de': '[DE] ',
    'pt': '[PT] ',
}

# 지원 언어 목록
SUPPORTED_LANGUAGES = set(LANGUAGE_PREFIXES.keys())

# 기본 세그먼트 길이 (초)
DEFAULT_SEGMENT_DURATION = 5.0


@dataclass
class DubSegment:
    """더빙 세그먼트 — 하나의 자막 구간"""
    timestamp: str
    original_text: str
    translated_text: str
    duration_seconds: float


@dataclass
class DubTrack:
    """더빙 트랙 — 특정 언어의 전체 세그먼트"""
    language: str
    segments: list[DubSegment] = field(default_factory=list)
    estimated_duration: float = 0.0


@dataclass
class DubPack:
    """더빙 팩 — 영상 하나에 대한 다국어 더빙 묶음"""
    video_id: str
    original_language: str
    dub_tracks: list[DubTrack] = field(default_factory=list)
    total_segments: int = 0


def _split_transcript(transcript: str) -> list[str]:
    """자막 텍스트를 문장 단위로 분할합니다."""
    if not transcript or not transcript.strip():
        return []

    # 문장 부호 기준 분할
    sentences = re.split(r'(?<=[.!?。！？])\s+', transcript.strip())
    # 빈 문자열 제거
    return [s.strip() for s in sentences if s.strip()]


def _translate_text(text: str, target_language: str) -> str:
    """시뮬레이션 번역 — 언어 접두사를 추가합니다."""
    prefix = LANGUAGE_PREFIXES.get(target_language, f'[{target_language.upper()}] ')
    return f"{prefix}{text}"


def _estimate_duration(text: str) -> float:
    """텍스트 길이 기반 예상 소요 시간(초)을 계산합니다."""
    # 대략 초당 4단어 (또는 한글 8자) 기준
    word_count = len(text.split())
    char_count = len(text)

    # 한글이 포함되면 글자 수 기준, 아니면 단어 수 기준
    has_korean = any('\uac00' <= c <= '\ud7a3' for c in text)
    if has_korean:
        duration = char_count / 8.0
    else:
        duration = word_count / 4.0

    return max(round(duration, 1), 1.0)


def _format_timestamp(seconds: float) -> str:
    """초를 MM:SS 형식으로 변환합니다."""
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes:02d}:{secs:02d}"


def create_dub_pack(
    video_id: str,
    languages: list[str],
    transcript: str = '',
    original_language: str = 'ko',
) -> DubPack:
    """다국어 더빙 팩을 생성합니다.

    Args:
        video_id: YouTube 영상 ID
        languages: 번역 대상 언어 코드 리스트 (예: ["en", "ja"])
        transcript: 원본 자막 텍스트
        original_language: 원본 언어 코드

    Returns:
        DubPack: 생성된 더빙 팩

    Raises:
        ValueError: video_id가 비어있거나, languages가 비어있을 때
    """
    if not video_id or not video_id.strip():
        raise ValueError("video_id는 필수입니다")

    if not languages:
        raise ValueError("최소 하나의 대상 언어가 필요합니다")

    # 유효한 언어만 필터링
    valid_languages = [lang for lang in languages if lang in SUPPORTED_LANGUAGES]
    if not valid_languages:
        raise ValueError(f"지원되지 않는 언어입니다. 지원: {sorted(SUPPORTED_LANGUAGES)}")

    # 원본 언어와 동일한 언어는 제외
    valid_languages = [lang for lang in valid_languages if lang != original_language]

    sentences = _split_transcript(transcript)

    dub_tracks = []
    current_time = 0.0

    for lang in valid_languages:
        segments = []
        track_time = 0.0

        for sentence in sentences:
            translated = _translate_text(sentence, lang)
            duration = _estimate_duration(sentence)
            timestamp = _format_timestamp(track_time)

            segment = DubSegment(
                timestamp=timestamp,
                original_text=sentence,
                translated_text=translated,
                duration_seconds=duration,
            )
            segments.append(segment)
            track_time += duration

        track = DubTrack(
            language=lang,
            segments=segments,
            estimated_duration=round(track_time, 1),
        )
        dub_tracks.append(track)

    total_segments = sum(len(t.segments) for t in dub_tracks)

    pack = DubPack(
        video_id=video_id.strip(),
        original_language=original_language,
        dub_tracks=dub_tracks,
        total_segments=total_segments,
    )

    logger.info(
        f"더빙 팩 생성: video={video_id}, "
        f"언어={len(valid_languages)}개, 세그먼트={total_segments}개"
    )
    return pack
