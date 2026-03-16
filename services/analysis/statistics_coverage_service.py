"""
Statistics Coverage Analyzer 서비스

콘텐츠의 섹션별 수치 근거(통계, 퍼센트, 금액, 연도 등) 분포를 분석합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


# ── 수치 패턴 정의 ──
_STAT_PATTERNS = [
    (re.compile(r'\d[\d,\.]*\s*(%|퍼센트)'), 'percentage'),
    (re.compile(r'\d[\d,\.]*\s*(원|만원|억원|조원)'), 'currency'),
    (re.compile(r'\$\s*\d[\d,\.]*'), 'currency'),
    (re.compile(r'(?:19|20)\d{2}년'), 'year'),
    (re.compile(r'\b(?:19|20)\d{2}\b'), 'year'),
    (re.compile(r'\d[\d,\.]*\s*배'), 'multiplier'),
    (re.compile(r'\d[\d,\.]*\s*times\b', re.IGNORECASE), 'multiplier'),
    (re.compile(r'\d[\d,\.]*\s*(명|건|개|회|시간|분|초|일|주|개월|톤|km|m|kg)'), 'quantity'),
    (re.compile(r'\d[\d,\.]*\s*(users|cases|hours|days|months|years|items|people)\b', re.IGNORECASE), 'quantity'),
    (re.compile(r'\d[\d,\.]*\s*(대|:)\s*\d[\d,\.]*'), 'ratio'),
]

# ── 마크다운 헤딩 패턴 ──
_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)


def _parse_sections(content: str) -> List[Dict]:
    """콘텐츠를 섹션(헤딩 + 본문)으로 파싱합니다."""
    lines = content.split('\n')
    sections = []
    current_section = {'section': '(서론)', 'content_lines': []}

    for line in lines:
        match = _HEADING_RE.match(line.strip())
        if match:
            if current_section['content_lines'] or current_section['section'] != '(서론)':
                sections.append(current_section)
            current_section = {
                'section': match.group(2).strip(),
                'content_lines': [],
            }
        else:
            current_section['content_lines'].append(line)

    sections.append(current_section)

    if sections and sections[0]['section'] == '(서론)' and not ''.join(sections[0]['content_lines']).strip():
        sections = sections[1:]

    return sections


def _find_statistics(text: str) -> List[Dict]:
    """텍스트에서 수치 패턴을 감지합니다."""
    stats = []
    seen_positions = set()

    for pattern, stat_type in _STAT_PATTERNS:
        for match in pattern.finditer(text):
            pos = match.start()
            if pos not in seen_positions:
                seen_positions.add(pos)
                stats.append({
                    'text': match.group(0).strip(),
                    'type': stat_type,
                    'value': match.group(0).strip(),
                })
    return stats


_EMPTY_RESULT = {
    'statistics': [], 'section_coverage': [],
    'summary': {'total_stats': 0, 'sections_with_stats': 0, 'total_sections': 0, 'coverage_rate': 0.0},
    'score': 0.0, 'suggestions': [],
}


def _scan_section_stats(sections: List[Dict]) -> tuple:
    """각 섹션의 수치 통계를 수집합니다.

    Returns:
        (all_statistics, section_coverage)
    """
    all_statistics = []
    section_coverage = []
    for sec in sections:
        sec_text = '\n'.join(sec['content_lines'])
        sec_stats = _find_statistics(sec_text)
        for stat in sec_stats:
            stat['section'] = sec['section']
            all_statistics.append(stat)
        section_coverage.append({
            'section': sec['section'],
            'stat_count': len(sec_stats),
            'has_stats': len(sec_stats) > 0,
        })
    return all_statistics, section_coverage


def _compute_coverage_score(coverage_rate: float, stat_types: set) -> float:
    """커버리지율과 수치 유형 다양성으로 점수를 계산합니다."""
    type_diversity = min(len(stat_types) * 10, 40)
    return round(max(0.0, min(100.0, coverage_rate * 0.6 + type_diversity)), 1)


def analyze_statistics_coverage(content: str) -> dict:
    """콘텐츠의 수치 근거 커버리지를 분석합니다.

    Args:
        content: 분석할 마크다운/텍스트 콘텐츠

    Returns:
        statistics, section_coverage, summary, score, suggestions를 포함하는 dict
    """
    try:
        if not content or not content.strip():
            return {**_EMPTY_RESULT, 'suggestions': ['콘텐츠가 비어 있습니다.']}

        sections = _parse_sections(content)
        if not sections:
            sections = [{'section': '(전체)', 'content_lines': content.split('\n')}]

        all_statistics, section_coverage = _scan_section_stats(sections)
        total_sections = len(section_coverage)
        sections_with = sum(1 for sc in section_coverage if sc['has_stats'])
        coverage_rate = round((sections_with / total_sections * 100) if total_sections > 0 else 0.0, 1)
        stat_types = set(s['type'] for s in all_statistics)

        return {
            'statistics': all_statistics,
            'section_coverage': section_coverage,
            'summary': {
                'total_stats': len(all_statistics), 'sections_with_stats': sections_with,
                'total_sections': total_sections, 'coverage_rate': coverage_rate,
            },
            'score': _compute_coverage_score(coverage_rate, stat_types),
            'suggestions': _generate_suggestions(all_statistics, section_coverage, coverage_rate, stat_types),
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}


def _generate_suggestions(
    stats: List[Dict], section_coverage: List[Dict],
    coverage_rate: float, stat_types: set,
) -> List[str]:
    """분석 결과 기반 제안을 생성합니다."""
    suggestions = []
    weak_sections = [sc['section'] for sc in section_coverage if not sc['has_stats']]

    if not stats:
        suggestions.append('수치 근거가 전혀 없습니다. 통계, 비율, 사례 수치를 추가하세요.')
        return suggestions

    if weak_sections:
        names = ', '.join(f'"{s}"' for s in weak_sections[:3])
        suggestions.append(f'수치가 없는 섹션: {names}. 해당 섹션에 통계나 구체적 수치를 보강하세요.')

    if coverage_rate >= 80:
        suggestions.append('수치 커버리지가 우수합니다.')
    elif coverage_rate >= 50:
        suggestions.append(f'커버리지 {coverage_rate}%로 양호하나 일부 섹션에 수치 보강이 필요합니다.')
    else:
        suggestions.append(f'커버리지 {coverage_rate}%로 낮습니다. 주요 주장에 수치 근거를 추가하세요.')

    all_types = {'percentage', 'currency', 'year', 'multiplier', 'quantity', 'ratio'}
    missing = all_types - stat_types
    type_labels = {
        'percentage': '퍼센트(%)', 'currency': '금액', 'year': '연도',
        'multiplier': '배수', 'quantity': '수량', 'ratio': '비율',
    }
    if len(missing) >= 3:
        missing_labels = [type_labels[t] for t in list(missing)[:3]]
        suggestions.append(
            f'누락된 수치 유형: {", ".join(missing_labels)}. '
            f'다양한 형태의 수치를 활용하면 설득력이 높아집니다.'
        )
    return suggestions
