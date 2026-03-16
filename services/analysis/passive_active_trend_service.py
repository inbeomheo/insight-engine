"""
Passive-to-Active Ratio Trend 서비스

섹션별 능동/피동 구문 비율의 추이를 분석합니다.
특정 섹션에서 피동이 집중되는지, 전체적으로 균일한지 파악합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

_HEADING_RE = re.compile(r'^(#{1,3})\s+(.+)$', re.MULTILINE)
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')

# 한국어 피동 표현
_KO_PASSIVE = [
    re.compile(r'(?:되었|되어|되고|되는|되면|되지|된다|됩니다|됐습니다)'),
    re.compile(r'(?:받았|받고|받는|받게|받을|받습니다)'),
    re.compile(r'(?:당했|당하|당한|당하는|당합니다)'),
    re.compile(r'(?:지어|지게|지는|져서|졌습니다)'),
]

# 영어 수동태
_EN_PASSIVE = re.compile(
    r'\b(?:is|are|was|were|been|being)\s+(?:\w+ed|written|done|made|taken|given|shown|known|found|built|sent|told|seen|held|kept)\b',
    re.IGNORECASE
)


def _is_passive(sentence: str) -> bool:
    for p in _KO_PASSIVE:
        if p.search(sentence):
            return True
    if _EN_PASSIVE.search(sentence):
        return True
    return False


def _split_sections(content: str) -> List[Dict]:
    """콘텐츠를 섹션별로 분할합니다."""
    lines = content.split('\n')
    sections = []
    current_title = '(서론)'
    current_lines = []

    for line in lines:
        if re.match(r'^#{1,3}\s+', line):
            if current_lines:
                text = '\n'.join(current_lines).strip()
                if text:
                    sections.append({'title': current_title, 'text': text})
            current_title = re.sub(r'^#{1,3}\s+', '', line).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        text = '\n'.join(current_lines).strip()
        if text:
            sections.append({'title': current_title, 'text': text})

    return sections


_EMPTY_RESULT = {
    'section_data': [],
    'summary': {
        'total_sections': 0, 'overall_passive_ratio': 0.0,
        'trend': 'none', 'hotspot_section': '',
    },
    'score': 100.0,
    'suggestions': [],
}


def _analyze_sections(sections: List[Dict]) -> tuple:
    """섹션별 능동/피동 비율을 분석합니다.

    Returns:
        (section_data, total_sentences, total_passive, hotspot, max_passive_ratio)
    """
    section_data = []
    total_sentences = 0
    total_passive = 0
    max_passive_ratio = 0.0
    hotspot = ''

    for sec in sections:
        sentences = [s.strip() for s in _SENTENCE_SPLIT.split(sec['text'])
                     if s.strip() and len(s.strip()) >= 5]
        if not sentences:
            continue

        passive_count = sum(1 for s in sentences if _is_passive(s))
        active_count = len(sentences) - passive_count
        ratio = round(passive_count / len(sentences) * 100, 1)

        total_sentences += len(sentences)
        total_passive += passive_count

        if ratio > max_passive_ratio:
            max_passive_ratio = ratio
            hotspot = sec['title']

        section_data.append({
            'title': sec['title'] if len(sec['title']) <= 30 else sec['title'][:27] + '...',
            'sentences': len(sentences),
            'passive': passive_count,
            'active': active_count,
            'passive_ratio': ratio,
        })

    return section_data, total_sentences, total_passive, hotspot, max_passive_ratio


def _determine_trend(section_data: List[Dict]) -> str:
    """섹션별 피동 비율의 추이를 판별합니다."""
    if len(section_data) < 2:
        return 'single'

    ratios = [s['passive_ratio'] for s in section_data]
    if all(ratios[i] == ratios[i + 1] for i in range(len(ratios) - 1)):
        return 'stable'
    if all(ratios[i] <= ratios[i + 1] for i in range(len(ratios) - 1)):
        return 'increasing'
    if all(ratios[i] >= ratios[i + 1] for i in range(len(ratios) - 1)):
        return 'decreasing'

    avg = sum(ratios) / len(ratios)
    max_dev = max(abs(r - avg) for r in ratios)
    return 'uneven' if max_dev > 20 else 'stable'


def _compute_passive_score(overall_ratio: float, trend: str) -> float:
    """전체 피동 비율과 추이로 점수를 계산합니다."""
    if overall_ratio <= 20:
        score = 100.0
    elif overall_ratio <= 35:
        score = 100.0 - (overall_ratio - 20) * 2.0
    else:
        score = max(20.0, 70.0 - (overall_ratio - 35) * 2.0)

    if trend == 'uneven':
        score -= 10.0

    return round(max(0.0, min(100.0, score)), 1)


def analyze_passive_active_trend(content: str) -> dict:
    """섹션별 능동/피동 비율 추이를 분석합니다.

    Returns:
        section_data, summary, score, suggestions를 포함하는 dict
    """
    try:
        if not content or not content.strip():
            return dict(_EMPTY_RESULT)

        sections = _split_sections(content)
        if not sections:
            return dict(_EMPTY_RESULT)

        section_data, total_sentences, total_passive, hotspot, max_passive_ratio = (
            _analyze_sections(sections)
        )
        overall_ratio = round(total_passive / max(total_sentences, 1) * 100, 1)
        trend = _determine_trend(section_data)
        score = _compute_passive_score(overall_ratio, trend)

        suggestions = _generate_suggestions(
            section_data, overall_ratio, trend, hotspot, max_passive_ratio
        )

        return {
            'section_data': section_data[:20],
            'summary': {
                'total_sections': len(section_data),
                'overall_passive_ratio': overall_ratio,
                'trend': trend,
                'hotspot_section': hotspot,
            },
            'score': score,
            'suggestions': suggestions,
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}


def _generate_suggestions(sections: List[Dict], overall: float,
                           trend: str, hotspot: str,
                           max_ratio: float) -> List[str]:
    suggestions = []
    trend_labels = {
        'increasing': '증가', 'decreasing': '감소',
        'stable': '안정', 'uneven': '불균일', 'single': '단일',
    }

    suggestions.append(
        f'전체 피동 비율 {overall}%, 추이: {trend_labels.get(trend, trend)}.'
    )

    if hotspot and max_ratio > 30:
        suggestions.append(
            f'"{hotspot}" 섹션의 피동 비율이 {max_ratio}%로 가장 높습니다. '
            f'이 섹션의 문장을 능동형으로 바꾸세요.'
        )

    if trend == 'increasing':
        suggestions.append(
            '글 후반부로 갈수록 피동 구문이 증가합니다. '
            '결론 부분을 더 직접적으로 작성하세요.'
        )
    elif trend == 'uneven':
        suggestions.append(
            '섹션별 피동 비율 편차가 큽니다. '
            '일관된 문체를 유지하세요.'
        )

    return suggestions
