"""
Sentence Ending Variety 서비스

문장 종결어미의 다양성을 분석합니다.
한국어: ~합니다/~입니다/~됩니다 등의 반복을 감지합니다.
영어: 마침표/물음표/느낌표 비율을 분석합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from collections import Counter
from typing import List

_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')
_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)

# 한국어 종결어미 패턴
_KO_ENDINGS = {
    '합니다': re.compile(r'합니다[.!?]?\s*$'),
    '입니다': re.compile(r'입니다[.!?]?\s*$'),
    '됩니다': re.compile(r'됩니다[.!?]?\s*$'),
    '있습니다': re.compile(r'있습니다[.!?]?\s*$'),
    '없습니다': re.compile(r'없습니다[.!?]?\s*$'),
    '했습니다': re.compile(r'했습니다[.!?]?\s*$'),
    '세요': re.compile(r'세요[.!?]?\s*$'),
    '해요': re.compile(r'해요[.!?]?\s*$'),
    '네요': re.compile(r'네요[.!?]?\s*$'),
    '까요': re.compile(r'까요[.!?]?\s*$'),
    '다': re.compile(r'(?:이다|한다|된다|있다|없다)[.!?]?\s*$'),
}

# 영어 종결 부호
_EN_PERIOD = re.compile(r'\.\s*$')
_EN_QUESTION = re.compile(r'\?\s*$')
_EN_EXCLAIM = re.compile(r'!\s*$')


def _split_sentences(content: str) -> List[str]:
    cleaned = _HEADING_RE.sub('', content)
    raw = _SENTENCE_SPLIT.split(cleaned)
    return [s.strip() for s in raw if s.strip() and len(s.strip()) >= 5]


def _classify_ending(sentence: str) -> str:
    """문장의 종결어미를 분류합니다."""
    # 한국어 종결어미
    for name, pattern in _KO_ENDINGS.items():
        if pattern.search(sentence):
            return name

    # 영어 종결부호
    if _EN_QUESTION.search(sentence):
        return 'question'
    if _EN_EXCLAIM.search(sentence):
        return 'exclamation'
    if _EN_PERIOD.search(sentence):
        return 'period'

    return 'other'


_EMPTY_RESULT = {
    'ending_data': [],
    'ending_distribution': {},
    'summary': {'total_sentences': 0, 'unique_endings': 0,
                'variety_rate': 0.0, 'dominant_ending': ''},
    'score': 100.0,
    'suggestions': [],
}


def _classify_all_endings(sentences: List[str]) -> tuple:
    """모든 문장의 종결어미를 분류합니다.

    Returns:
        (ending_data, ending_counts, dominant, dominant_ratio, variety_rate)
    """
    ending_data = []
    ending_counts = Counter()

    for sent in sentences:
        ending = _classify_ending(sent)
        ending_counts[ending] += 1
        ending_data.append({
            'text': sent if len(sent) <= 50 else sent[:47] + '...',
            'ending': ending,
        })

    total = len(sentences)
    unique = len(ending_counts)
    variety_rate = round(unique / total * 100, 1) if total > 0 else 0.0

    dominant = ending_counts.most_common(1)[0][0] if ending_counts else ''
    dominant_ratio = round(
        ending_counts[dominant] / total * 100, 1
    ) if dominant and total > 0 else 0.0

    return ending_data, ending_counts, dominant, dominant_ratio, variety_rate


def analyze_sentence_ending_variety(content: str) -> dict:
    """문장 종결어미 다양성을 분석합니다.

    Returns:
        ending_data, ending_distribution, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return dict(_EMPTY_RESULT)

    sentences = _split_sentences(content)
    if not sentences:
        return dict(_EMPTY_RESULT)

    ending_data, ending_counts, dominant, dominant_ratio, variety_rate = (
        _classify_all_endings(sentences)
    )
    total = len(sentences)

    return {
        'ending_data': ending_data[:30],
        'ending_distribution': dict(ending_counts),
        'summary': {
            'total_sentences': total,
            'unique_endings': len(ending_counts),
            'variety_rate': variety_rate,
            'dominant_ending': dominant,
        },
        'score': _calculate_score(variety_rate, dominant_ratio, ending_counts, total),
        'suggestions': _generate_suggestions(
            dominant, dominant_ratio, variety_rate, ending_counts
        ),
    }


def _calculate_score(variety: float, dominant_ratio: float,
                     counts: Counter, total: int) -> float:
    if total < 3:
        return 80.0

    score = 100.0

    # 지배적 종결어미가 70% 이상이면 감점
    if dominant_ratio > 80:
        score -= 30.0
    elif dominant_ratio > 70:
        score -= 20.0
    elif dominant_ratio > 60:
        score -= 10.0

    # 다양성 보너스
    if variety < 20:
        score -= 15.0

    # 3회 이상 연속 동일 종결어미 감점
    return round(max(0.0, min(100.0, score)), 1)


def _generate_suggestions(dominant: str, ratio: float, variety: float,
                           counts: Counter) -> List[str]:
    suggestions = []

    if ratio > 70:
        suggestions.append(
            f'종결어미 "{dominant}"가 {ratio}%로 과도합니다. '
            f'다른 어미를 섞어 단조로움을 피하세요.'
        )
    elif ratio > 50:
        suggestions.append(
            f'종결어미 "{dominant}"가 {ratio}%로 다소 높습니다.'
        )
    else:
        suggestions.append(f'종결어미 다양성 {variety}%로 양호합니다.')

    # 질문 부족
    q_count = counts.get('question', 0) + counts.get('까요', 0)
    if q_count == 0 and sum(counts.values()) >= 5:
        suggestions.append('질문형 문장이 없습니다. 독자 참여를 위해 질문을 추가하세요.')

    return suggestions
