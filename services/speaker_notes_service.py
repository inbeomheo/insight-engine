"""
화자별 발언 노트 추출 서비스

자막 텍스트에서 화자를 식별하고, 각 화자의 발언 노트·핵심 포인트를 추출합니다.
외부 API 없이 텍스트 패턴 분석으로 동작합니다.
"""
import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

# 화자 구분 패턴: "화자:", "화자 :", "[화자]", "(화자)" 등
_SPEAKER_PATTERNS = [
    re.compile(r'^\[([^\]]+)\]\s*(.+)', re.MULTILINE),       # [화자] 발언
    re.compile(r'^\(([^)]+)\)\s*(.+)', re.MULTILINE),        # (화자) 발언
    re.compile(r'^([A-Za-z가-힣\s]{1,20})\s*:\s*(.+)', re.MULTILINE),  # 화자: 발언
]

# 핵심 포인트 추출을 위한 키워드 (한/영)
_KEY_PHRASES = [
    '중요한', '핵심', '결론', '요약하면', '정리하면', '포인트는',
    'important', 'key point', 'in summary', 'conclusion', 'takeaway',
    '첫째', '둘째', '셋째', '마지막으로', '결국',
]


@dataclass
class SpeakerNote:
    """화자별 발언 노트"""
    speaker: str
    notes: List[str] = field(default_factory=list)
    word_count: int = 0
    key_points: List[str] = field(default_factory=list)


def _detect_speakers(transcript: str, speakers: Optional[List[str]] = None) -> dict:
    """자막에서 화자별 발언을 분리합니다."""
    result = {}

    # 사전 지정 화자가 있으면 패턴 매칭 시도
    for pattern in _SPEAKER_PATTERNS:
        matches = pattern.findall(transcript)
        if matches:
            for speaker_name, text in matches:
                speaker_name = speaker_name.strip()
                # 사전 지정 화자 필터링
                if speakers and speaker_name not in speakers:
                    continue
                if speaker_name not in result:
                    result[speaker_name] = []
                result[speaker_name].append(text.strip())
            if result:
                return result

    # 패턴 매칭 실패 시 — 사전 지정 화자로 라인 분배
    if speakers:
        lines = [line.strip() for line in transcript.split('\n') if line.strip()]
        for i, line in enumerate(lines):
            speaker_idx = i % len(speakers)
            speaker_name = speakers[speaker_idx]
            if speaker_name not in result:
                result[speaker_name] = []
            result[speaker_name].append(line)
        return result

    # 화자 정보 없으면 기본 화자 1명으로 처리
    lines = [line.strip() for line in transcript.split('\n') if line.strip()]
    if lines:
        result['Speaker'] = lines

    return result


def _count_words(text: str) -> int:
    """한국어+영어 혼합 단어 수를 셉니다."""
    # 한국어: 공백 기준 분리, 영어: 공백 기준 분리
    words = text.split()
    return len(words)


def _extract_key_points(notes: List[str]) -> List[str]:
    """발언 목록에서 핵심 포인트를 추출합니다."""
    key_points = []
    for note in notes:
        note_lower = note.lower()
        for phrase in _KEY_PHRASES:
            if phrase in note_lower:
                # 중복 방지
                if note not in key_points:
                    key_points.append(note)
                break
    return key_points


def extract_speaker_notes(
    transcript: str,
    speakers: Optional[List[str]] = None
) -> List[SpeakerNote]:
    """
    자막에서 화자별 발언 노트를 추출합니다.

    Args:
        transcript: 자막 텍스트
        speakers: 사전 지정 화자 목록 (None이면 자동 감지)

    Returns:
        화자별 SpeakerNote 리스트
    """
    if not transcript or not transcript.strip():
        return []

    speaker_lines = _detect_speakers(transcript, speakers)
    if not speaker_lines:
        return []

    results = []
    for speaker_name, notes in speaker_lines.items():
        all_text = ' '.join(notes)
        word_count = _count_words(all_text)
        key_points = _extract_key_points(notes)

        results.append(SpeakerNote(
            speaker=speaker_name,
            notes=notes,
            word_count=word_count,
            key_points=key_points,
        ))

    # 발언량(단어 수) 내림차순 정렬
    results.sort(key=lambda x: x.word_count, reverse=True)
    return results
