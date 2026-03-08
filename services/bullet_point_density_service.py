"""
Bullet Point Density Analyzer 서비스

콘텐츠에서 불릿 리스트의 밀도와 분포를 분석하여
스캔 가능성과 정보 구조 품질을 평가합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict


# 마크다운 헤딩
_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

# 불릿 리스트 항목 (마크다운)
_BULLET_RE = re.compile(r'^\s*[-*+]\s+.+', re.MULTILINE)

# 번호 리스트 항목 (마크다운)
_NUMBERED_RE = re.compile(r'^\s*\d+[.)]\s+.+', re.MULTILINE)

# HTML 리스트 항목
_HTML_LI_RE = re.compile(r'<li\b[^>]*>(.+?)</li>', re.IGNORECASE | re.DOTALL)


def _count_content_lines(content: str) -> int:
    """비어있지 않은 콘텐츠 줄 수를 셉니다."""
    return sum(1 for line in content.split('\n') if line.strip() and not _HEADING_RE.match(line.strip()))


def _parse_sections(content: str) -> List[Dict]:
    lines = content.split('\n')
    sections = []
    current = {'section': '(서론)', 'lines': []}
    for line in lines:
        m = _HEADING_RE.match(line.strip())
        if m:
            if current['lines'] or current['section'] != '(서론)':
                sections.append(current)
            current = {'section': m.group(2).strip(), 'lines': []}
        else:
            current['lines'].append(line)
    sections.append(current)
    if sections and sections[0]['section'] == '(서론)' and not ''.join(sections[0]['lines']).strip():
        sections = sections[1:]
    return sections


_EMPTY_RESULT = {
    'section_analysis': [],
    'list_groups': [],
    'summary': {'total_list_items': 0, 'total_content_lines': 0,
                'bullet_density': 0.0, 'list_group_count': 0},
    'score': 50.0,
    'suggestions': [],
}


def _detect_list_groups(content: str) -> List[Dict]:
    """연속된 리스트 항목을 그룹으로 감지합니다."""
    list_groups = []
    lines = content.split('\n')
    in_list = False
    group_start = -1
    group_items = 0
    for i, line in enumerate(lines):
        is_list = bool(_BULLET_RE.match(line) or _NUMBERED_RE.match(line))
        if is_list:
            if not in_list:
                group_start = i
                group_items = 0
            group_items += 1
            in_list = True
        else:
            if in_list and group_items > 0:
                list_groups.append({
                    'start_line': group_start + 1,
                    'item_count': group_items,
                    'is_long': group_items > 10,
                })
            in_list = False
            group_items = 0
    if in_list and group_items > 0:
        list_groups.append({
            'start_line': group_start + 1,
            'item_count': group_items,
            'is_long': group_items > 10,
        })
    return list_groups


def _compute_bullet_score(density: float, list_groups: List[Dict]) -> float:
    """밀도와 긴 리스트 그룹 기반으로 점수를 계산합니다."""
    if density == 0:
        score = 40.0
    elif density < 10:
        score = 40.0 + density * 3
    elif density <= 40:
        score = 70.0 + min(30.0, (density - 10) * (30.0 / 30.0))
    elif density <= 60:
        score = 100.0 - (density - 40) * 2
    else:
        score = max(0.0, 60.0 - (density - 60) * 2)
    score = round(max(0.0, min(100.0, score)), 1)

    long_groups = [g for g in list_groups if g['is_long']]
    if long_groups:
        score = round(max(0.0, score - len(long_groups) * 10), 1)

    return score


def analyze_bullet_density(content: str) -> dict:
    """불릿 리스트 밀도를 분석합니다.

    Returns:
        section_analysis, list_groups, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {**_EMPTY_RESULT, 'suggestions': ['콘텐츠가 비어 있습니다.']}

    bullet_items = _BULLET_RE.findall(content)
    numbered_items = _NUMBERED_RE.findall(content)
    html_items = _HTML_LI_RE.findall(content)
    total_list_items = len(bullet_items) + len(numbered_items) + len(html_items)

    content_lines = _count_content_lines(content)
    density = round((total_list_items / content_lines * 100) if content_lines > 0 else 0.0, 1)

    list_groups = _detect_list_groups(content)

    sections = _parse_sections(content)
    section_analysis = []
    for sec in sections:
        text = '\n'.join(sec['lines'])
        sec_bullets = len(_BULLET_RE.findall(text)) + len(_NUMBERED_RE.findall(text))
        sec_lines = sum(1 for l in sec['lines'] if l.strip())
        sec_density = round((sec_bullets / sec_lines * 100) if sec_lines > 0 else 0.0, 1)
        section_analysis.append({
            'section': sec['section'],
            'list_items': sec_bullets,
            'content_lines': sec_lines,
            'density': sec_density,
        })

    score = _compute_bullet_score(density, list_groups)
    long_groups = [g for g in list_groups if g['is_long']]

    suggestions = _generate_suggestions(
        total_list_items, density, list_groups, long_groups, content_lines
    )

    return {
        'section_analysis': section_analysis,
        'list_groups': list_groups,
        'summary': {
            'total_list_items': total_list_items,
            'total_content_lines': content_lines,
            'bullet_density': density,
            'list_group_count': len(list_groups),
        },
        'score': score,
        'suggestions': suggestions,
    }


def _generate_suggestions(
    items: int, density: float, groups: list, long: list, lines: int
) -> List[str]:
    suggestions = []
    if items == 0:
        suggestions.append('불릿 리스트가 없습니다. 핵심 포인트를 목록으로 정리하면 스캔성이 높아집니다.')
        return suggestions
    if density > 60:
        suggestions.append(f'불릿 밀도 {density}%로 과다합니다. 일부를 문단 서술로 바꿔 균형을 맞추세요.')
    elif density < 10:
        suggestions.append(f'불릿 밀도 {density}%로 낮습니다. 나열형 정보를 목록으로 변환하세요.')
    else:
        suggestions.append(f'불릿 밀도 {density}%로 적정합니다.')
    if long:
        suggestions.append(f'10항목 초과 리스트 {len(long)}개: 하위 그룹으로 분리하면 가독성이 향상됩니다.')
    return suggestions
