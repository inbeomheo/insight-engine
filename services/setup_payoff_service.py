"""설정-회수 패턴 추적 서비스 — 자막에서 설정(setup)과 회수(payoff) 쌍을 탐지"""
import re
from dataclasses import dataclass


@dataclass
class SetupPayoff:
    """설정-회수 쌍"""
    setup_text: str
    payoff_text: str
    setup_position: int  # 문장 인덱스
    payoff_position: int  # 문장 인덱스
    distance: int  # payoff_position - setup_position


# 최소 거리 — 너무 가까운 반복은 설정-회수가 아닌 단순 반복
_MIN_DISTANCE = 2
# 최대 거리 — 너무 먼 반복은 관련성 낮음
_MAX_DISTANCE = 50

# 불용어 (설정-회수 키워드에서 제외)
_STOPWORDS = {
    # 한국어 불용어
    "그", "이", "저", "것", "수", "등", "및", "또", "더", "좀", "잘", "못",
    "를", "을", "에", "의", "가", "는", "은", "로", "와", "과", "도", "만",
    "그리고", "하지만", "그래서", "그런데", "그러나", "그러면", "때문에",
    "이런", "저런", "그런", "이것", "그것", "저것", "여기", "거기", "저기",
    "아주", "매우", "정말", "진짜", "너무", "조금",
    # 영어 불용어
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "this", "that", "these", "those",
    "and", "but", "or", "so", "if", "then", "than", "very", "really",
    "just", "also", "about", "with", "from", "into", "for", "not",
}


def _split_sentences(transcript: str) -> list[str]:
    """자막을 문장 단위로 분리한다."""
    # 마침표, 느낌표, 물음표, 줄바꿈으로 분리
    raw = re.split(r'[.!?。\n]+', transcript)
    sentences = []
    for s in raw:
        s = s.strip()
        if len(s) >= 5:  # 너무 짧은 문장 제외
            sentences.append(s)
    return sentences


def _extract_keywords(sentence: str) -> set[str]:
    """문장에서 의미 있는 키워드를 추출한다."""
    # 한글 + 영문 단어 추출
    tokens = re.findall(r'[가-힣]{2,}|[a-zA-Z]{3,}', sentence)
    keywords = set()
    for token in tokens:
        t_lower = token.lower()
        if t_lower not in _STOPWORDS and len(t_lower) >= 2:
            keywords.add(t_lower)
    return keywords


def _find_keyword_repeats(sentences: list[str]) -> list[tuple[int, int, str]]:
    """키워드 반복 패턴을 찾는다. (setup_idx, payoff_idx, keyword) 튜플 리스트."""
    # 각 문장의 키워드 인덱스 매핑
    sentence_keywords: list[set[str]] = [
        _extract_keywords(s) for s in sentences
    ]

    # 키워드별 첫 등장 위치 기록
    keyword_first: dict[str, int] = {}
    repeats: list[tuple[int, int, str]] = []

    for idx, keywords in enumerate(sentence_keywords):
        for kw in keywords:
            if kw in keyword_first:
                first_idx = keyword_first[kw]
                distance = idx - first_idx
                if _MIN_DISTANCE <= distance <= _MAX_DISTANCE:
                    repeats.append((first_idx, idx, kw))
            else:
                keyword_first[kw] = idx

    return repeats


def _deduplicate_pairs(
    pairs: list[tuple[int, int, str]],
    sentences: list[str],
) -> list[SetupPayoff]:
    """중복 쌍을 제거하고 SetupPayoff 객체로 변환한다."""
    seen_pairs: set[tuple[int, int]] = set()
    results: list[SetupPayoff] = []

    # 거리 순으로 정렬 (가까운 것 우선)
    sorted_pairs = sorted(pairs, key=lambda x: x[1] - x[0])

    for setup_idx, payoff_idx, keyword in sorted_pairs:
        pair_key = (setup_idx, payoff_idx)
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)

        results.append(SetupPayoff(
            setup_text=sentences[setup_idx],
            payoff_text=sentences[payoff_idx],
            setup_position=setup_idx,
            payoff_position=payoff_idx,
            distance=payoff_idx - setup_idx,
        ))

    return results


def track_setup_payoff(transcript: str) -> list[SetupPayoff]:
    """자막에서 설정-회수 패턴을 추적한다.

    Args:
        transcript: 자막 텍스트

    Returns:
        SetupPayoff 리스트 (distance 오름차순 정렬)
    """
    if not transcript or not transcript.strip():
        return []

    sentences = _split_sentences(transcript)
    if len(sentences) < _MIN_DISTANCE + 1:
        return []

    repeats = _find_keyword_repeats(sentences)
    if not repeats:
        return []

    results = _deduplicate_pairs(repeats, sentences)

    # 거리 오름차순 정렬
    results.sort(key=lambda sp: sp.distance)
    return results
