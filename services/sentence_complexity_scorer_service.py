"""
Sentence Complexity Scorer 서비스

문장의 구조적 복잡도를 평가합니다.
절/구 수, 접속사 빈도, 중첩 깊이를 기반으로 복잡도를 산출합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict

_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')
_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)

# 절 구분 표지 (한국어)
_KO_CLAUSE_MARKERS = re.compile(
    r'(?:하고|하며|하면|하지만|하여|해서|하니|하는데|인데|는데|지만|면서|거나|든지|으므로|이므로|때문에|으니까|니까|으면서|ㄴ데)',
    re.UNICODE
)

# 절 구분 표지 (영어)
_EN_CLAUSE_MARKERS = re.compile(
    r'\b(?:and|but|or|because|although|while|when|if|since|unless|whereas|however|therefore|moreover|furthermore|nevertheless|yet|so|that|which|who|whom|where)\b',
    re.IGNORECASE
)

# 괄호/인용 중첩
_NESTING_OPEN = re.compile(r'[(\[{「『""]')
_NESTING_CLOSE = re.compile(r'[)\]}」』""]')

# 쉼표 수
_COMMA_RE = re.compile(r'[,，]')


def _split_sentences(content: str) -> List[str]:
    cleaned = _HEADING_RE.sub('', content)
    raw = _SENTENCE_SPLIT.split(cleaned)
    return [s.strip() for s in raw if s.strip() and len(s.strip()) >= 5]


def _score_sentence(sentence: str) -> Dict:
    """개별 문장의 복잡도를 계산합니다."""
    word_count = len(sentence.split())

    # 절 수 (접속사/연결어미 기반)
    ko_clauses = len(_KO_CLAUSE_MARKERS.findall(sentence))
    en_clauses = len(_EN_CLAUSE_MARKERS.findall(sentence))
    clause_count = ko_clauses + en_clauses + 1  # 최소 1절

    # 쉼표 수
    comma_count = len(_COMMA_RE.findall(sentence))

    # 중첩 깊이
    max_depth = 0
    depth = 0
    for ch in sentence:
        if _NESTING_OPEN.match(ch):
            depth += 1
            max_depth = max(max_depth, depth)
        elif _NESTING_CLOSE.match(ch):
            depth = max(0, depth - 1)

    # 복잡도 점수 (0~100, 높을수록 복잡)
    complexity = 0.0
    complexity += min(30.0, clause_count * 8.0)  # 절 수
    complexity += min(20.0, comma_count * 5.0)    # 쉼표
    complexity += min(20.0, max_depth * 10.0)     # 중첩
    complexity += min(30.0, max(0, word_count - 10) * 1.5)  # 길이

    complexity = round(min(100.0, complexity), 1)

    # 카테고리
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


_EMPTY_RESULT = {
    'sentences': [],
    'summary': {
        'total_sentences': 0, 'avg_complexity': 0.0,
        'distribution': {}, 'level': 'none',
    },
    'score': 0.0,
    'suggestions': [],
}


def _compute_complexity_stats(scored: list) -> tuple:
    """복잡도 분포와 레벨을 계산합니다.

    Returns:
        (distribution, avg_complexity, level)
    """
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


def _compute_complexity_score(avg: float, distribution: dict) -> float:
    """복잡도 점수를 계산합니다."""
    if 20 <= avg <= 45:
        score = 100.0
    elif avg < 20:
        score = 70.0 + avg * 1.5
    else:
        score = max(20.0, 100.0 - (avg - 45) * 2.0)

    if sum(1 for v in distribution.values() if v > 0) >= 3:
        score += 5.0

    return round(max(0.0, min(100.0, score)), 1)


def score_sentence_complexity(content: str) -> dict:
    """문장 복잡도를 평가합니다.

    Returns:
        sentences, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {**_EMPTY_RESULT, 'suggestions': ['콘텐츠가 비어 있습니다.']}

    sentences = _split_sentences(content)
    if not sentences:
        return dict(_EMPTY_RESULT)

    scored = [_score_sentence(s) for s in sentences]
    distribution, avg_complexity, level = _compute_complexity_stats(scored)
    score = _compute_complexity_score(avg_complexity, distribution)

    return {
        'sentences': scored[:30],
        'summary': {
            'total_sentences': len(scored),
            'avg_complexity': avg_complexity,
            'distribution': distribution,
            'level': level,
        },
        'score': score,
        'suggestions': _generate_suggestions(avg_complexity, level, distribution, len(scored)),
    }


def _generate_suggestions(avg: float, level: str,
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
        suggestions.append(
            '문장이 전반적으로 복잡합니다. '
            '긴 문장을 나누고 접속사를 줄이세요.'
        )
    elif level == 'easy' and total >= 5:
        suggestions.append(
            '문장이 대부분 단순합니다. '
            '복합문이나 종속절을 적절히 사용하면 글의 깊이가 더해집니다.'
        )

    if dist['very_complex'] > total * 0.3:
        suggestions.append(
            f'매우 복잡한 문장이 {dist["very_complex"]}개({round(dist["very_complex"]/total*100)}%)입니다. '
            f'독자 피로를 줄이려면 간결한 문장과 번갈아 배치하세요.'
        )

    return suggestions
