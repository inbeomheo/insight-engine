"""서사 비트 서비스 — 자막에서 서사 구조(narrative beats) 태그

자막 텍스트를 분석하여 도입(introduction), 전개(development),
전환점(turning_point), 클라이맥스(climax), 해결(resolution) 등
서사 구조 비트를 자동 태그합니다.
"""
import logging
import re
from dataclasses import dataclass, asdict
from typing import List

logger = logging.getLogger(__name__)

# 서사 비트 유형과 탐지 키워드/패턴
_BEAT_TYPES = ["introduction", "development", "turning_point", "climax", "resolution"]

# 비트 유형별 탐지 단서 (한국어 + 영어)
_BEAT_INDICATORS = {
    "introduction": {
        "keywords": ["안녕하세요", "오늘", "소개", "시작", "먼저", "들어가",
                      "hello", "today", "introduce", "begin", "welcome"],
        "position_range": (0.0, 0.25),  # 텍스트 앞부분
    },
    "development": {
        "keywords": ["그리고", "또한", "다음으로", "이어서", "구체적으로",
                      "자세히", "살펴보", "예를 들", "furthermore", "also",
                      "additionally", "detail", "explain"],
        "position_range": (0.15, 0.7),  # 중간부
    },
    "turning_point": {
        "keywords": ["하지만", "그런데", "반면", "그러나", "반대로", "사실",
                      "놀랍게도", "의외로", "however", "but", "actually",
                      "surprisingly", "contrary", "yet"],
        "position_range": (0.3, 0.8),  # 중후반
    },
    "climax": {
        "keywords": ["가장 중요", "핵심", "결정적", "바로", "드디어",
                      "마침내", "결국", "최종", "crucial", "key",
                      "most important", "finally", "ultimately"],
        "position_range": (0.5, 0.9),  # 후반부
    },
    "resolution": {
        "keywords": ["결론", "정리", "마무리", "요약", "마치", "감사",
                      "끝으로", "다음에", "conclusion", "summary",
                      "wrap up", "thank", "in closing"],
        "position_range": (0.7, 1.0),  # 끝부분
    },
}


@dataclass
class NarrativeBeat:
    """서사 비트 (서사 구조의 단위 요소)"""
    beat_type: str        # "introduction" | "development" | "turning_point" | "climax" | "resolution"
    start_position: int   # 문자 위치
    text_excerpt: str     # 해당 구간 발췌문
    intensity: float      # 0.0~1.0 (서사 강도)


def tag_narrative_beats(transcript: str) -> List[NarrativeBeat]:
    """자막에서 도입-전개-전환-클라이맥스-해결 비트를 태그합니다.

    Args:
        transcript: 자막 텍스트

    Returns:
        NarrativeBeat 리스트 (위치 순 정렬)

    Raises:
        ValueError: 자막이 비어있을 때
    """
    if not transcript or not transcript.strip():
        raise ValueError("자막 텍스트가 비어있습니다")

    stripped = transcript.strip()
    if len(stripped) < 20:
        raise ValueError("자막이 너무 짧아 서사 분석이 불가합니다 (최소 20자)")

    # 문장 단위로 분리
    sentences = _split_sentences(stripped)
    if not sentences:
        return []

    total_len = len(stripped)
    beats: List[NarrativeBeat] = []

    for sentence_text, char_pos in sentences:
        relative_pos = char_pos / total_len if total_len > 0 else 0.0
        detected = _detect_beat_type(sentence_text, relative_pos)

        if detected:
            beat_type, intensity = detected
            # 발췌문은 최대 100자
            excerpt = sentence_text[:100].strip()
            beats.append(NarrativeBeat(
                beat_type=beat_type,
                start_position=char_pos,
                text_excerpt=excerpt,
                intensity=intensity,
            ))

    # 비트가 없으면 기본 구조 생성 (최소 도입/해결)
    if not beats:
        beats = _create_default_beats(stripped, sentences)

    # 위치 순 정렬
    beats.sort(key=lambda b: b.start_position)

    # 중복 제거: 같은 비트 유형이 연속이면 강도 높은 것만 유지
    beats = _deduplicate_beats(beats)

    return beats


