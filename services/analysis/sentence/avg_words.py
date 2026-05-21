"""문장당 평균 단어 수 분석 (avg_words_per_sentence)."""
import logging
from typing import List

from services.analysis.sentence._common import split_sentences

logger = logging.getLogger(__name__)

_AVG_WORDS_EMPTY = {
    'sentence_data': [],
    'summary': {'total_sentences': 0, 'total_words': 0,
                'avg_words': 0.0, 'readability_level': 'none'},
    'score': 0.0,
    'suggestions': [],
}


def _avg_words_count(sentence: str) -> int:
    tokens = sentence.split()
    return len([t for t in tokens if len(t) >= 1])


def _avg_words_collect(sentences: List[str]) -> tuple:
    sentence_data = []
    total_words = 0
    long_sentences = 0
    short_sentences = 0
    for sent in sentences:
        wc = _avg_words_count(sent)
        total_words += wc
        if wc > 30:
            length_cat = 'long'
            long_sentences += 1
        elif wc < 5:
            length_cat = 'short'
            short_sentences += 1
        else:
            length_cat = 'normal'
        sentence_data.append({
            'text': sent if len(sent) <= 50 else sent[:47] + '...',
            'word_count': wc,
            'category': length_cat,
        })
    return sentence_data, total_words, long_sentences, short_sentences


def _avg_words_readability(avg: float, long_sentences: int, total: int) -> tuple:
    if 10 <= avg <= 20:
        level = 'optimal'
    elif 5 <= avg < 10 or 20 < avg <= 30:
        level = 'acceptable'
    elif avg < 5:
        level = 'too_short'
    else:
        level = 'too_long'

    optimal_center = 15.0
    deviation = abs(avg - optimal_center)
    if deviation <= 5:
        score = 100.0 - (deviation * 2.0)
    elif deviation <= 10:
        score = 90.0 - ((deviation - 5) ** 1.3 * 4.0)
    else:
        score = max(15.0, 60.0 - ((deviation - 10) ** 1.2 * 3.0))
    if long_sentences > total * 0.3:
        score -= 10.0
    return round(max(0.0, min(100.0, score)), 1), level


def _avg_words_generate_suggestions(avg: float, level: str, long: int,
                                    short: int, total: int) -> List[str]:
    suggestions = []
    level_labels = {
        'optimal': '최적 가독성', 'acceptable': '수용 가능',
        'too_short': '너무 짧음', 'too_long': '너무 길음',
    }
    suggestions.append(
        f'문장당 평균 {avg} 단어 ({level_labels.get(level, level)}). '
        f'권장 범위: 10-20 단어.'
    )
    if level == 'too_long':
        suggestions.append(f'긴 문장 {long}개: 접속사 기준으로 문장을 분리하세요.')
    elif level == 'too_short':
        suggestions.append(f'짧은 문장 {short}개: 구체적 설명을 추가하세요.')
    if long > total * 0.3 and total >= 5:
        suggestions.append(
            f'전체의 {round(long / total * 100)}%가 30단어 이상입니다. '
            f'독자 피로를 유발할 수 있습니다.'
        )
    return suggestions


def analyze_avg_words_per_sentence(content: str) -> dict:
    """문장당 평균 단어 수를 분석합니다."""
    try:
        if not content or not content.strip():
            return {**_AVG_WORDS_EMPTY, 'suggestions': ['콘텐츠가 비어 있습니다.']}

        sentences = split_sentences(content)
        if not sentences:
            return dict(_AVG_WORDS_EMPTY)

        sentence_data, total_words, long_sentences, short_sentences = _avg_words_collect(sentences)
        total = len(sentences)
        avg = round(total_words / total, 1) if total > 0 else 0.0
        score, level = _avg_words_readability(avg, long_sentences, total)

        return {
            'sentence_data': sentence_data[:30],
            'summary': {
                'total_sentences': total, 'total_words': total_words,
                'avg_words': avg, 'readability_level': level,
                'long_sentences': long_sentences, 'short_sentences': short_sentences,
            },
            'score': score,
            'suggestions': _avg_words_generate_suggestions(avg, level, long_sentences, short_sentences, total),
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}
