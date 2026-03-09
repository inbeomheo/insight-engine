"""
의미 중복 감시 서비스.

콘텐츠 간 의미적 중복을 Jaccard 유사도와 n-gram 기반으로 탐지한다.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DuplicatePair:
    """중복 쌍."""
    content_a_id: str
    content_b_id: str
    similarity: float
    overlap_phrases: list  # list[str] — 겹치는 구절
    recommendation: str  # keep_both / merge / remove_one


def _tokenize(text: str) -> set:
    """텍스트를 단어 집합으로 변환한다."""
    return set(text.lower().split())


def _get_ngrams(text: str, n: int) -> set:
    """n-gram 집합을 반환한다."""
    words = text.lower().split()
    if len(words) < n:
        return set()
    return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}


def calculate_similarity(text_a: str, text_b: str) -> float:
    """Jaccard 유사도를 계산한다 (단어 집합 기반)."""
    set_a = _tokenize(text_a)
    set_b = _tokenize(text_b)

    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0

    intersection = set_a & set_b
    union = set_a | set_b

    return round(len(intersection) / len(union), 4)


def extract_overlap(text_a: str, text_b: str) -> list:
    """겹치는 구절을 추출한다 (3-gram 이상)."""
    # 3-gram 교집합
    ngrams_a = _get_ngrams(text_a, 3)
    ngrams_b = _get_ngrams(text_b, 3)

    common = ngrams_a & ngrams_b

    # 정렬 후 반환
    return sorted(common)


def recommend_action(similarity: float) -> str:
    """유사도별 권고를 반환한다."""
    if similarity > 0.9:
        return "remove_one"
    elif similarity > 0.7:
        return "merge"
    else:
        return "keep_both"


def find_duplicates(
    contents: list,
    threshold: float = 0.5,
) -> list:
    """중복 쌍을 탐지한다.

    Args:
        contents: list[dict] — {id, text} 형태
        threshold: 유사도 임계값 (기본 0.5)
    """
    pairs = []

    for i in range(len(contents)):
        for j in range(i + 1, len(contents)):
            text_a = contents[i].get("text", "")
            text_b = contents[j].get("text", "")
            id_a = contents[i].get("id", f"content_{i}")
            id_b = contents[j].get("id", f"content_{j}")

            sim = calculate_similarity(text_a, text_b)

            if sim >= threshold:
                overlaps = extract_overlap(text_a, text_b)
                rec = recommend_action(sim)

                pairs.append(DuplicatePair(
                    content_a_id=id_a,
                    content_b_id=id_b,
                    similarity=sim,
                    overlap_phrases=overlaps,
                    recommendation=rec,
                ))

    return pairs
