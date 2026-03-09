"""
AI 흔적 포렌식 서비스.

콘텐츠에서 AI 생성 흔적을 탐지한다.
반복 패턴, 균일 문장 길이, 일반적 전환어 과다 사용 등을 분석.
"""

import math
import re
import uuid
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ForensicIndicator:
    """포렌식 지표."""
    indicator_type: str  # repetitive_phrases / low_perplexity / uniform_length / generic_transitions / lack_of_specificity
    confidence: float  # 0.0~1.0
    evidence: str


@dataclass
class ForensicReport:
    """포렌식 분석 보고서."""
    content_id: str
    indicators: list  # list[ForensicIndicator]
    ai_probability: float  # 0.0~1.0
    human_edits_detected: bool


# 일반적 전환어 목록
_GENERIC_TRANSITIONS = [
    "또한", "그러나", "따라서", "한편", "그러므로",
    "게다가", "반면에", "결론적으로", "마찬가지로", "더불어",
    "이처럼", "그렇기 때문에", "요약하면", "정리하면",
]

# 인간적 편집 흔적 (오타, 구어체, 이모지 등)
_HUMAN_MARKERS = ["ㅋㅋ", "ㅎㅎ", "ㅠㅠ", "...", "!!", "??", "~"]


def _split_sentences(text: str) -> list:
    """텍스트를 문장 단위로 분리한다."""
    # 마침표/물음표/느낌표 기준 분리
    sentences = re.split(r"[.!?。]\s*", text)
    return [s.strip() for s in sentences if s.strip()]


def _get_ngrams(text: str, n: int) -> list:
    """n-gram 리스트를 반환한다."""
    words = text.split()
    if len(words) < n:
        return []
    return [" ".join(words[i : i + n]) for i in range(len(words) - n + 1)]


def detect_repetitive_patterns(text: str) -> Optional[ForensicIndicator]:
    """반복 패턴을 탐지한다 (3-gram 빈도 분석)."""
    trigrams = _get_ngrams(text, 3)
    if len(trigrams) < 5:
        return None

    counts = Counter(trigrams)
    repeated = {gram: cnt for gram, cnt in counts.items() if cnt >= 3}

    if not repeated:
        return None

    # 반복 비율로 신뢰도 산출
    repeat_ratio = sum(repeated.values()) / len(trigrams)
    confidence = min(repeat_ratio * 3.0, 1.0)

    top_repeated = sorted(repeated.items(), key=lambda x: x[1], reverse=True)[:3]
    evidence = ", ".join(f"'{g}'({c}회)" for g, c in top_repeated)

    return ForensicIndicator(
        indicator_type="repetitive_phrases",
        confidence=round(confidence, 2),
        evidence=f"반복 3-gram 탐지: {evidence}",
    )


def detect_uniform_length(text: str) -> Optional[ForensicIndicator]:
    """균일 문장 길이를 탐지한다 (변동계수 < 0.2)."""
    sentences = _split_sentences(text)
    if len(sentences) < 5:
        return None

    lengths = [len(s) for s in sentences]
    mean = sum(lengths) / len(lengths)
    if mean == 0:
        return None

    variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
    std_dev = math.sqrt(variance)
    cv = std_dev / mean  # 변동계수

    if cv >= 0.2:
        return None

    confidence = max(0.0, 1.0 - cv * 5)  # CV가 낮을수록 AI 가능성 높음
    return ForensicIndicator(
        indicator_type="uniform_length",
        confidence=round(confidence, 2),
        evidence=f"문장 길이 변동계수 {cv:.3f} (평균 {mean:.1f}자, 표준편차 {std_dev:.1f})",
    )


def detect_generic_transitions(text: str) -> Optional[ForensicIndicator]:
    """일반적 전환어 과다 사용을 탐지한다."""
    sentences = _split_sentences(text)
    if len(sentences) < 3:
        return None

    transition_count = 0
    found_transitions = []
    for sentence in sentences:
        for t in _GENERIC_TRANSITIONS:
            if t in sentence:
                transition_count += 1
                found_transitions.append(t)
                break  # 문장당 1회만 카운트

    ratio = transition_count / len(sentences)
    if ratio < 0.3:
        return None

    confidence = min(ratio * 1.5, 1.0)
    top_transitions = Counter(found_transitions).most_common(5)
    evidence_list = ", ".join(f"'{t}'({c}회)" for t, c in top_transitions)

    return ForensicIndicator(
        indicator_type="generic_transitions",
        confidence=round(confidence, 2),
        evidence=f"전환어 비율 {ratio:.0%} — {evidence_list}",
    )


def _detect_human_edits(text: str) -> bool:
    """인간 편집 흔적을 탐지한다."""
    return any(marker in text for marker in _HUMAN_MARKERS)


def calculate_ai_probability(indicators: list) -> float:
    """AI 생성 확률을 계산한다 (가중합)."""
    if not indicators:
        return 0.0

    # 지표별 가중치
    weights = {
        "repetitive_phrases": 0.30,
        "uniform_length": 0.25,
        "generic_transitions": 0.25,
        "low_perplexity": 0.10,
        "lack_of_specificity": 0.10,
    }

    total_weight = 0.0
    weighted_sum = 0.0
    for ind in indicators:
        w = weights.get(ind.indicator_type, 0.1)
        weighted_sum += ind.confidence * w
        total_weight += w

    if total_weight == 0:
        return 0.0

    return round(min(weighted_sum / total_weight, 1.0), 2)


def analyze_content(content: dict) -> ForensicReport:
    """콘텐츠에서 AI 흔적을 종합 분석한다."""
    content_id = content.get("id", f"fc_{uuid.uuid4().hex[:8]}")
    text = content.get("text", "")

    indicators = []

    # 각 탐지기 실행
    rep = detect_repetitive_patterns(text)
    if rep:
        indicators.append(rep)

    uni = detect_uniform_length(text)
    if uni:
        indicators.append(uni)

    gen = detect_generic_transitions(text)
    if gen:
        indicators.append(gen)

    ai_prob = calculate_ai_probability(indicators)
    human_edits = _detect_human_edits(text)

    return ForensicReport(
        content_id=content_id,
        indicators=indicators,
        ai_probability=ai_prob,
        human_edits_detected=human_edits,
    )
