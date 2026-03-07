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
    issues = []

    # 1. 연속 빈 줄 감지 (3줄 이상)
    consecutive_blank = 0
    blank_start = -1
    consecutive_blank_count = 0
    for i, line in enumerate(lines):
        if line.strip() == '':
            if blank_start == -1:
                blank_start = i
            consecutive_blank += 1
        else:
            if consecutive_blank >= 3:
                consecutive_blank_count += 1
                issues.append({
                    'type': 'consecutive_blanks',
                    'line': blank_start + 1,
                    'detail': f'{consecutive_blank}줄 연속 빈 줄 (라인 {blank_start + 1}-{i})',
                    'severity': 'warning',
                })
            consecutive_blank = 0
            blank_start = -1
    if consecutive_blank >= 3:
        consecutive_blank_count += 1
        issues.append({
            'type': 'consecutive_blanks',
            'line': blank_start + 1,
            'detail': f'{consecutive_blank}줄 연속 빈 줄 (라인 {blank_start + 1}-{total_lines})',
            'severity': 'warning',
        })

    # 2. 후행 공백 감지
    trailing_count = 0
    for i, line in enumerate(lines):
        if line != line.rstrip() and line.strip():
            trailing_count += 1
    if trailing_count > 0:
        issues.append({
            'type': 'trailing_spaces',
            'line': 0,
            'detail': f'후행 공백이 있는 줄 {trailing_count}개',
            'severity': 'info',
        })

    # 3. 탭/스페이스 혼용 감지
    has_tab = False
    has_space_indent = False
    for line in lines:
        if line.startswith('\t'):
            has_tab = True
        elif re.match(r'^    ', line):
            has_space_indent = True
    inconsistent_indent = 0
    if has_tab and has_space_indent:
        inconsistent_indent = 1
        issues.append({
            'type': 'mixed_indent',
            'line': 0,
            'detail': '탭과 스페이스 들여쓰기가 혼용되어 있습니다',
            'severity': 'warning',
        })

    # 4. 매우 긴 줄 감지 (200자 이상, 코드 블록 제외)
    long_lines = 0
    in_code_block = False
    for i, line in enumerate(lines):
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

    # 5. 헤딩 전후 빈 줄 누락 감지
    missing_heading_space = 0
    for i, line in enumerate(lines):
        if re.match(r'^#{1,6}\s+', line.strip()):
            # 헤딩 위에 빈 줄이 없으면 (첫 줄 제외)
            if i > 0 and lines[i - 1].strip() != '':
                missing_heading_space += 1
    if missing_heading_space > 0:
        issues.append({
            'type': 'heading_spacing',
            'line': 0,
            'detail': f'헤딩 위에 빈 줄이 없는 곳 {missing_heading_space}개',
            'severity': 'info',
        })

    total_issues = len(issues)
    # 점수 계산
    penalty = (consecutive_blank_count * 10 + trailing_count * 2 +
               inconsistent_indent * 15 + long_lines * 5 + missing_heading_space * 3)
    score = round(max(0.0, min(100.0, 100.0 - penalty)), 1)

    suggestions = _generate_suggestions(issues, consecutive_blank_count,
                                         trailing_count, inconsistent_indent, long_lines)

    return {
        'issues': issues,
        'summary': {
            'total_issues': total_issues,
            'consecutive_blanks': consecutive_blank_count,
            'trailing_spaces': trailing_count,
            'inconsistent_indent': inconsistent_indent,
            'total_lines': total_lines,
        },
        'score': score,
        'suggestions': suggestions,
    }


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
