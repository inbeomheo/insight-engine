"""
Heading Hierarchy Integrity Checker 서비스

H1→H2→H3 계층 건너뜀, 중복 H1, 빈 섹션 등
마크다운 제목 구조 오류를 검사합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

# 마크다운 제목 패턴
_HEADING = re.compile(r'^(#{1,6})\s+(.+)', re.MULTILINE)


def _extract_headings(content: str) -> List[Dict]:
    """마크다운 제목을 추출합니다."""
    headings = []
    for m in _HEADING.finditer(content):
        level = len(m.group(1))
        text = m.group(2).strip()
        headings.append({
            'level': level,
            'text': text,
            'position': m.start(),
        })
    return headings


def _check_skip(headings: List[Dict]) -> List[Dict]:
    """계층 건너뜀을 감지합니다 (예: H1→H3)."""
    skips = []
    for i in range(1, len(headings)):
        prev_level = headings[i - 1]['level']
        curr_level = headings[i]['level']
        if curr_level > prev_level + 1:
            skips.append({
                'type': 'skip',
                'message': f'H{prev_level}→H{curr_level} 건너뜀',
                'heading': headings[i]['text'][:50],
                'from_level': prev_level,
                'to_level': curr_level,
            })
    return skips


def _check_duplicate_h1(headings: List[Dict]) -> List[Dict]:
    """H1이 2개 이상인 경우를 감지합니다."""
    h1s = [h for h in headings if h['level'] == 1]
    if len(h1s) > 1:
        return [{
            'type': 'duplicate_h1',
            'message': f'H1이 {len(h1s)}개 존재 (권장: 1개)',
            'headings': [h['text'][:30] for h in h1s[:3]],
        }]
    return []


def _check_empty_sections(content: str, headings: List[Dict]) -> List[Dict]:
    """빈 섹션 (연속된 제목 사이 본문 없음)을 감지합니다."""
    empty = []
    lines = content.split('\n')

    for i in range(len(headings) - 1):
        # 두 제목 사이의 텍스트 확인
        start_pos = headings[i]['position']
        end_pos = headings[i + 1]['position']
        between = content[start_pos:end_pos]

        # 제목 자체의 줄을 제외한 본문 확인
        between_lines = between.split('\n')[1:]  # 첫 줄(제목) 제외
        body = '\n'.join(between_lines).strip()

        if len(body) < 2:  # 실질 본문 없음
            empty.append({
                'type': 'empty_section',
                'message': f'빈 섹션: "{headings[i]["text"][:30]}"',
                'heading': headings[i]['text'][:50],
            })

    return empty


def _check_deep_nesting(headings: List[Dict]) -> List[Dict]:
    """과도한 깊이 (H5+)를 감지합니다."""
    deep = []
    for h in headings:
        if h['level'] >= 5:
            deep.append({
                'type': 'deep_nesting',
                'message': f'H{h["level"]} 과도한 깊이',
                'heading': h['text'][:50],
            })
    return deep


_EMPTY_RESULT = {
    'score': 100.0,
    'summary': {'total_headings': 0, 'max_depth': 0, 'issue_count': 0, 'level': 'none'},
    'hierarchy_issues': [],
    'suggestions': [],
}


def _collect_issues(content: str, headings: List[Dict]) -> List[Dict]:
    """모든 계층 구조 이슈를 수집합니다."""
    issues = []
    issues.extend(_check_skip(headings))
    issues.extend(_check_duplicate_h1(headings))
    issues.extend(_check_empty_sections(content, headings))
    issues.extend(_check_deep_nesting(headings))
    return issues


def _compute_hierarchy_score(issue_count: int, total_headings: int) -> tuple:
    """계층 구조 점수와 레벨을 계산합니다.

    Returns:
        (score, level)
    """
    if issue_count == 0:
        level = 'clean'
    elif issue_count <= 2:
        level = 'minor'
    elif issue_count <= 5:
        level = 'moderate'
    else:
        level = 'problematic'

    if issue_count == 0:
        score = 100.0
    else:
        issue_ratio = issue_count / max(1, total_headings)
        score = max(10.0, 100.0 - (issue_count * 10.0) - (issue_ratio * 20.0))

    return round(max(0.0, min(100.0, score)), 1), level


def check_heading_hierarchy(content: str) -> dict:
    """마크다운 제목 계층 구조를 검사합니다.

    Returns:
        score, summary, hierarchy_issues, suggestions를 포함하는 dict
    """
    try:
        if not content or not content.strip():
            return dict(_EMPTY_RESULT)

        headings = _extract_headings(content)
        if not headings:
            return dict(_EMPTY_RESULT)

        issues = _collect_issues(content, headings)
        max_depth = max(h['level'] for h in headings)
        score, level = _compute_hierarchy_score(len(issues), len(headings))

        return {
            'score': score,
            'summary': {'total_headings': len(headings), 'max_depth': max_depth,
                         'issue_count': len(issues), 'level': level},
            'hierarchy_issues': issues[:10],
            'suggestions': _generate_suggestions(headings, max_depth, issues, level),
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}



def _generate_suggestions(headings: List[Dict], max_depth: int,
                           issues: List[Dict], level: str) -> List[str]:
    suggestions = []

    level_labels = {
        'none': '해당 없음', 'clean': '깨끗',
        'minor': '경미', 'moderate': '보통', 'problematic': '문제',
    }
    suggestions.append(
        f'제목 계층 구조: {level_labels.get(level, level)}. '
        f'제목 {len(headings)}개, 최대 깊이 H{max_depth}, 이슈 {len(issues)}건.'
    )

    skip_issues = [i for i in issues if i['type'] == 'skip']
    if skip_issues:
        suggestions.append(
            '제목 레벨을 건너뛰지 마세요 (예: H1→H3 대신 H1→H2→H3).'
        )

    h1_issues = [i for i in issues if i['type'] == 'duplicate_h1']
    if h1_issues:
        suggestions.append(
            '문서에 H1(#)은 하나만 사용하세요. 나머지는 H2(##)로 변경하세요.'
        )

    empty_issues = [i for i in issues if i['type'] == 'empty_section']
    if empty_issues:
        suggestions.append(
            f'빈 섹션 {len(empty_issues)}건: 본문을 추가하거나 제목을 제거하세요.'
        )

    deep_issues = [i for i in issues if i['type'] == 'deep_nesting']
    if deep_issues:
        suggestions.append(
            'H5 이상의 깊은 제목은 문서 구조를 복잡하게 합니다. H4 이하로 유지하세요.'
        )

    return suggestions
