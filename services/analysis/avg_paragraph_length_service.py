"""
Average Paragraph Length 서비스

단락의 평균 길이를 분석합니다.
최적 단락 길이(3-7 문장, 50-150 단어)를 기준으로 평가합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List

_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)
_PARAGRAPH_SPLIT = re.compile(r'\n\s*\n')
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+')


def _split_paragraphs(content: str) -> List[str]:
    """콘텐츠를 단락으로 분할합니다."""
    cleaned = _HEADING_RE.sub('', content)
    paragraphs = _PARAGRAPH_SPLIT.split(cleaned)
    return [p.strip() for p in paragraphs if p.strip() and len(p.strip()) >= 10]


_EMPTY_RESULT = {
    'paragraph_data': [],
    'summary': {
        'total_paragraphs': 0, 'avg_words': 0.0,
        'avg_sentences': 0.0, 'level': 'none',
    },
    'score': 0.0,
    'suggestions': [],
}


def _classify_paragraphs(paragraphs: List[str]) -> tuple:
    """단락별 단어/문장 수를 분류합니다.

    Returns:
        (paragraph_data, long_paras, short_paras, total_words, total_sentences)
    """
    paragraph_data = []
    total_words = 0
    total_sentences = 0
    long_paras = 0
    short_paras = 0

    for p in paragraphs:
        words = len(p.split())
        sentences = max(len([s for s in _SENTENCE_SPLIT.split(p) if s.strip()]), 1)
        total_words += words
        total_sentences += sentences

        if words > 150:
            category = 'long'
            long_paras += 1
        elif words < 30:
            category = 'short'
            short_paras += 1
        else:
            category = 'normal'

        paragraph_data.append({
            'preview': p[:50] + '...' if len(p) > 50 else p,
            'word_count': words, 'sentence_count': sentences, 'category': category,
        })

    return paragraph_data, long_paras, short_paras, total_words, total_sentences


def _compute_paragraph_score(avg_words: float, paragraph_data: list,
                              long_paras: int, short_paras: int, total: int) -> tuple:
    """평균 단어 수 기반으로 점수와 레벨을 계산합니다.

    Returns:
        (score, level)
    """
    if 50 <= avg_words <= 150:
        level = 'optimal'
    elif 30 <= avg_words < 50 or 150 < avg_words <= 200:
        level = 'acceptable'
    elif avg_words < 30:
        level = 'too_short'
    else:
        level = 'too_long'

    deviation = abs(avg_words - 100.0)
    if 50 <= avg_words <= 150:
        score = 100.0 - (deviation * 0.2)
    else:
        score = max(20.0, 100.0 - (deviation * 0.5))

    if total >= 2:
        word_counts = [pd['word_count'] for pd in paragraph_data]
        mean_wc = sum(word_counts) / len(word_counts)
        if mean_wc > 0:
            variance = sum((w - mean_wc) ** 2 for w in word_counts) / len(word_counts)
            cv = (variance ** 0.5) / mean_wc
            score -= min(15.0, cv * 15.0)

    if long_paras > total * 0.3:
        score -= 10.0
    if short_paras > total * 0.5:
        score -= 10.0

    return round(max(0.0, min(100.0, score)), 1), level


def analyze_avg_paragraph_length(content: str) -> dict:
    """단락 평균 길이를 분석합니다.

    Returns:
        paragraph_data, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {**_EMPTY_RESULT, 'suggestions': ['콘텐츠가 비어 있습니다.']}

    paragraphs = _split_paragraphs(content)
    if not paragraphs:
        return dict(_EMPTY_RESULT)

    paragraph_data, long_paras, short_paras, total_words, total_sentences = _classify_paragraphs(paragraphs)
    total = len(paragraphs)
    avg_words = round(total_words / total, 1)
    avg_sentences = round(total_sentences / total, 1)

    score, level = _compute_paragraph_score(avg_words, paragraph_data, long_paras, short_paras, total)
    suggestions = _generate_suggestions(avg_words, avg_sentences, level, long_paras, short_paras, total)

    return {
        'paragraph_data': paragraph_data[:20],
        'summary': {
            'total_paragraphs': total, 'avg_words': avg_words,
            'avg_sentences': avg_sentences, 'long_paragraphs': long_paras,
            'short_paragraphs': short_paras, 'level': level,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _generate_suggestions(avg_words: float, avg_sent: float, level: str,
                           long: int, short: int, total: int) -> List[str]:
    suggestions = []
    level_labels = {
        'optimal': '최적', 'acceptable': '수용 가능',
        'too_short': '너무 짧음', 'too_long': '너무 길음',
    }

    suggestions.append(
        f'단락 평균 {avg_words} 단어, {avg_sent} 문장 '
        f'({level_labels.get(level, level)}). '
        f'권장: 50-150 단어.'
    )

    if level == 'too_long':
        suggestions.append(
            f'긴 단락 {long}개: 주제 전환 지점에서 단락을 나누세요.'
        )
    elif level == 'too_short':
        suggestions.append(
            f'짧은 단락 {short}개: 관련 문장을 묶어 단락을 보강하세요.'
        )

    if long > 0 and short > 0:
        suggestions.append(
            '단락 길이가 불균일합니다. 균일한 길이로 조정하면 읽기 편해집니다.'
        )

    return suggestions
