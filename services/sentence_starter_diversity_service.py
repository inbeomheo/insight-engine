"""
Sentence Starter Diversity 서비스

문장 시작어의 다양성을 분석합니다.
같은 단어로 시작하는 문장이 연속되면 단조로운 글이 됩니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List
from collections import Counter

_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')
_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)


def _split_sentences(content: str) -> List[str]:
    cleaned = _HEADING_RE.sub('', content)
    raw = _SENTENCE_SPLIT.split(cleaned)
    return [s.strip() for s in raw if s.strip() and len(s.strip()) >= 5]


def _get_starter(sentence: str) -> str:
    """문장의 시작 단어를 추출합니다."""
    tokens = sentence.split()
    if not tokens:
        return ''
    return tokens[0].lower().strip('\"\'([{')


def analyze_sentence_starter_diversity(content: str) -> dict:
    """문장 시작어 다양성을 분석합니다.

    Returns:
        starter_data, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'starter_data': [],
            'summary': {
                'total_sentences': 0,
                'unique_starters': 0,
                'diversity_ratio': 0.0,
                'consecutive_repeats': 0,
                'level': 'none',
            },
            'score': 0.0,
            'suggestions': ['콘텐츠가 비어 있습니다.'],
        }

    sentences = _split_sentences(content)
    if not sentences:
        return {
            'starter_data': [],
            'summary': {
                'total_sentences': 0,
                'unique_starters': 0,
                'diversity_ratio': 0.0,
                'consecutive_repeats': 0,
                'level': 'none',
            },
            'score': 0.0,
            'suggestions': [],
        }

    starters = [_get_starter(s) for s in sentences]
    starter_counter = Counter(starters)
    unique_count = len(starter_counter)
    total = len(starters)

    diversity_ratio = round(unique_count / max(total, 1) * 100, 1)

    # 연속 반복 감지
    consecutive_repeats = 0
    for i in range(1, len(starters)):
        if starters[i] == starters[i - 1] and starters[i]:
            consecutive_repeats += 1

    # 시작어 빈도 데이터
    starter_data = [
        {'starter': word, 'count': count, 'ratio': round(count / total * 100, 1)}
        for word, count in starter_counter.most_common(15)
    ]

    # 레벨
    if diversity_ratio >= 70:
        level = 'diverse'
    elif diversity_ratio >= 50:
        level = 'moderate'
    elif diversity_ratio >= 30:
        level = 'repetitive'
    else:
        level = 'very_repetitive'

    # 점수
    score = min(100.0, diversity_ratio * 1.3)

    # 연속 반복 감점
    if consecutive_repeats > 0:
        score -= min(20.0, consecutive_repeats * 5.0)

    score = round(max(0.0, min(100.0, score)), 1)

    suggestions = _generate_suggestions(
        starter_counter, diversity_ratio, level, consecutive_repeats, total
    )

    return {
        'starter_data': starter_data,
        'summary': {
            'total_sentences': total,
            'unique_starters': unique_count,
            'diversity_ratio': diversity_ratio,
            'consecutive_repeats': consecutive_repeats,
            'level': level,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _generate_suggestions(counter: Counter, ratio: float, level: str,
                           consec: int, total: int) -> List[str]:
    suggestions = []
    level_labels = {
        'diverse': '다양', 'moderate': '보통',
        'repetitive': '반복적', 'very_repetitive': '매우 반복적',
    }

    suggestions.append(
        f'시작어 다양성 {ratio}% ({level_labels.get(level, level)}). '
        f'총 {total}문장, 고유 시작어 {len(counter)}개.'
    )

    if consec > 0:
        suggestions.append(
            f'연속으로 같은 단어로 시작하는 문장이 {consec}쌍 있습니다. '
            f'문장 구조를 다양하게 바꾸세요.'
        )

    # 과다 사용 시작어
    overused = [(w, c) for w, c in counter.most_common(3) if c >= 3]
    if overused:
        words = ', '.join([f'"{w}" ({c}회)' for w, c in overused])
        suggestions.append(f'과다 사용 시작어: {words}.')

    return suggestions
