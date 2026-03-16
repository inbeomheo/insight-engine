"""
Comparison Criteria Completeness Checker 서비스

비교/리뷰 콘텐츠에서 비교 기준이 명시적이고
체계적인지 검사합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

# 비교 콘텐츠 탐지 패턴
_COMPARISON_SIGNAL = [
    re.compile(r'(?:비교|대결|vs\.?|versus)\b', re.IGNORECASE),
    re.compile(r'(?:장단점|장점.*?단점|pros.*?cons)', re.IGNORECASE),
    re.compile(r'(?:리뷰|후기|평가|분석|벤치마크)', re.IGNORECASE),
    re.compile(r'\b(?:compare|comparison|review|benchmark|rating)\b', re.IGNORECASE),
]

# 비교 기준 명시 패턴
_CRITERIA_PATTERNS = {
    'explicit_criteria': {
        'label': '명시적 기준',
        'patterns': [
            re.compile(r'(?:평가\s*기준|비교\s*(?:기준|항목|포인트)|기준\s*(?:항목|표))', re.IGNORECASE),
            re.compile(r'\b(?:criteria|evaluation\s+(?:criteria|factors)|scoring)\b', re.IGNORECASE),
        ],
    },
    'rating_system': {
        'label': '평가 체계',
        'patterns': [
            re.compile(r'(?:\d+\s*(?:점|점\s*만점|/\s*\d+|★|⭐))', re.IGNORECASE),
            re.compile(r'(?:등급|랭킹|순위|점수)', re.IGNORECASE),
            re.compile(r'\b(?:\d+\s*/\s*(?:5|10)|rating|score|rank)\b', re.IGNORECASE),
        ],
    },
    'structured_comparison': {
        'label': '구조화된 비교',
        'patterns': [
            re.compile(r'(?:\|.*?\|.*?\|)', re.MULTILINE),  # 마크다운 테이블
            re.compile(r'(?:항목\s*\|)|(?:기능\s*\|)', re.IGNORECASE),
            re.compile(r'(?:가격|성능|사용성|디자인|기능)\s*:', re.IGNORECASE),
        ],
    },
    'methodology': {
        'label': '방법론 설명',
        'patterns': [
            re.compile(r'(?:테스트\s*(?:방법|환경|조건)|측정\s*(?:방법|기준))', re.IGNORECASE),
            re.compile(r'(?:실제\s*(?:사용|테스트|측정)|직접\s*(?:사용|체험))', re.IGNORECASE),
            re.compile(r'\b(?:methodology|test\s*(?:setup|environment|method))\b', re.IGNORECASE),
        ],
    },
    'weighting': {
        'label': '가중치/우선순위',
        'patterns': [
            re.compile(r'(?:가중치|우선순위|중요도|비중)', re.IGNORECASE),
            re.compile(r'\b(?:weight|priority|importance|emphasis)\b', re.IGNORECASE),
        ],
    },
}


def _has_pattern(content: str, patterns: list) -> bool:
    return any(p.search(content) for p in patterns)


_EMPTY_RESULT = {
    'score': 100.0,
    'summary': {
        'is_comparison_content': False, 'criteria_categories': 0,
        'criteria_found': [], 'completeness_ratio': 0.0, 'level': 'none',
    },
    'criteria_details': [],
    'suggestions': [],
}


def _scan_criteria(content: str) -> tuple:
    """비교 기준 카테고리를 스캔합니다.

    Returns:
        (criteria_details, found_categories)
    """
    found_categories = []
    criteria_details = []
    for cat_name, cat_info in _CRITERIA_PATTERNS.items():
        has = _has_pattern(content, cat_info['patterns'])
        criteria_details.append({
            'category': cat_name, 'label': cat_info['label'], 'found': has,
        })
        if has:
            found_categories.append(cat_name)
    return criteria_details, found_categories


def _compute_completeness_level(found_count: int) -> str:
    """충족 카테고리 수로 완전성 레벨을 결정합니다."""
    if found_count >= 4:
        return 'comprehensive'
    elif found_count >= 3:
        return 'good'
    elif found_count >= 2:
        return 'partial'
    elif found_count >= 1:
        return 'minimal'
    return 'missing'


def check_comparison_criteria_completeness(content: str) -> dict:
    """비교 콘텐츠의 기준 명시 완전성을 검사합니다.

    Returns:
        score, summary, criteria_found, suggestions를 포함하는 dict
    """
    try:
        if not content or not content.strip():
            return dict(_EMPTY_RESULT)

        if not _has_pattern(content, _COMPARISON_SIGNAL):
            return dict(_EMPTY_RESULT)

        criteria_details, found_categories = _scan_criteria(content)
        found_count = len(found_categories)
        total_categories = len(_CRITERIA_PATTERNS)
        completeness = round(found_count / total_categories * 100, 1)
        level = _compute_completeness_level(found_count)
        score = round(max(0.0, min(100.0, 15.0 + (found_count / total_categories * 85.0))), 1)

        return {
            'score': score,
            'summary': {
                'is_comparison_content': True, 'criteria_categories': found_count,
                'criteria_found': found_categories,
                'completeness_ratio': completeness, 'level': level,
            },
            'criteria_details': criteria_details,
            'suggestions': _generate_suggestions(
                found_categories, criteria_details, completeness, level
            ),
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}


def _generate_suggestions(found: List[str], details: List[Dict],
                           completeness: float, level: str) -> List[str]:
    suggestions = []

    level_labels = {
        'none': '해당 없음', 'comprehensive': '포괄적',
        'good': '양호', 'partial': '부분적',
        'minimal': '최소', 'missing': '없음',
    }
    suggestions.append(
        f'비교 기준 완전성: {level_labels.get(level, level)} '
        f'({completeness}%).'
    )

    missing = [d for d in details if not d['found']]
    if missing:
        labels = ', '.join(d['label'] for d in missing[:3])
        suggestions.append(
            f'누락된 비교 요소: {labels}. 추가하면 신뢰도가 높아집니다.'
        )

    if 'explicit_criteria' not in found:
        suggestions.append(
            '"평가 기준" 또는 "비교 항목" 섹션을 추가하세요.'
        )

    if 'methodology' not in found:
        suggestions.append(
            '테스트 방법이나 평가 환경을 명시하세요.'
        )

    return suggestions
