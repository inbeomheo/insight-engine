"""
Acronym Expansion Compliance Checker 서비스

약어(2-6자 대문자)가 첫 등장 시 풀어서 설명됐는지 점검하여
초심자 친화성과 정보 전달 명확성을 높입니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict


# 약어 패턴 (2-6자 대문자, 한글 뒤 \b 미동작 우회)
_ACRONYM_PATTERN = re.compile(r'(?<![A-Za-z])([A-Z]{2,6})(?![A-Za-z])')

# 일반 영어 단어로 오탐되기 쉬운 약어 제외 목록
_ACRONYM_EXCEPTIONS = {
    'THE', 'AND', 'FOR', 'BUT', 'NOT', 'ARE', 'WAS', 'HAS', 'HAD',
    'HIS', 'HER', 'HIM', 'ITS', 'WHO', 'HOW', 'WHY', 'CAN', 'MAY',
    'ALL', 'ANY', 'FEW', 'NEW', 'OLD', 'OUR', 'OWN', 'TWO', 'USE',
    'SET', 'GET', 'PUT', 'RUN', 'LET', 'SAY', 'SEE', 'TRY', 'ADD',
    'END', 'BIG', 'TOP', 'LOW', 'KEY', 'WAY', 'DAY', 'MAN', 'GOD',
    'YES', 'NO', 'OK',
}

# 잘 알려진 약어 (풀어쓰기 없어도 허용)
_WELL_KNOWN = {
    'AI', 'API', 'URL', 'HTML', 'CSS', 'JS', 'HTTP', 'HTTPS',
    'SQL', 'PDF', 'USB', 'CEO', 'CTO', 'CFO', 'VP', 'HR',
    'PC', 'TV', 'OK', 'FAQ', 'ID', 'IT', 'UI', 'UX',
}

# 풀어쓰기 패턴: "약어 (Full Name)" 또는 "Full Name (약어)"
_EXPANSION_PATTERN_PAREN = re.compile(
    r'([A-Z]{2,6})\s*\(([^)]{3,})\)'      # API (Application Programming Interface)
    r'|'
    r'\(([A-Z]{2,6})\)'                     # (API)
)

# "약어, 즉 설명" 또는 "약어: 설명"
_EXPANSION_PATTERN_INLINE = re.compile(
    r'([A-Z]{2,6})\s*(?:,\s*즉|,\s*다시\s*말해|:\s)\s*(.{5,50})'
)

# "Full Name, 약어" 패턴
_EXPANSION_BEFORE = re.compile(
    r'([A-Za-z\s]{5,50})\s*\(([A-Z]{2,6})\)'
)


_EMPTY_RESULT = {
    'acronyms': [],
    'summary': {'total_acronyms': 0, 'expanded': 0, 'unexpanded': 0, 'well_known': 0},
    'score': 100.0,
    'suggestions': [],
}


def _find_expanded_acronyms(content: str) -> set:
    """풀어쓰기된 약어를 모든 패턴에서 찾습니다."""
    expanded = set()
    for match in _EXPANSION_PATTERN_PAREN.finditer(content):
        if match.group(1):
            expanded.add(match.group(1))
        if match.group(3):
            expanded.add(match.group(3))
    for match in _EXPANSION_PATTERN_INLINE.finditer(content):
        expanded.add(match.group(1))
    for match in _EXPANSION_BEFORE.finditer(content):
        expanded.add(match.group(2))
    return expanded


def _classify_acronyms(all_acronyms: set, expanded_set: set) -> tuple:
    """약어를 상태별로 분류합니다.

    Returns:
        (acronyms_list, well_known_count)
    """
    acronyms = []
    well_known_count = 0
    for acr in sorted(all_acronyms):
        is_well_known = acr in _WELL_KNOWN
        is_expanded = acr in expanded_set
        if is_well_known:
            well_known_count += 1
        status = 'expanded' if is_expanded else ('well_known' if is_well_known else 'unexpanded')
        acronyms.append({
            'acronym': acr, 'is_expanded': is_expanded,
            'is_well_known': is_well_known, 'status': status,
        })
    return acronyms, well_known_count


def check_acronym_expansion(content: str) -> dict:
    """약어의 첫 등장 시 풀어쓰기 여부를 점검합니다.

    Args:
        content: 분석할 텍스트 콘텐츠

    Returns:
        acronyms, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return dict(_EMPTY_RESULT)

    all_acronyms = {m.group(1) for m in _ACRONYM_PATTERN.finditer(content)} - _ACRONYM_EXCEPTIONS
    if not all_acronyms:
        return dict(_EMPTY_RESULT)

    acronyms, well_known_count = _classify_acronyms(all_acronyms, _find_expanded_acronyms(content))
    total = len(acronyms)
    expanded = sum(1 for a in acronyms if a['is_expanded'])
    unexpanded = sum(1 for a in acronyms if a['status'] == 'unexpanded')
    compliant = expanded + well_known_count
    score = max(0.0, min(100.0, round((compliant / total * 100) if total > 0 else 100.0, 1)))

    return {
        'acronyms': acronyms,
        'summary': {'total_acronyms': total, 'expanded': expanded,
                    'unexpanded': unexpanded, 'well_known': well_known_count},
        'score': score,
        'suggestions': _generate_suggestions(acronyms, unexpanded, total),
    }


def _generate_suggestions(acronyms: List[Dict], unexpanded: int, total: int) -> List[str]:
    """분석 결과 기반 제안을 생성합니다."""
    suggestions = []

    if unexpanded == 0:
        if total > 0:
            suggestions.append('모든 약어가 풀어쓰기되었거나 잘 알려진 약어입니다.')
        return suggestions

    unexpanded_list = [a['acronym'] for a in acronyms if a['status'] == 'unexpanded']
    names = ', '.join(unexpanded_list[:5])
    suggestions.append(
        f'풀어쓰기 없는 약어 {unexpanded}개: {names}. '
        f'첫 등장 시 "약어 (Full Name)" 형식으로 설명을 추가하세요.'
    )

    if unexpanded > total * 0.5:
        suggestions.append(
            '절반 이상의 약어에 설명이 없습니다. '
            '초심자 독자를 위해 약어 풀어쓰기를 보강하세요.'
        )

    return suggestions
