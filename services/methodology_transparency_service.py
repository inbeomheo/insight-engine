"""
Methodology Transparency Checker 서비스

콘텐츠의 주장이나 결론이 어떤 방법론/과정을 통해
도출되었는지 투명하게 밝히고 있는지 검사합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict

# 방법론 투명성 카테고리
_METHODOLOGY_CATEGORIES = {
    'data_source': {
        'label': '데이터 출처',
        'patterns': [
            re.compile(r'(?:데이터\s*(?:출처|소스|수집|원본))', re.IGNORECASE),
            re.compile(r'(?:조사\s*(?:대상|범위|기간|방법))', re.IGNORECASE),
            re.compile(r'\b(?:data\s*(?:source|collection|from)|sourced?\s+from)\b', re.IGNORECASE),
        ],
    },
    'sample_info': {
        'label': '표본 정보',
        'patterns': [
            re.compile(r'(?:표본\s*(?:크기|수|규모)|샘플\s*(?:크기|수))', re.IGNORECASE),
            re.compile(r'(?:응답자\s*\d|참여자\s*\d|\d+\s*(?:명|건|개)\s*(?:대상|표본|샘플))', re.IGNORECASE),
            re.compile(r'\b(?:sample\s*(?:size|of)|(?:n|N)\s*=\s*\d+|respondents?)\b', re.IGNORECASE),
        ],
    },
    'process_description': {
        'label': '과정 설명',
        'patterns': [
            re.compile(r'(?:(?:분석|평가|측정|테스트)\s*(?:과정|절차|방법|프로세스))', re.IGNORECASE),
            re.compile(r'(?:(?:다음|아래)\s*(?:과정|단계|절차)를?\s*(?:거쳐|통해|따라))', re.IGNORECASE),
            re.compile(r'\b(?:(?:our|the)\s+(?:process|methodology|approach|procedure))\b', re.IGNORECASE),
            re.compile(r'\b(?:we\s+(?:analyzed|evaluated|assessed|measured)\s+(?:by|using|through))\b', re.IGNORECASE),
        ],
    },
    'limitations': {
        'label': '한계/제약',
        'patterns': [
            re.compile(r'(?:한계|제약|제한\s*(?:사항|점)|주의\s*(?:사항|점))', re.IGNORECASE),
            re.compile(r'(?:(?:이\s*)?(?:분석|결과|조사)의?\s*한계)', re.IGNORECASE),
            re.compile(r'\b(?:limitations?|caveats?|constraints?|disclaimer)\b', re.IGNORECASE),
        ],
    },
    'reproducibility': {
        'label': '재현 가능성',
        'patterns': [
            re.compile(r'(?:재현|재생산|반복\s*(?:가능|실행))', re.IGNORECASE),
            re.compile(r'(?:(?:동일|같은)\s*(?:조건|환경|방법)으로?\s*(?:반복|재현))', re.IGNORECASE),
            re.compile(r'(?:코드|스크립트|환경)\s*(?:공개|제공|공유)', re.IGNORECASE),
            re.compile(r'\b(?:reproducib|replicat|open[\s-]?source|code\s+available)\b', re.IGNORECASE),
        ],
    },
    'time_context': {
        'label': '시점/기간',
        'patterns': [
            re.compile(r'(?:\d{4}년\s*\d{1,2}월|\d{4}\s*[-/]\s*\d{1,2})', re.IGNORECASE),
            re.compile(r'(?:(?:조사|분석|테스트|측정)\s*(?:기간|시점|일자))', re.IGNORECASE),
            re.compile(r'(?:기준일|기준\s*시점|작성\s*시점)', re.IGNORECASE),
            re.compile(r'\b(?:as\s+of|dated?|conducted\s+(?:in|on|during))\b', re.IGNORECASE),
        ],
    },
}


def _has_pattern(content: str, patterns: list) -> bool:
    return any(p.search(content) for p in patterns)


_EMPTY_RESULT = {
    'score': 50.0,
    'summary': {
        'categories_found': 0,
        'found_list': [],
        'missing_list': [],
        'transparency_ratio': 0.0,
        'level': 'none',
    },
    'transparency_details': [],
    'suggestions': [],
}


def _scan_categories(content: str) -> tuple:
    """카테고리별 방법론 패턴을 스캔합니다.

    Returns:
        (found_list, missing_list, details)
    """
    found_list = []
    missing_list = []
    details = []

    for cat_name, cat_info in _METHODOLOGY_CATEGORIES.items():
        found = _has_pattern(content, cat_info['patterns'])
        details.append({
            'category': cat_name,
            'label': cat_info['label'],
            'found': found,
        })
        if found:
            found_list.append(cat_name)
        else:
            missing_list.append(cat_name)

    return found_list, missing_list, details


def _compute_transparency_level(found_count: int, total: int) -> tuple:
    """투명성 레벨과 점수를 계산합니다.

    Returns:
        (level, score, ratio)
    """
    ratio = round(found_count / total * 100, 1)

    if found_count >= 5:
        level = 'transparent'
    elif found_count >= 3:
        level = 'good'
    elif found_count >= 2:
        level = 'partial'
    elif found_count >= 1:
        level = 'minimal'
    else:
        level = 'opaque'

    score = round(max(0.0, min(100.0, 15.0 + (found_count / total * 85.0))), 1)
    return level, score, ratio


def check_methodology_transparency(content: str) -> dict:
    """방법론 투명성을 검사합니다.

    Returns:
        score, summary, transparency_details, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return dict(_EMPTY_RESULT)

    found_list, missing_list, details = _scan_categories(content)
    total = len(_METHODOLOGY_CATEGORIES)
    level, score, ratio = _compute_transparency_level(len(found_list), total)

    return {
        'score': score,
        'summary': {
            'categories_found': len(found_list),
            'found_list': found_list,
            'missing_list': missing_list,
            'transparency_ratio': ratio,
            'level': level,
        },
        'transparency_details': details,
        'suggestions': _generate_suggestions(
            found_list, missing_list, ratio, level, details
        ),
    }


def _generate_suggestions(found: List[str], missing: List[str],
                           ratio: float, level: str,
                           details: List[Dict]) -> List[str]:
    suggestions = []

    level_labels = {
        'none': '해당 없음', 'transparent': '투명',
        'good': '양호', 'partial': '부분적',
        'minimal': '최소', 'opaque': '불투명',
    }
    suggestions.append(
        f'방법론 투명성: {level_labels.get(level, level)} '
        f'({ratio}%).'
    )

    labels = {k: v['label'] for k, v in _METHODOLOGY_CATEGORIES.items()}

    if missing:
        missing_labels = ', '.join(labels.get(m, m) for m in missing[:3])
        suggestions.append(
            f'누락된 투명성 요소: {missing_labels}.'
        )

    if 'data_source' not in found:
        suggestions.append('데이터 출처를 명시하세요.')

    if 'limitations' not in found:
        suggestions.append('분석의 한계나 주의사항을 밝히세요.')

    if 'time_context' not in found:
        suggestions.append('조사/분석 시점이나 기간을 명시하세요.')

    return suggestions
