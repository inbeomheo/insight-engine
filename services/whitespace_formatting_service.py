"""
Whitespace Formatting Auditor 서비스

콘텐츠의 공백, 빈 줄, 들여쓰기 등 포맷 일관성을 점검합니다.
과도한 빈 줄, 후행 공백, 탭/스페이스 혼용 등을 감지합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict


def audit_whitespace_formatting(content: str) -> dict:
    """콘텐츠의 공백/포맷 일관성을 점검합니다.

    Returns:
        issues, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'issues': [],
            'summary': {'total_issues': 0, 'consecutive_blanks': 0,
                        'trailing_spaces': 0, 'inconsistent_indent': 0,
                        'total_lines': 0},
            'score': 100.0,
            'suggestions': [],
        }

    lines = content.split('\n')
    total_lines = len(lines)
    issues: list = []

    blanks_issues, consecutive_blank_count = _check_consecutive_blanks(lines, total_lines)
    trailing_issues, trailing_count = _check_trailing_spaces(lines)
    indent_issues, inconsistent_indent = _check_mixed_indent(lines)
    long_issues, long_lines = _check_long_lines(lines)
    heading_issues, missing_heading_space = _check_heading_spacing(lines)

    issues.extend(blanks_issues)
    issues.extend(trailing_issues)
    issues.extend(indent_issues)
    issues.extend(long_issues)
    issues.extend(heading_issues)

    penalty = (consecutive_blank_count * 10 + trailing_count * 2 +
               inconsistent_indent * 15 + long_lines * 5 + missing_heading_space * 3)
    score = round(max(0.0, min(100.0, 100.0 - penalty)), 1)

    suggestions = _generate_suggestions(issues, consecutive_blank_count,
                                         trailing_count, inconsistent_indent, long_lines)

    return {
        'issues': issues,
        'summary': {
            'total_issues': len(issues),
            'consecutive_blanks': consecutive_blank_count,
            'trailing_spaces': trailing_count,
            'inconsistent_indent': inconsistent_indent,
            'total_lines': total_lines,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _check_consecutive_blanks(lines: list, total_lines: int) -> tuple:
    """연속 빈 줄(3줄 이상) 감지."""
    issues = []
    consecutive_blank = 0
    blank_start = -1
    count = 0
    for i, line in enumerate(lines):
        if line.strip() == '':
            if blank_start == -1:
                blank_start = i
            consecutive_blank += 1
        else:
            if consecutive_blank >= 3:
                count += 1
                issues.append({
                    'type': 'consecutive_blanks',
                    'line': blank_start + 1,
                    'detail': f'{consecutive_blank}줄 연속 빈 줄 (라인 {blank_start + 1}-{i})',
                    'severity': 'warning',
                })
            consecutive_blank = 0
            blank_start = -1
    if consecutive_blank >= 3:
        count += 1
        issues.append({
            'type': 'consecutive_blanks',
            'line': blank_start + 1,
            'detail': f'{consecutive_blank}줄 연속 빈 줄 (라인 {blank_start + 1}-{total_lines})',
            'severity': 'warning',
        })
    return issues, count


def _check_trailing_spaces(lines: list) -> tuple:
    """후행 공백 감지."""
    issues = []
    trailing_count = sum(1 for line in lines if line != line.rstrip() and line.strip())
    if trailing_count > 0:
        issues.append({
            'type': 'trailing_spaces',
            'line': 0,
            'detail': f'후행 공백이 있는 줄 {trailing_count}개',
            'severity': 'info',
        })
    return issues, trailing_count


def _check_mixed_indent(lines: list) -> tuple:
    """탭/스페이스 혼용 감지."""
    issues = []
    has_tab = any(line.startswith('\t') for line in lines)
    has_space_indent = any(re.match(r'^    ', line) for line in lines)
    inconsistent = 0
    if has_tab and has_space_indent:
        inconsistent = 1
        issues.append({
            'type': 'mixed_indent',
            'line': 0,
            'detail': '탭과 스페이스 들여쓰기가 혼용되어 있습니다',
            'severity': 'warning',
        })
    return issues, inconsistent


def _check_long_lines(lines: list) -> tuple:
    """매우 긴 줄(200자 이상, 코드 블록 제외) 감지."""
    issues = []
    long_lines = 0
    in_code_block = False
    for line in lines:
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            continue
        if not in_code_block and len(line) > 200:
            long_lines += 1
    if long_lines > 0:
        issues.append({
            'type': 'long_lines',
            'line': 0,
            'detail': f'200자 초과 줄 {long_lines}개 (가독성 저하 우려)',
            'severity': 'info',
        })
    return issues, long_lines


def _check_heading_spacing(lines: list) -> tuple:
    """헤딩 전후 빈 줄 누락 감지."""
    issues = []
    missing = 0
    for i, line in enumerate(lines):
        if re.match(r'^#{1,6}\s+', line.strip()):
            if i > 0 and lines[i - 1].strip() != '':
                missing += 1
    if missing > 0:
        issues.append({
            'type': 'heading_spacing',
            'line': 0,
            'detail': f'헤딩 위에 빈 줄이 없는 곳 {missing}개',
            'severity': 'info',
        })
    return issues, missing


def _generate_suggestions(issues: List[Dict], blanks: int, trailing: int,
                           indent: int, long: int) -> List[str]:
    suggestions = []
    if not issues:
        suggestions.append('포맷이 일관적입니다. 특별한 문제가 없습니다.')
        return suggestions
    if blanks > 0:
        suggestions.append(f'연속 빈 줄 {blanks}곳: 2줄 이내로 줄이면 가독성이 향상됩니다.')
    if trailing > 0:
        suggestions.append(f'후행 공백 {trailing}줄: 에디터의 "Trim trailing whitespace" 기능을 활성화하세요.')
    if indent > 0:
        suggestions.append('탭/스페이스 혼용: 하나의 들여쓰기 방식으로 통일하세요.')
    if long > 0:
        suggestions.append(f'긴 줄 {long}개: 줄바꿈을 추가하여 모바일 가독성을 개선하세요.')
    return suggestions
