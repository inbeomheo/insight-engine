"""문장 종결어미 다양성 분석 (sentence_ending_variety)."""
import re
import logging
from collections import Counter
from typing import List

from services.analysis.sentence._common import split_sentences

logger = logging.getLogger(__name__)

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

_EN_PERIOD = re.compile(r'\.\s*$')
_EN_QUESTION = re.compile(r'\?\s*$')
_EN_EXCLAIM = re.compile(r'!\s*$')

_ENDING_EMPTY = {
    'ending_data': [],
    'ending_distribution': {},
    'summary': {'total_sentences': 0, 'unique_endings': 0,
                'variety_rate': 0.0, 'dominant_ending': ''},
    'score': 100.0,
    'suggestions': [],
}


def _classify_ending(sentence: str) -> str:
    for name, pattern in _KO_ENDINGS.items():
        if pattern.search(sentence):
            return name
    if _EN_QUESTION.search(sentence):
        return 'question'
    if _EN_EXCLAIM.search(sentence):
        return 'exclamation'
    if _EN_PERIOD.search(sentence):
        return 'period'
    return 'other'


def _ending_classify_all(sentences: List[str]) -> tuple:
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


def _ending_calculate_score(variety: float, dominant_ratio: float,
                            counts: Counter, total: int) -> float:
    if total < 3:
        return 80.0
    score = 100.0
    if dominant_ratio > 80:
        score -= 30.0
    elif dominant_ratio > 70:
        score -= 20.0
    elif dominant_ratio > 60:
        score -= 10.0
    if variety < 20:
        score -= 15.0
    return round(max(0.0, min(100.0, score)), 1)


def _ending_generate_suggestions(dominant: str, ratio: float, variety: float,
                                 counts: Counter) -> List[str]:
    suggestions = []
    if ratio > 70:
        suggestions.append(
            f'종결어미 "{dominant}"가 {ratio}%로 과도합니다. '
            f'다른 어미를 섞어 단조로움을 피하세요.'
        )
    elif ratio > 50:
        suggestions.append(f'종결어미 "{dominant}"가 {ratio}%로 다소 높습니다.')
    else:
        suggestions.append(f'종결어미 다양성 {variety}%로 양호합니다.')

    q_count = counts.get('question', 0) + counts.get('까요', 0)
    if q_count == 0 and sum(counts.values()) >= 5:
        suggestions.append('질문형 문장이 없습니다. 독자 참여를 위해 질문을 추가하세요.')
    return suggestions


def analyze_sentence_ending_variety(content: str) -> dict:
    """문장 종결어미 다양성을 분석합니다."""
    try:
        if not content or not content.strip():
            return dict(_ENDING_EMPTY)

        sentences = split_sentences(content)
        if not sentences:
            return dict(_ENDING_EMPTY)

        ending_data, ending_counts, dominant, dominant_ratio, variety_rate = (
            _ending_classify_all(sentences)
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
            'score': _ending_calculate_score(variety_rate, dominant_ratio, ending_counts, total),
            'suggestions': _ending_generate_suggestions(
                dominant, dominant_ratio, variety_rate, ending_counts
            ),
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}
