"""
Acronym Consistency Checker 서비스

콘텐츠 내 약어/두문자어가 일관성 있게 사용되었는지 검사합니다.
첫 사용 시 풀네임 여부, 같은 약어의 표기 통일, 과도한 약어 사용을 감지합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict, Tuple
from collections import defaultdict

# 약어 패턴: 2글자 이상 대문자 (숫자 포함 가능)
_ACRONYM_RE = re.compile(r'(?<![A-Za-z0-9])([A-Z][A-Z0-9]{1,9})(?![A-Za-z0-9])')

# 괄호 안 약어 정의: "Full Name (ABC)" 또는 "(ABC, Full Name)"
_DEFINED_ACRONYM_RE = re.compile(
    r'([A-Za-z\s]{3,50})\s*\(([A-Z][A-Z0-9]{1,9})\)'
)

# 마크다운 헤딩 제거
_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)

# 흔한 영어 약어 (검사 제외)
_COMMON_ACRONYMS = {
    'OK', 'AM', 'PM', 'TV', 'IT', 'AI', 'PC', 'USB', 'URL', 'HTTP',
    'HTTPS', 'HTML', 'CSS', 'JS', 'PDF', 'FAQ', 'CEO', 'CTO', 'HR',
    'PR', 'QA', 'UI', 'UX', 'ID', 'IO', 'OS', 'SQL', 'API', 'SDK',
    'CD', 'DVD', 'GPS', 'SMS', 'SIM', 'PIN', 'ATM', 'DIY', 'VIP',
}


def _find_acronyms(content: str) -> List[Dict]:
    """콘텐츠에서 모든 약어를 위치와 함께 추출합니다."""
    acronyms = []
    for match in _ACRONYM_RE.finditer(content):
        acronym = match.group(1)
        if acronym not in _COMMON_ACRONYMS and len(acronym) >= 2:
            acronyms.append({
                'acronym': acronym,
                'position': match.start(),
            })
    return acronyms


def _find_definitions(content: str) -> Dict[str, str]:
    """괄호로 정의된 약어를 찾습니다."""
    definitions = {}
    for match in _DEFINED_ACRONYM_RE.finditer(content):
        full_name = match.group(1).strip()
        acronym = match.group(2)
        definitions[acronym] = full_name
    return definitions


def check_acronym_consistency(content: str) -> dict:
    """약어 일관성을 검사합니다.

    Returns:
        acronym_map, issues, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'acronym_map': [],
            'issues': [],
            'summary': {
                'total_acronyms': 0,
                'unique_acronyms': 0,
                'defined_count': 0,
                'undefined_count': 0,
                'consistency_level': 'none',
            },
            'score': 100.0,
            'suggestions': [],
        }

    cleaned = _HEADING_RE.sub('', content)
    acronyms = _find_acronyms(cleaned)
    definitions = _find_definitions(cleaned)

    if not acronyms:
        return {
            'acronym_map': [],
            'issues': [],
            'summary': {
                'total_acronyms': 0,
                'unique_acronyms': 0,
                'defined_count': 0,
                'undefined_count': 0,
                'consistency_level': 'none',
            },
            'score': 100.0,
            'suggestions': [],
        }

    # 약어별 사용 횟수
    usage_count = defaultdict(int)
    first_occurrence = {}
    for item in acronyms:
        acr = item['acronym']
        usage_count[acr] += 1
        if acr not in first_occurrence:
            first_occurrence[acr] = item['position']

    unique_acronyms = set(usage_count.keys())
    defined = set(definitions.keys())
    undefined = unique_acronyms - defined

    # 이슈 감지
    issues = []

    # 1. 정의 없이 사용된 약어
    for acr in undefined:
        if usage_count[acr] >= 1:
            issues.append({
                'type': 'undefined',
                'acronym': acr,
                'message': f'{acr}의 풀네임이 정의되지 않았습니다.',
            })

    # 2. 과다 사용 (5회 이상이면서 정의 없는 경우)
    for acr in unique_acronyms:
        if usage_count[acr] >= 5 and acr in undefined:
            issues.append({
                'type': 'overuse',
                'acronym': acr,
                'message': f'{acr}이(가) {usage_count[acr]}회 사용되었으나 풀네임 없음.',
            })

    # 약어 맵 생성
    acronym_map = []
    for acr in sorted(unique_acronyms):
        acronym_map.append({
            'acronym': acr,
            'full_name': definitions.get(acr, ''),
            'count': usage_count[acr],
            'defined': acr in defined,
        })

    # 일관성 레벨
    total_unique = len(unique_acronyms)
    defined_count = len(defined & unique_acronyms)
    undefined_count = len(undefined)

    if total_unique == 0:
        level = 'none'
    elif undefined_count == 0:
        level = 'excellent'
    elif undefined_count <= total_unique * 0.3:
        level = 'good'
    elif undefined_count <= total_unique * 0.6:
        level = 'fair'
    else:
        level = 'poor'

    # 점수 계산
    if total_unique == 0:
        score = 100.0
    else:
        defined_ratio = defined_count / total_unique
        score = 100.0 * defined_ratio
        # 이슈 수에 따른 감점
        issue_penalty = min(30.0, len(issues) * 5.0)
        score -= issue_penalty

    score = round(max(0.0, min(100.0, score)), 1)

    suggestions = _generate_suggestions(undefined, defined, usage_count, level)

    return {
        'acronym_map': acronym_map[:20],
        'issues': issues[:15],
        'summary': {
            'total_acronyms': sum(usage_count.values()),
            'unique_acronyms': total_unique,
            'defined_count': defined_count,
            'undefined_count': undefined_count,
            'consistency_level': level,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _generate_suggestions(undefined: set, defined: set,
                           usage_count: dict, level: str) -> List[str]:
    suggestions = []
    level_labels = {
        'excellent': '우수', 'good': '양호',
        'fair': '보통', 'poor': '미흡', 'none': '없음',
    }
    suggestions.append(
        f'약어 일관성: {level_labels.get(level, level)}.'
    )

    if undefined:
        undef_list = ', '.join(sorted(list(undefined))[:5])
        suggestions.append(
            f'정의 없는 약어: {undef_list}. '
            f'첫 사용 시 "풀네임 (약어)" 형식으로 정의하세요.'
        )

    if len(defined) + len(undefined) > 10:
        suggestions.append(
            '약어가 많습니다. 독자의 이해를 위해 약어 목록(glossary)을 추가하세요.'
        )

    return suggestions
