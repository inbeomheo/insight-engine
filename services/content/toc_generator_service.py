"""
Table of Contents Generator 서비스

마크다운 콘텐츠에서 헤딩을 추출하여 목차(TOC)를 자동 생성합니다.
깊이 제한, 앵커 링크 생성, 구조 검증을 수행합니다.
규칙 기반 (AI API 호출 없음).
"""
import logging
import re
from typing import List, Dict

logger = logging.getLogger(__name__)

_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)


def _slugify(text: str) -> str:
    """텍스트를 URL-safe 앵커 ID로 변환합니다."""
    slug = re.sub(r'[^\w가-힣\s-]', '', text)
    slug = re.sub(r'\s+', '-', slug.strip())
    return slug.lower()


_EMPTY_RESULT = {
    'toc': [],
    'markdown_toc': '',
    'summary': {'total_headings': 0, 'max_depth_used': 0,
                'structure_valid': True, 'depth_distribution': {}},
    'score': 0.0,
    'suggestions': [],
}


def _extract_headings(content: str, max_depth: int) -> List[Dict]:
    """마크다운 콘텐츠에서 헤딩을 추출합니다."""
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
    return headings


def _build_markdown_toc(headings: List[Dict]) -> tuple:
    """마크다운 TOC 문자열과 깊이 분포를 생성합니다.

    Returns:
        (markdown_toc, depth_dist, max_depth_used)
    """
    depth_dist = {}
    md_lines = []
    for h in headings:
        key = f'h{h["level"]}'
        depth_dist[key] = depth_dist.get(key, 0) + 1
        indent = '  ' * (h['level'] - 1)
        md_lines.append(f'{indent}- [{h["text"]}](#{h["anchor"]})')

    max_depth_used = max(h['level'] for h in headings)
    return '\n'.join(md_lines), depth_dist, max_depth_used


def generate_toc(content: str, max_depth: int = 3) -> dict:
    """마크다운 콘텐츠에서 목차를 생성합니다.

    Args:
        content: 마크다운 콘텐츠
        max_depth: 최대 헤딩 깊이 (기본 3 = H1~H3)

    Returns:
        toc, markdown_toc, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {**_EMPTY_RESULT, 'suggestions': ['콘텐츠가 비어 있습니다.']}
    try:

        headings = _extract_headings(content, max_depth)
        if not headings:
            return {**_EMPTY_RESULT, 'score': 30.0,
                    'suggestions': ['헤딩이 없습니다. 구조화를 위해 헤딩을 추가하세요.']}

        issues = _validate_structure(headings)
        markdown_toc, depth_dist, max_depth_used = _build_markdown_toc(headings)
        score = _calculate_score(headings, issues)

        return {
            'toc': headings,
            'markdown_toc': markdown_toc,
            'summary': {
                'total_headings': len(headings),
                'max_depth_used': max_depth_used,
                'structure_valid': len(issues) == 0,
                'depth_distribution': depth_dist,
            },
            'score': score,
            'suggestions': _generate_suggestions(headings, issues, depth_dist),
        }
    except Exception as e:
        logger.error(f"목차 생성 처리 실패: {e}")
        return {**_EMPTY_RESULT, 'suggestions': ['분석 중 오류가 발생했습니다.']}
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


def generate_numbered_toc(content: str, max_depth: int = 3) -> dict:
    """마크다운 콘텐츠에서 계층적 번호가 매겨진 목차를 생성합니다.

    H1은 번호 제외, H2부터 1., 2. 형식, H3는 1.1., 1.2. 형식으로 번호를 부여합니다.

    Args:
        content: 마크다운 콘텐츠
        max_depth: 최대 헤딩 깊이 (기본 3)

    Returns:
        numbered_toc (목차 항목 리스트), markdown (번호가 매겨진 마크다운 목차 문자열)
    """
    if not content or not content.strip():
        return {'numbered_toc': [], 'markdown': ''}

    headings = _extract_headings(content, max_depth)
    if not headings:
        return {'numbered_toc': [], 'markdown': ''}

    # 카운터: 각 레벨의 현재 번호
    counters = {}
    numbered = []
    md_lines = []

    for h in headings:
        level = h['level']

        if level == 1:
            # H1은 번호 없이 제목으로
            numbered.append({
                'level': level,
                'number': '',
                'text': h['text'],
                'anchor': h['anchor'],
            })
            md_lines.append(f'- [{h["text"]}](#{h["anchor"]})')
            # H1 이후 하위 카운터 리셋
            counters = {}
            continue

        # 현재 레벨 카운터 증가
        counters[level] = counters.get(level, 0) + 1

        # 현재 레벨보다 깊은 카운터 리셋
        for k in list(counters.keys()):
            if k > level:
                del counters[k]

        # 번호 생성: 2부터 현재 레벨까지의 카운터 조합
        parts = []
        for lv in range(2, level + 1):
            parts.append(str(counters.get(lv, 0)))
        number = '.'.join(parts) + '.'

        indent = '  ' * (level - 1)
        numbered.append({
            'level': level,
            'number': number,
            'text': h['text'],
            'anchor': h['anchor'],
        })
        md_lines.append(f'{indent}{number} [{h["text"]}](#{h["anchor"]})')

    return {
        'numbered_toc': numbered,
        'markdown': '\n'.join(md_lines),
    }