def _split_sentences(text: str) -> List[tuple]:
    """텍스트를 문장 단위로 분리하고 각 문장의 시작 위치를 반환합니다.

    Returns:
        [(문장_텍스트, 문자_시작_위치), ...]
    """
    # 줄바꿈 또는 문장부호로 분리
    pattern = r'[.!?。！？\n]+'
    parts = re.split(pattern, text)

    sentences = []
    pos = 0
    for part in parts:
        part = part.strip()
        if part and len(part) >= 5:  # 너무 짧은 조각 제외
            # 원본에서의 위치 찾기
            idx = text.find(part, pos)
            if idx >= 0:
                sentences.append((part, idx))
                pos = idx + len(part)
            else:
                sentences.append((part, pos))

    return sentences


def _detect_beat_type(sentence: str, relative_pos: float) -> tuple:
    """문장에서 서사 비트 유형을 감지합니다.

    Args:
        sentence: 문장 텍스트
        relative_pos: 전체 텍스트 내 상대적 위치 (0.0~1.0)

    Returns:
        (beat_type, intensity) 또는 None
    """
    lower = sentence.lower()
    best_match = None
    best_score = 0.0

    for beat_type, indicators in _BEAT_INDICATORS.items():
        pos_min, pos_max = indicators["position_range"]

        # 위치 적합성 검사
        if not (pos_min <= relative_pos <= pos_max):
            continue

        # 키워드 매칭 점수
        keyword_hits = sum(1 for kw in indicators["keywords"] if kw in lower)
        if keyword_hits == 0:
            continue

        # 점수 계산: 키워드 적중 수 + 위치 적합도
        pos_fitness = 1.0 - abs(relative_pos - (pos_min + pos_max) / 2) / 0.5
        pos_fitness = max(0.0, min(1.0, pos_fitness))

        score = min(keyword_hits * 0.3, 0.6) + pos_fitness * 0.4

        if score > best_score:
            best_score = score
            best_match = beat_type

    if best_match:
        intensity = max(0.1, min(1.0, round(best_score, 2)))
        return (best_match, intensity)

    return None


def _create_default_beats(text: str, sentences: List[tuple]) -> List[NarrativeBeat]:
    """키워드 매칭이 없을 때 위치 기반 기본 비트를 생성합니다."""
    if not sentences:
        return []

    beats = []
    total = len(sentences)

    # 첫 문장 → introduction
    first_text, first_pos = sentences[0]
    beats.append(NarrativeBeat(
        beat_type="introduction",
        start_position=first_pos,
        text_excerpt=first_text[:100].strip(),
        intensity=0.5,
    ))

    # 마지막 문장 → resolution
    if total > 1:
        last_text, last_pos = sentences[-1]
        beats.append(NarrativeBeat(
            beat_type="resolution",
            start_position=last_pos,
            text_excerpt=last_text[:100].strip(),
            intensity=0.5,
        ))

    # 중간 지점 → development
    if total > 2:
        mid_idx = total // 2
        mid_text, mid_pos = sentences[mid_idx]
        beats.append(NarrativeBeat(
            beat_type="development",
            start_position=mid_pos,
            text_excerpt=mid_text[:100].strip(),
            intensity=0.4,
        ))

    return beats


def _deduplicate_beats(beats: List[NarrativeBeat]) -> List[NarrativeBeat]:
    """같은 유형의 연속 비트 중 강도가 높은 것만 유지합니다."""
    if len(beats) <= 1:
        return beats

    result = [beats[0]]
    for beat in beats[1:]:
        if beat.beat_type == result[-1].beat_type:
            # 강도가 더 높으면 교체
            if beat.intensity > result[-1].intensity:
                result[-1] = beat
        else:
            result.append(beat)

    return result


def narrative_beats_to_dicts(beats: List[NarrativeBeat]) -> List[dict]:
    """NarrativeBeat 리스트를 직렬화 가능한 dict 리스트로 변환합니다."""
    return [asdict(b) for b in beats]
