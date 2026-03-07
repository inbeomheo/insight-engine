"""
Table of Contents Generator 서비스

마크다운 콘텐츠에서 헤딩을 추출하여 목차(TOC)를 자동 생성합니다.
깊이 제한, 앵커 링크 생성, 구조 검증을 수행합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict

_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)


def _slugify(text: str) -> str:
    """텍스트를 URL-safe 앵커 ID로 변환합니다."""
    # 특수문자 제거, 공백 → 하이픈
    slug = re.sub(r'[^\w가-힣\s-]', '', text)
    slug = re.sub(r'\s+', '-', slug.strip())
    return slug.lower()


def generate_toc(content: str, max_depth: int = 3) -> dict:
    """마크다운 콘텐츠에서 목차를 생성합니다.

    Args:
        content: 마크다운 콘텐츠
        max_depth: 최대 헤딩 깊이 (기본 3 = H1~H3)

    Returns:
        toc, markdown_toc, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'toc': [],
            'markdown_toc': '',
            'summary': {'total_headings': 0, 'max_depth_used': 0,
                        'structure_valid': True, 'depth_distribution': {}},
            'score': 0.0,
            'suggestions': ['콘텐츠가 비어 있습니다.'],
        }

    # 헤딩 추출
    headings = []
    for match in _HEADING_RE.finditer(content):
        level = len(match.group(1))
        text = match.group(2).strip()
        if level <= max_depth:
            headings.append({
                'level': level,
                'text': text,
                'anchor': _slugify(text),
            })

    if not headings:
        return {
            'toc': [],
            'markdown_toc': '',
            'summary': {'total_headings': 0, 'max_depth_used': 0,
                        'structure_valid': True, 'depth_distribution': {}},
            'score': 30.0,
            'suggestions': ['헤딩이 없습니다. 구조화를 위해 헤딩을 추가하세요.'],
        }

    # 구조 검증
    issues = _validate_structure(headings)
    structure_valid = len(issues) == 0

    # 깊이 분포
    depth_dist = {}
    for h in headings:
        key = f'h{h["level"]}'
        depth_dist[key] = depth_dist.get(key, 0) + 1

    max_depth_used = max(h['level'] for h in headings)

    # 마크다운 TOC 생성
    md_lines = []
    for h in headings:
        indent = '  ' * (h['level'] - 1)
        md_lines.append(f'{indent}- [{h["text"]}](#{h["anchor"]})')
    markdown_toc = '\n'.join(md_lines)

    # 점수
    score = _calculate_score(headings, issues)

    suggestions = _generate_suggestions(headings, issues, depth_dist)

    return {
        'toc': headings,
        'markdown_toc': markdown_toc,
        'summary': {
            'total_headings': len(headings),
            'max_depth_used': max_depth_used,
            'structure_valid': structure_valid,
            'depth_distribution': depth_dist,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _validate_structure(headings: List[Dict]) -> List[str]:
    """헤딩 구조를 검증합니다."""
    issues = []

    # H1이 여러 개인지
    h1_count = sum(1 for h in headings if h['level'] == 1)
    if h1_count > 1:
        issues.append(f'H1이 {h1_count}개입니다. H1은 1개만 사용하세요.')

    # 레벨 건너뛰기 (H1→H3 등)
    for i in range(1, len(headings)):
        prev_level = headings[i - 1]['level']
        curr_level = headings[i]['level']
        if curr_level > prev_level + 1:
            issues.append(
                f'H{prev_level}→H{curr_level} 레벨 건너뛰기: '
                f'"{headings[i]["text"]}"'
            )

    return issues


def _calculate_score(headings: List[Dict], issues: List[str]) -> float:
    base = 100.0

    # 이슈 감점
    base -= len(issues) * 15.0

    # 헤딩 수 보너스/페널티
    count = len(headings)
    if count < 3:
        base -= 20.0  # 헤딩 부족
    elif count > 20:
        base -= 10.0  # 과도한 헤딩

    return round(max(0.0, min(100.0, base)), 1)


def _generate_suggestions(headings: List[Dict], issues: List[str],
                           dist: Dict) -> List[str]:
    suggestions = []

    if issues:
        suggestions.extend(issues[:3])

    count = len(headings)
    if count < 3:
        suggestions.append(f'헤딩 {count}개로 부족합니다. 섹션을 나눠 구조를 강화하세요.')
    elif count > 20:
        suggestions.append(f'헤딩 {count}개로 과다합니다. 하위 헤딩을 통합하세요.')
    else:
        suggestions.append(f'헤딩 {count}개로 적정합니다.')

    if 'h1' not in dist:
        suggestions.append('H1(제목)이 없습니다. 최상위 제목을 추가하세요.')

    return suggestions
