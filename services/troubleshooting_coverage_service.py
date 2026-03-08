"""
Troubleshooting Coverage Analyzer 서비스

실행 가이드에 실패 케이스, 검증 방법, 복구/롤백,
FAQ형 문제 해결이 없는지 탐지합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List

# 가이드/튜토리얼 신호
_GUIDE_SIGNALS = [
    re.compile(r'(?:가이드|튜토리얼|설치|설정|구축|배포|실습|따라하기)', re.IGNORECASE),
    re.compile(r'(?:단계별|step\s*by\s*step|how\s*to|getting\s*started|setup)', re.IGNORECASE),
]

# 문제 해결 카테고리별 패턴
_TROUBLESHOOTING_CATEGORIES = {
    'error_handling': {
        'label': '에러/실패 케이스',
        'patterns': [
            re.compile(r'(?:에러|오류|실패|문제\s*(?:해결|발생)|트러블슈팅)', re.IGNORECASE),
            re.compile(r'(?:안\s*(?:되|될)\s*(?:때|경우|경우에)|작동\s*(?:안|하지\s*않))', re.IGNORECASE),
            re.compile(r'\b(?:error|fail|trouble|issue|problem|not\s+working|debug)\b', re.IGNORECASE),
        ],
    },
    'validation': {
        'label': '검증/확인 방법',
        'patterns': [
            re.compile(r'(?:확인\s*(?:방법|하기|하세요)|검증|테스트\s*(?:하|방법))', re.IGNORECASE),
            re.compile(r'(?:정상\s*(?:작동|동작|실행)|성공\s*(?:시|하면))', re.IGNORECASE),
            re.compile(r'\b(?:verify|validate|check|test|confirm|expect|should\s+see)\b', re.IGNORECASE),
        ],
    },
    'rollback': {
        'label': '복구/롤백',
        'patterns': [
            re.compile(r'(?:복구|롤백|되돌리|원상|복원|취소\s*(?:방법|하기))', re.IGNORECASE),
            re.compile(r'(?:이전\s*(?:상태|버전).*?(?:돌아|복구|복원))', re.IGNORECASE),
            re.compile(r'\b(?:rollback|revert|undo|restore|recover|fallback)\b', re.IGNORECASE),
        ],
    },
    'faq': {
        'label': 'FAQ/자주 묻는 질문',
        'patterns': [
            re.compile(r'(?:FAQ|자주\s*(?:묻는|하는)\s*질문|Q\s*&\s*A|질문\s*(?:과|&)\s*답)', re.IGNORECASE),
            re.compile(r'(?:(?:Q|질문)\s*[:\.]\s*.+\n\s*(?:A|답)\s*[:\.]\s*)', re.IGNORECASE),
            re.compile(r'\b(?:frequently\s+asked|common\s+(?:questions?|issues?))\b', re.IGNORECASE),
        ],
    },
    'workaround': {
        'label': '대안/우회 방법',
        'patterns': [
            re.compile(r'(?:대안|우회\s*방법|대체\s*방법|차선책|해결\s*(?:책|방법))', re.IGNORECASE),
            re.compile(r'(?:다른\s*방법|대신|대체\s*(?:할|가능))', re.IGNORECASE),
            re.compile(r'\b(?:workaround|alternative|instead|another\s+way|work\s*around)\b', re.IGNORECASE),
        ],
    },
}

# 문제 해결 섹션 헤딩
_TROUBLESHOOTING_HEADING_PATTERNS = [
    re.compile(r'(?:문제\s*해결|트러블슈팅|에러\s*처리|FAQ|자주\s*(?:묻는|하는))', re.IGNORECASE),
    re.compile(r'\b(?:troubleshoot|debug|FAQ|common\s+(?:errors?|issues?|problems?))\b', re.IGNORECASE),
]

_HEADING_RE = re.compile(r'^#{1,3}\s+(.+)$', re.MULTILINE)


def _count_matches(content: str, patterns: list) -> int:
    return sum(len(p.findall(content)) for p in patterns)


def _has_pattern(content: str, patterns: list) -> bool:
    return any(p.search(content) for p in patterns)


def analyze_troubleshooting_coverage(content: str) -> dict:
    """가이드의 문제 해결 커버리지를 분석합니다.

    Returns:
        score, summary, suggestions, missing_categories를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'score': 100.0,
            'summary': {
                'is_guide_content': False,
                'has_troubleshooting_section': False,
                'categories_found': [],
                'categories_missing': [],
                'coverage_ratio': 0.0,
                'level': 'none',
            },
            'missing_categories': [],
            'suggestions': [],
        }

    # 가이드 콘텐츠 여부
    is_guide = _count_matches(content, _GUIDE_SIGNALS) >= 2

    # 문제 해결 섹션 존재 여부
    headings = _HEADING_RE.findall(content)
    has_ts_section = any(
        _has_pattern(h, _TROUBLESHOOTING_HEADING_PATTERNS) for h in headings
    )

    # 각 카테고리 존재 여부
    categories_found = []
    categories_missing = []

    for cat_name, cat_info in _TROUBLESHOOTING_CATEGORIES.items():
        if _has_pattern(content, cat_info['patterns']):
            categories_found.append(cat_name)
        else:
            categories_missing.append(cat_name)

    # 커버리지 비율
    total = len(_TROUBLESHOOTING_CATEGORIES)
    coverage = round(len(categories_found) / max(total, 1) * 100, 1)

    # 레벨 판정
    if not is_guide:
        level = 'none'
    elif coverage >= 80:
        level = 'comprehensive'
    elif coverage >= 60:
        level = 'good'
    elif coverage >= 40:
        level = 'fair'
    elif coverage >= 20:
        level = 'partial'
    else:
        level = 'missing'

    # 연속 점수 — coverage 비율 기반
    if not is_guide:
        score = 100.0
    else:
        score = 20.0 + (coverage / 100.0 * 75.0)
        if has_ts_section:
            score += 5.0

    score = round(max(0.0, min(100.0, score)), 1)

    missing_details = [
        {'category': m, 'label': _TROUBLESHOOTING_CATEGORIES[m]['label']}
        for m in categories_missing
    ]

    suggestions = _generate_suggestions(
        is_guide, has_ts_section, categories_found,
        categories_missing, coverage, level
    )

    return {
        'score': score,
        'summary': {
            'is_guide_content': is_guide,
            'has_troubleshooting_section': has_ts_section,
            'categories_found': categories_found,
            'categories_missing': categories_missing,
            'coverage_ratio': coverage,
            'level': level,
        },
        'missing_categories': missing_details,
        'suggestions': suggestions,
    }


def _generate_suggestions(is_guide: bool, has_section: bool,
                           found: List[str], missing: List[str],
                           coverage: float, level: str) -> List[str]:
    suggestions = []

    if not is_guide:
        suggestions.append('가이드/튜토리얼 콘텐츠가 아닌 것으로 판단됩니다.')
        return suggestions

    level_labels = {
        'comprehensive': '포괄적', 'good': '양호', 'fair': '보통',
        'partial': '부분적', 'missing': '부족',
    }
    suggestions.append(
        f'문제 해결 커버리지: {level_labels.get(level, level)} '
        f'({len(found)}/{len(found) + len(missing)} 카테고리, {coverage}%).'
    )

    if not has_section:
        suggestions.append(
            '"문제 해결" 또는 "Troubleshooting" 섹션을 추가하세요.'
        )

    labels = {c: _TROUBLESHOOTING_CATEGORIES[c]['label'] for c in _TROUBLESHOOTING_CATEGORIES}
    for m in missing[:3]:
        suggestions.append(
            f'{labels.get(m, m)} 관련 내용을 추가하세요.'
        )

    return suggestions
