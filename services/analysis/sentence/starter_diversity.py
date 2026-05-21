"""문장 시작어 다양성 분석 (sentence_starter_diversity)."""
import logging
from collections import Counter
from typing import List

from services.analysis.sentence._common import split_sentences

logger = logging.getLogger(__name__)

_STARTER_EMPTY = {
    'starter_data': [],
    'summary': {
        'total_sentences': 0, 'unique_starters': 0,
        'diversity_ratio': 0.0, 'consecutive_repeats': 0, 'level': 'none',
    },
    'score': 0.0,
    'suggestions': [],
}


def _get_starter(sentence: str) -> str:
    tokens = sentence.split()
    if not tokens:
        return ''
    return tokens[0].lower().strip('\"\'([{')


def _starter_analyze(starters: list, total: int) -> tuple:
    starter_counter = Counter(starters)
    diversity_ratio = round(len(starter_counter) / max(total, 1) * 100, 1)
    consecutive_repeats = 0
    for i in range(1, len(starters)):
        if starters[i] == starters[i - 1] and starters[i]:
            consecutive_repeats += 1
    starter_data = [
        {'starter': word, 'count': count, 'ratio': round(count / total * 100, 1)}
        for word, count in starter_counter.most_common(15)
    ]
    return starter_counter, diversity_ratio, consecutive_repeats, starter_data


def _starter_compute_score(diversity_ratio: float, consecutive_repeats: int) -> tuple:
    if diversity_ratio >= 70:
        level = 'diverse'
    elif diversity_ratio >= 50:
        level = 'moderate'
    elif diversity_ratio >= 30:
        level = 'repetitive'
    else:
        level = 'very_repetitive'
    score = min(100.0, diversity_ratio * 1.3)
    if consecutive_repeats > 0:
        score -= min(20.0, consecutive_repeats * 5.0)
    return round(max(0.0, min(100.0, score)), 1), level


def _starter_generate_suggestions(counter: Counter, ratio: float, level: str,
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
    overused = [(w, c) for w, c in counter.most_common(3) if c >= 3]
    if overused:
        words = ', '.join([f'"{w}" ({c}회)' for w, c in overused])
        suggestions.append(f'과다 사용 시작어: {words}.')
    return suggestions


def analyze_sentence_starter_diversity(content: str) -> dict:
    """문장 시작어 다양성을 분석합니다."""
    try:
        if not content or not content.strip():
            return {**_STARTER_EMPTY, 'suggestions': ['콘텐츠가 비어 있습니다.']}

        sentences = split_sentences(content)
        if not sentences:
            return dict(_STARTER_EMPTY)

        starters = [_get_starter(s) for s in sentences]
        total = len(starters)
        starter_counter, diversity_ratio, consec, starter_data = _starter_analyze(starters, total)
        score, level = _starter_compute_score(diversity_ratio, consec)

        return {
            'starter_data': starter_data,
            'summary': {
                'total_sentences': total,
                'unique_starters': len(starter_counter),
                'diversity_ratio': diversity_ratio,
                'consecutive_repeats': consec,
                'level': level,
            },
            'score': score,
            'suggestions': _starter_generate_suggestions(
                starter_counter, diversity_ratio, level, consec, total
            ),
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}
