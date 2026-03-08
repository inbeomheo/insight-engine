"""
문장 다양성 분석 서비스

문장 길이, 구조, 시작 패턴의 다양성을 분석하여
단조로운 글쓰기를 개선하는 인사이트를 제공합니다.
"""
import re
import logging
import math

logger = logging.getLogger(__name__)

# 문장 길이 분류
_LENGTH_CATEGORIES = {
    'very_short': (0, 15),     # ~15자
    'short': (16, 30),         # 16~30자
    'medium': (31, 60),        # 31~60자
    'long': (61, 100),         # 61~100자
    'very_long': (101, 9999),  # 100자+
}


_EMPTY_RESULT = {
    'sentences': [],
    'length_distribution': {},
    'start_pattern': {'unique_ratio': 0, 'repeated': []},
    'variety_score': 0,
    'stats': {'count': 0, 'avg_length': 0, 'std_dev': 0,
              'min_length': 0, 'max_length': 0},
    'suggestions': [],
}


def _analyze_sentences(sentences: list) -> tuple:
    """문장별 길이/카테고리/시작 단어를 분석합니다.

    Returns:
        (analyzed, lengths, start_words, length_dist)
    """
    analyzed = []
    lengths = []
    start_words = []
    length_dist = {cat: 0 for cat in _LENGTH_CATEGORIES}

    for sent in sentences:
        length = len(sent)
        lengths.append(length)
        category = _categorize_length(length)
        length_dist[category] += 1

        start_match = re.match(r'([가-힣]{1,6})', sent)
        start_word = start_match.group(1) if start_match else sent[:3]
        start_words.append(start_word)

        analyzed.append({
            'text': sent[:80] + '...' if len(sent) > 80 else sent,
            'length': length,
            'category': category,
            'start_word': start_word,
        })

    return analyzed, lengths, start_words, length_dist


def _analyze_start_patterns(start_words: list, count: int) -> tuple:
    """시작 단어 반복 패턴을 분석합니다.

    Returns:
        (unique_ratio, repeated)
    """
    unique_ratio = round(len(set(start_words)) / count, 2)
    start_freq = {}
    for w in start_words:
        start_freq[w] = start_freq.get(w, 0) + 1
    repeated = [{'word': w, 'count': c} for w, c in start_freq.items() if c >= 3]
    repeated.sort(key=lambda x: x['count'], reverse=True)
    return unique_ratio, repeated


def analyze_variety(content: str) -> dict:
    """문장 다양성을 분석합니다.

    Args:
        content: 분석할 콘텐츠

    Returns:
        sentences, length_distribution, start_pattern, variety_score, stats, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {**_EMPTY_RESULT, 'suggestions': ['콘텐츠가 비어 있습니다.']}

    clean = re.sub(r'#{1,6}\s+', '', content)
    clean = re.sub(r'```[\s\S]*?```', '', clean)
    clean = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', clean)

    raw_sentences = re.split(r'(?<=[.!?。])\s+|\n+', clean)
    sentences = [s.strip() for s in raw_sentences if len(s.strip()) >= 5]

    if not sentences:
        return {**_EMPTY_RESULT, 'suggestions': ['분석할 문장이 없습니다.']}

    analyzed, lengths, start_words, length_dist = _analyze_sentences(sentences)

    count = len(lengths)
    avg_length = sum(lengths) / count
    variance = sum((l - avg_length) ** 2 for l in lengths) / count
    std_dev = round(math.sqrt(variance), 1)

    unique_ratio, repeated = _analyze_start_patterns(start_words, count)
    variety_score = _calculate_variety_score(length_dist, count, unique_ratio, std_dev, avg_length)
    suggestions = _generate_suggestions(length_dist, count, unique_ratio, repeated, avg_length)

    return {
        'sentences': analyzed,
        'length_distribution': length_dist,
        'start_pattern': {'unique_ratio': unique_ratio, 'repeated': repeated},
        'variety_score': variety_score,
        'stats': {
            'count': count, 'avg_length': round(avg_length, 1),
            'std_dev': std_dev, 'min_length': min(lengths),
            'max_length': max(lengths),
        },
        'suggestions': suggestions,
    }


def _categorize_length(length: int) -> str:
    for cat, (lo, hi) in _LENGTH_CATEGORIES.items():
        if lo <= length <= hi:
            return cat
    return 'very_long'


def _calculate_variety_score(dist: dict, count: int, unique_ratio: float, std_dev: float, avg: float) -> int:
    """문장 다양성 점수 (0~100)."""
    if count <= 1:
        return 100

    score = 30

    # 길이 분포 다양성: 3개 이상 카테고리에 분포
    used_cats = sum(1 for v in dist.values() if v > 0)
    if used_cats >= 4:
        score += 25
    elif used_cats >= 3:
        score += 20
    elif used_cats >= 2:
        score += 10

    # 시작 단어 다양성
    if unique_ratio >= 0.7:
        score += 20
    elif unique_ratio >= 0.5:
        score += 10
    elif unique_ratio >= 0.3:
        score += 5

    # 표준편차: 적절한 변동성 (너무 낮으면 단조, 너무 높으면 불안정)
    cv = std_dev / max(avg, 1)
    if 0.3 <= cv <= 0.7:
        score += 15  # 적절한 변동
    elif 0.2 <= cv <= 0.8:
        score += 10
    elif cv < 0.15:
        score += 0   # 너무 균일

    # 극단적 편중 페널티
    dominant = max(dist.values())
    if dominant / count > 0.7:
        score -= 10

    return max(0, min(100, score))


def _generate_suggestions(dist: dict, count: int, unique_ratio: float, repeated: list, avg: float) -> list:
    suggestions = []

    if count <= 2:
        suggestions.append('문장이 너무 적어 다양성 분석이 제한적입니다.')
        return suggestions

    # 길이 편중
    used_cats = sum(1 for v in dist.values() if v > 0)
    if used_cats <= 2:
        suggestions.append('문장 길이가 편중되어 있습니다. 짧은 문장과 긴 문장을 섞어 리듬감을 만드세요.')

    if dist.get('very_long', 0) > count * 0.3:
        suggestions.append('긴 문장이 많습니다. 핵심 포인트는 짧은 문장으로 강조하세요.')

    if dist.get('very_short', 0) > count * 0.4:
        suggestions.append('짧은 문장이 많습니다. 설명이 필요한 부분은 좀 더 길게 서술하세요.')

    # 시작 패턴 반복
    if unique_ratio < 0.4:
        suggestions.append('문장 시작이 반복적입니다. 다양한 표현으로 시작해 보세요.')

    if repeated:
        top = repeated[0]
        suggestions.append(f'"{top["word"]}"(으)로 시작하는 문장이 {top["count"]}개입니다. 다른 표현을 시도하세요.')

    if not suggestions:
        suggestions.append('문장 다양성이 양호합니다.')

    return suggestions
