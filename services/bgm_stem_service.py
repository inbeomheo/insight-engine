"""
BGM 추천 서비스

콘텐츠의 분위기와 구조를 분석하여 적절한 BGM을 추천합니다.
외부 API 없이 키워드 기반 분위기 매칭으로 동작합니다.
"""
import re
import logging
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)

SUPPORTED_MOODS = ('upbeat', 'calm', 'dramatic', 'neutral', 'melancholic')


@dataclass
class BGMSuggestion:
    """BGM 추천 항목"""
    track_name: str
    genre: str
    mood: str
    bpm: int
    energy_level: float  # 0.0 ~ 1.0
    timestamp_range: str  # "0:00-1:30" 형식


# 분위기별 BGM 라이브러리 (프리셋)
_BGM_LIBRARY = {
    'upbeat': [
        {'track_name': 'Sunrise Groove', 'genre': 'pop', 'bpm': 128, 'energy_level': 0.8},
        {'track_name': 'Bright Morning', 'genre': 'electronic', 'bpm': 120, 'energy_level': 0.75},
        {'track_name': 'Happy Steps', 'genre': 'acoustic', 'bpm': 110, 'energy_level': 0.7},
        {'track_name': 'Energy Wave', 'genre': 'dance', 'bpm': 135, 'energy_level': 0.9},
    ],
    'calm': [
        {'track_name': 'Gentle Rain', 'genre': 'ambient', 'bpm': 70, 'energy_level': 0.2},
        {'track_name': 'Soft Breeze', 'genre': 'lo-fi', 'bpm': 80, 'energy_level': 0.3},
        {'track_name': 'Morning Dew', 'genre': 'classical', 'bpm': 60, 'energy_level': 0.15},
        {'track_name': 'Still Water', 'genre': 'new age', 'bpm': 65, 'energy_level': 0.2},
    ],
    'dramatic': [
        {'track_name': 'Rising Storm', 'genre': 'orchestral', 'bpm': 140, 'energy_level': 0.9},
        {'track_name': 'Epic Journey', 'genre': 'cinematic', 'bpm': 130, 'energy_level': 0.85},
        {'track_name': 'Dark Pulse', 'genre': 'electronic', 'bpm': 150, 'energy_level': 0.95},
        {'track_name': 'Thunder March', 'genre': 'orchestral', 'bpm': 120, 'energy_level': 0.8},
    ],
    'neutral': [
        {'track_name': 'Background Flow', 'genre': 'lo-fi', 'bpm': 90, 'energy_level': 0.4},
        {'track_name': 'Steady Beat', 'genre': 'jazz', 'bpm': 95, 'energy_level': 0.45},
        {'track_name': 'Subtle Rhythm', 'genre': 'ambient', 'bpm': 85, 'energy_level': 0.35},
        {'track_name': 'Even Keel', 'genre': 'pop', 'bpm': 100, 'energy_level': 0.5},
    ],
    'melancholic': [
        {'track_name': 'Fading Light', 'genre': 'piano', 'bpm': 65, 'energy_level': 0.2},
        {'track_name': 'Autumn Leaves', 'genre': 'classical', 'bpm': 70, 'energy_level': 0.25},
        {'track_name': 'Lonely Road', 'genre': 'acoustic', 'bpm': 75, 'energy_level': 0.3},
        {'track_name': 'Grey Skies', 'genre': 'ambient', 'bpm': 60, 'energy_level': 0.15},
    ],
}

# 분위기 감지 키워드
_MOOD_KEYWORDS = {
    'upbeat': ['재미', '신나', '즐거', '웃음', '축하', 'fun', 'happy', 'exciting', 'great'],
    'calm': ['조용', '평화', '힐링', '편안', '고요', 'calm', 'peaceful', 'relax', 'gentle'],
    'dramatic': ['충격', '반전', '위기', '긴장', '갈등', 'shock', 'crisis', 'tension', 'conflict'],
    'melancholic': ['슬픔', '아쉬', '이별', '그리움', '외로', 'sad', 'miss', 'lonely', 'farewell'],
}


def _detect_mood(content: str) -> str:
    """콘텐츠에서 분위기를 감지합니다."""
    content_lower = content.lower()
    scores = {}
    for mood, keywords in _MOOD_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in content_lower)
        scores[mood] = score

    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return 'neutral'
    return best


def _split_segments(content: str) -> List[str]:
    """콘텐츠를 시간 구간에 매핑할 세그먼트로 분리합니다."""
    paragraphs = re.split(r'\n\s*\n', content.strip())
    return [p.strip() for p in paragraphs if p.strip()]


def _format_timestamp(start_seconds: float, end_seconds: float) -> str:
    """초 단위를 MM:SS-MM:SS 형식으로 변환합니다."""
    def _fmt(s):
        m = int(s) // 60
        sec = int(s) % 60
        return f'{m}:{sec:02d}'
    return f'{_fmt(start_seconds)}-{_fmt(end_seconds)}'


def suggest_bgm(
    content: str,
    mood: str = 'neutral',
) -> List[BGMSuggestion]:
    """
    콘텐츠에 맞는 BGM을 추천합니다.

    Args:
        content: 콘텐츠 텍스트
        mood: 분위기 ("upbeat", "calm", "dramatic", "neutral", "melancholic")

    Returns:
        BGMSuggestion 리스트

    Raises:
        ValueError: 지원하지 않는 분위기가 지정된 경우
    """
    if not content or not content.strip():
        return []

    if mood not in SUPPORTED_MOODS:
        raise ValueError(
            f'지원하지 않는 분위기: {mood}. '
            f'지원 목록: {list(SUPPORTED_MOODS)}'
        )

    # 분위기가 neutral이면 자동 감지 시도
    effective_mood = mood
    if mood == 'neutral':
        detected = _detect_mood(content)
        if detected != 'neutral':
            effective_mood = detected

    library = _BGM_LIBRARY.get(effective_mood, _BGM_LIBRARY['neutral'])
    segments = _split_segments(content)
    segment_count = max(len(segments), 1)

    # 세그먼트당 예상 시간 (30초 기준)
    duration_per_segment = 30.0

    suggestions = []
    for i in range(min(segment_count, len(library))):
        track = library[i]
        start_s = i * duration_per_segment
        end_s = start_s + duration_per_segment

        suggestions.append(BGMSuggestion(
            track_name=track['track_name'],
            genre=track['genre'],
            mood=effective_mood,
            bpm=track['bpm'],
            energy_level=track['energy_level'],
            timestamp_range=_format_timestamp(start_s, end_s),
        ))

    return suggestions
