"""문장 복잡도 평가 (sentence_complexity_scorer)."""
import re
import logging
from typing import Dict, List

from services.analysis.sentence._common import split_sentences

logger = logging.getLogger(__name__)

_KO_CLAUSE_MARKERS = re.compile(
    r'(?:하고|하며|하면|하지만|하여|해서|하니|하는데|인데|는데|지만|면서|거나|든지|으므로|이므로|때문에|으니까|니까|으면서|ㄴ데)',
    re.UNICODE
)
_EN_CLAUSE_MARKERS = re.compile(
    r'\b(?:and|but|or|because|although|while|when|if|since|unless|whereas|however|therefore|moreover|furthermore|nevertheless|yet|so|that|which|who|whom|where)\b',
    re.IGNORECASE
)
_NESTING_OPEN = re.compile(r'[(\[{]')
_NESTING_CLOSE = re.compile(r'[)\]}]')
_COMMA_RE = re.compile(r'[,]')

_COMPLEXITY_EMPTY = {
    'sentences': [],
    'summary': {
        'total_sentences': 0, 'avg_complexity': 0.0,
        'distribution': {}, 'level': 'none',
    },
    'score': 0.0,
    'suggestions': [],
}


def _complexity_score_sentence(sentence: str) -> Dict:
    word_count = len(sentence.split())
    ko_clauses = len(_KO_CLAUSE_MARKERS.findall(sentence))
    en_clauses = len(_EN_CLAUSE_MARKERS.findall(sentence))
    clause_count = ko_clauses + en_clauses + 1

    comma_count = len(_COMMA_RE.findall(sentence))

    max_depth = 0
    depth = 0
    for ch in sentence:
        if _NESTING_OPEN.match(ch):
            depth += 1
            max_depth = max(max_depth, depth)
        elif _NESTING_CLOSE.match(ch):
            depth = max(0, depth - 1)

    complexity = 0.0
    complexity += min(30.0, clause_count * 8.0)
    complexity += min(20.0, comma_count * 5.0)
    complexity += min(20.0, max_depth * 10.0)
    complexity += min(30.0, max(0, word_count - 10) * 1.5)
    complexity = round(min(100.0, complexity), 1)

    if complexity <= 20:
        category = 'simple'
    elif complexity <= 45:
        category = 'moderate'
    elif complexity <= 70:
        category = 'complex'
    else:
        category = 'very_complex'

    return {
        'text': sentence if len(sentence) <= 60 else sentence[:57] + '...',
        'word_count': word_count,
        'clause_count': clause_count,
        'comma_count': comma_count,
        'nesting_depth': max_depth,
        'complexity': complexity,
        'category': category,
    }


def _complexity_compute_stats(scored: list) -> tuple:
    distribution = {'simple': 0, 'moderate': 0, 'complex': 0, 'very_complex': 0}
    total_complexity = 0.0
    for s in scored:
        distribution[s['category']] += 1
        total_complexity += s['complexity']
    avg = round(total_complexity / len(scored), 1)
    if avg <= 25:
        level = 'easy'
    elif avg <= 45:
        level = 'balanced'
    elif avg <= 65:
        level = 'complex'
    else:
        level = 'very_complex'
    return distribution, avg, level


def _complexity_compute_score(avg: float, distribution: dict) -> float:
    if 20 <= avg <= 45:
        score = 100.0
    elif avg < 20:
        score = 70.0 + avg * 1.5
    else:
        score = max(20.0, 100.0 - (avg - 45) * 2.0)
    if sum(1 for v in distribution.values() if v > 0) >= 3:
        score += 5.0
    return round(max(0.0, min(100.0, score)), 1)


def _complexity_generate_suggestions(avg: float, level: str,
                                     dist: Dict, total: int) -> List[str]:
    suggestions = []
    level_labels = {
        'easy': '쉬움', 'balanced': '균형',
        'complex': '복잡', 'very_complex': '매우 복잡',
    }
    suggestions.append(
        f'평균 복잡도 {avg} ({level_labels.get(level, level)}). '
        f'단순 {dist["simple"]}개, 보통 {dist["moderate"]}개, '
        f'복잡 {dist["complex"]}개, 매우 복잡 {dist["very_complex"]}개.'
    )
    if level == 'very_complex':
        suggestions.append('문장이 전반적으로 복잡합니다. 긴 문장을 나누고 접속사를 줄이세요.')
    elif level == 'easy' and total >= 5:
        suggestions.append('문장이 대부분 단순합니다. 복합문이나 종속절을 적절히 사용하면 글의 깊이가 더해집니다.')
    if dist['very_complex'] > total * 0.3:
        suggestions.append(
            f'매우 복잡한 문장이 {dist["very_complex"]}개({round(dist["very_complex"]/total*100)}%)입니다. '
            f'독자 피로를 줄이려면 간결한 문장과 번갈아 배치하세요.'
        )
    return suggestions


def score_sentence_complexity(content: str) -> dict:
    """문장 복잡도를 평가합니다."""
    try:
        if not content or not content.strip():
            return {**_COMPLEXITY_EMPTY, 'suggestions': ['콘텐츠가 비어 있습니다.']}

        sentences = split_sentences(content)
        if not sentences:
            return dict(_COMPLEXITY_EMPTY)

        scored = [_complexity_score_sentence(s) for s in sentences]
        distribution, avg_complexity, level = _complexity_compute_stats(scored)
        score = _complexity_compute_score(avg_complexity, distribution)

        return {
            'sentences': scored[:30],
            'summary': {
                'total_sentences': len(scored),
                'avg_complexity': avg_complexity,
                'distribution': distribution,
                'level': level,
            },
            'score': score,
            'suggestions': _complexity_generate_suggestions(avg_complexity, level, distribution, len(scored)),
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}
