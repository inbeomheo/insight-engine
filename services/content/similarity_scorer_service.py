"""
콘텐츠 유사도 측정 서비스

두 콘텐츠 간 유사도를 여러 기준으로 측정합니다.
SequenceMatcher + 키워드 자카드 유사도 기반.
"""
import difflib
import logging
import re
from collections import Counter

logger = logging.getLogger(__name__)

_WORD_PATTERN = re.compile(r'[가-힣]{2,}|[a-zA-Z]{3,}')
_HEADING_PATTERN = re.compile(r'^#{1,6}\s+(.+)$', re.MULTILINE)


def _extract_words(text: str) -> list:
    """단어 목록 추출."""
    return [w.lower() for w in _WORD_PATTERN.findall(text)]


def _jaccard_similarity(set_a: set, set_b: set) -> float:
    """자카드 유사도 계산."""
    if not set_a and not set_b:
        return 1.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


def _cosine_similarity(counter_a: Counter, counter_b: Counter) -> float:
    """코사인 유사도 계산 (단어 빈도 기반)."""
    all_words = set(counter_a.keys()) | set(counter_b.keys())
    if not all_words:
        return 0.0

    dot_product = sum(counter_a.get(w, 0) * counter_b.get(w, 0) for w in all_words)
    mag_a = sum(v ** 2 for v in counter_a.values()) ** 0.5
    mag_b = sum(v ** 2 for v in counter_b.values()) ** 0.5

    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot_product / (mag_a * mag_b)


def score_similarity(content_a: str, content_b: str) -> dict:
    """두 콘텐츠의 유사도를 측정합니다.

    Args:
        content_a: 첫 번째 콘텐츠
        content_b: 두 번째 콘텐츠

    Returns:
        {
            'overall_score': float (0.0~1.0),
            'text_similarity': float,
            'keyword_similarity': float,
            'structure_similarity': float,
            'shared_keywords': [str],
            'unique_to_a': [str],
            'unique_to_b': [str],
            'verdict': str,
        }
    """
    if not content_a or not content_b:
        return _empty_result()

    a_text = content_a.strip()
    b_text = content_b.strip()

    # 1) 텍스트 유사도 (SequenceMatcher)
    text_sim = difflib.SequenceMatcher(None, a_text, b_text).ratio()

    # 2) 키워드 유사도 (자카드 + 코사인)
    words_a = _extract_words(a_text)
    words_b = _extract_words(b_text)
    set_a = set(words_a)
    set_b = set(words_b)
    jaccard = _jaccard_similarity(set_a, set_b)
    cosine = _cosine_similarity(Counter(words_a), Counter(words_b))
    keyword_sim = (jaccard + cosine) / 2

    # 3) 구조 유사도 (헤딩 비교)
    headings_a = _HEADING_PATTERN.findall(a_text)
    headings_b = _HEADING_PATTERN.findall(b_text)
    if headings_a or headings_b:
        heading_set_a = set(h.lower().strip() for h in headings_a)
        heading_set_b = set(h.lower().strip() for h in headings_b)
        structure_sim = _jaccard_similarity(heading_set_a, heading_set_b)
    else:
        structure_sim = 1.0 if (not headings_a and not headings_b) else 0.0

    # 종합 점수 (가중 평균)
    overall = round(text_sim * 0.4 + keyword_sim * 0.4 + structure_sim * 0.2, 4)

    # 공유/고유 키워드
    shared = sorted(set_a & set_b)[:20]
    unique_a = sorted(set_a - set_b)[:10]
    unique_b = sorted(set_b - set_a)[:10]

    # 판정
    if overall >= 0.9:
        verdict = 'nearly_identical'
    elif overall >= 0.7:
        verdict = 'very_similar'
    elif overall >= 0.4:
        verdict = 'somewhat_similar'
    elif overall >= 0.2:
        verdict = 'slightly_similar'
    else:
        verdict = 'different'

    return {
        'overall_score': round(overall, 4),
        'text_similarity': round(text_sim, 4),
        'keyword_similarity': round(keyword_sim, 4),
        'structure_similarity': round(structure_sim, 4),
        'shared_keywords': shared,
        'unique_to_a': unique_a,
        'unique_to_b': unique_b,
        'verdict': verdict,
    }


def _empty_result() -> dict:
    return {
        'overall_score': 0.0,
        'text_similarity': 0.0,
        'keyword_similarity': 0.0,
        'structure_similarity': 0.0,
        'shared_keywords': [],
        'unique_to_a': [],
        'unique_to_b': [],
        'verdict': 'different',
    }
