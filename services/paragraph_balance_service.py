"""
문단 균형 분석 서비스

문단 길이 분포, 균일성, 이상값을 분석하고
가독성 향상을 위한 문단 구조 개선 제안을 제공합니다.
"""
import re
import logging
import math

logger = logging.getLogger(__name__)

# 적정 문단 길이 (글자수 기준)
_OPTIMAL_MIN = 50   # 최소
_OPTIMAL_MAX = 300  # 최대
_IDEAL_MIN = 80
_IDEAL_MAX = 200


_EMPTY_RESULT = {
    'paragraphs': [],
    'stats': {'count': 0, 'avg_length': 0, 'min_length': 0,
              'max_length': 0, 'std_dev': 0},
    'balance_score': 0,
    'issues': [],
    'suggestions': [],
}


def _classify_paragraphs(paragraphs: list, lengths: list) -> tuple:
    """문단별 상태를 분류하고 이슈를 수집합니다.

    Returns:
        (para_results, issues)
    """
    para_results = []
    issues = []

    for idx, (para, length) in enumerate(zip(paragraphs, lengths)):
        preview = para[:60] + '...' if len(para) > 60 else para

        if length < _OPTIMAL_MIN:
            status = 'too_short'
            issues.append({
                'type': 'too_short', 'paragraph': idx,
                'message': f'{idx+1}번째 문단이 너무 짧습니다 ({length}자). 앞뒤 문단과 병합을 고려하세요.',
            })
        elif length > _OPTIMAL_MAX:
            status = 'too_long'
            issues.append({
                'type': 'too_long', 'paragraph': idx,
                'message': f'{idx+1}번째 문단이 너무 깁니다 ({length}자). 분할을 고려하세요.',
            })
        elif _IDEAL_MIN <= length <= _IDEAL_MAX:
            status = 'ideal'
        else:
            status = 'acceptable'

        para_results.append({
            'index': idx, 'length': length,
            'status': status, 'preview': preview,
        })

    return para_results, issues


def analyze_balance(content: str) -> dict:
    """문단 길이 균형을 분석합니다.

    Returns:
        paragraphs, stats, balance_score, issues, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {**_EMPTY_RESULT, 'suggestions': ['콘텐츠가 비어 있습니다.']}

    clean = re.sub(r'#{1,6}\s+', '', content)
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', clean) if len(p.strip()) >= 3]

    if not paragraphs:
        paragraphs = [p.strip() for p in clean.split('\n') if len(p.strip()) >= 3]

    if not paragraphs:
        return {**_EMPTY_RESULT, 'suggestions': ['문단을 감지할 수 없습니다.']}

    lengths = [len(p) for p in paragraphs]
    avg_len = sum(lengths) / len(lengths)
    variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
    std_dev = round(math.sqrt(variance), 1)

    para_results, issues = _classify_paragraphs(paragraphs, lengths)
    balance_score = _calculate_balance_score(lengths, avg_len, std_dev, issues)
    suggestions = _generate_suggestions(lengths, avg_len, std_dev, issues, len(paragraphs))

    return {
        'paragraphs': para_results,
        'stats': {
            'count': len(paragraphs), 'avg_length': round(avg_len, 1),
            'min_length': min(lengths), 'max_length': max(lengths),
            'std_dev': std_dev,
        },
        'balance_score': balance_score,
        'issues': issues,
        'suggestions': suggestions,
    }


def _calculate_balance_score(lengths: list, avg: float, std_dev: float, issues: list) -> int:
    """문단 균형 점수를 계산합니다 (0~100)."""
    score = 70  # 기본

    # 평균 길이가 적정 범위
    if _IDEAL_MIN <= avg <= _IDEAL_MAX:
        score += 15
    elif _OPTIMAL_MIN <= avg <= _OPTIMAL_MAX:
        score += 5

    # 변동 계수 (CV) — 낮을수록 균일
    cv = std_dev / max(avg, 1)
    if cv < 0.3:
        score += 15  # 매우 균일
    elif cv < 0.5:
        score += 5
    elif cv > 1.0:
        score -= 15  # 매우 불균일

    # 이슈 감점
    score -= len(issues) * 5

    return max(0, min(100, score))


def _generate_suggestions(lengths: list, avg: float, std_dev: float, issues: list, count: int) -> list:
    """분석 결과에 따른 개선 제안."""
    suggestions = []

    if count <= 1:
        suggestions.append('문단이 1개뿐입니다. 내용을 여러 문단으로 나누면 가독성이 향상됩니다.')
        return suggestions

    short_count = sum(1 for l in lengths if l < _OPTIMAL_MIN)
    long_count = sum(1 for l in lengths if l > _OPTIMAL_MAX)

    if short_count > count * 0.3:
        suggestions.append(f'짧은 문단({short_count}개)이 많습니다. 인접 문단과 병합하거나 내용을 보충하세요.')

    if long_count > 0:
        suggestions.append(f'긴 문단({long_count}개)이 있습니다. 핵심 논점별로 분할하면 읽기 쉬워집니다.')

    cv = std_dev / max(avg, 1)
    if cv > 0.7:
        suggestions.append('문단 길이 편차가 큽니다. 비슷한 길이로 조정하면 시각적 리듬감이 좋아집니다.')

    if avg > _OPTIMAL_MAX:
        suggestions.append(f'평균 문단 길이({avg:.0f}자)가 깁니다. {_IDEAL_MIN}~{_IDEAL_MAX}자를 권장합니다.')
    elif avg < _OPTIMAL_MIN:
        suggestions.append(f'평균 문단 길이({avg:.0f}자)가 짧습니다. 더 풍부한 서술을 추가하세요.')

    if not suggestions:
        suggestions.append('문단 구조가 균형 잡혀 있습니다.')

    return suggestions
