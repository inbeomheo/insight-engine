"""
Conclusion Strength Analyzer 서비스

콘텐츠 결론부의 강도를 평가합니다.
요약, CTA, 핵심 메시지 재확인 등 결론 요소를 점검합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict


_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

# 결론 헤딩 패턴
_CONCLUSION_HEADING = re.compile(
    r'(?:결론|마무리|정리|요약|마치며|끝으로|결말|Conclusion|Summary|Wrap|Final)',
    re.IGNORECASE
)

# 요약 신호
_SUMMARY_SIGNALS = [
    re.compile(r'(?:요약하면|정리하면|다시\s*말해|한마디로|핵심은)'),
    re.compile(r'\b(?:in\s+summary|to\s+summarize|in\s+short|to\s+sum\s+up)\b', re.IGNORECASE),
    re.compile(r'\b(?:tl;?\s*dr|key\s+takeaway|bottom\s+line)\b', re.IGNORECASE),
]

# CTA(행동 유도) 신호
_CTA_SIGNALS = [
    re.compile(r'(?:시작하세요|시도해\s*보세요|도전해\s*보세요|확인해\s*보세요|방문하세요)'),
    re.compile(r'(?:지금\s*바로|오늘부터|당장)'),
    re.compile(r'\b(?:try\s+it|get\s+started|sign\s+up|learn\s+more|check\s+out)\b', re.IGNORECASE),
    re.compile(r'\b(?:start\s+(?:now|today)|take\s+action)\b', re.IGNORECASE),
]

# 미래 전망 신호
_FORWARD_SIGNALS = [
    re.compile(r'(?:앞으로|향후|미래에|다음\s*단계|발전)'),
    re.compile(r'\b(?:moving\s+forward|in\s+the\s+future|next\s+step|going\s+forward)\b', re.IGNORECASE),
]

# 핵심 재확인 신호
_REAFFIRM_SIGNALS = [
    re.compile(r'(?:가장\s*중요한|결국|궁극적으로|무엇보다)'),
    re.compile(r'\b(?:most\s+important(?:ly)?|ultimately|above\s+all)\b', re.IGNORECASE),
]


def _get_conclusion_section(content: str) -> str:
    """콘텐츠 마지막 20% 또는 결론 헤딩 이후 텍스트를 추출합니다."""
    # 결론 헤딩 찾기
    last_conclusion = None
    for match in _HEADING_RE.finditer(content):
        heading_text = match.group(2).strip()
        if _CONCLUSION_HEADING.search(heading_text):
            last_conclusion = match.end()

    if last_conclusion is not None:
        return content[last_conclusion:]

    # 결론 헤딩이 없으면 마지막 20%
    total_len = len(content)
    return content[int(total_len * 0.8):]


def analyze_conclusion_strength(content: str) -> dict:
    """결론부의 강도를 분석합니다.

    Returns:
        elements, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'elements': {},
            'summary': {'has_conclusion_heading': False, 'element_count': 0,
                        'strength_level': 'none'},
            'score': 0.0,
            'suggestions': ['콘텐츠가 비어 있습니다.'],
        }

    conclusion = _get_conclusion_section(content)

    # 결론 헤딩 존재 여부
    has_heading = bool(_CONCLUSION_HEADING.search(content))

    # 결론 요소 감지
    has_summary = any(p.search(conclusion) for p in _SUMMARY_SIGNALS)
    has_cta = any(p.search(conclusion) for p in _CTA_SIGNALS)
    has_forward = any(p.search(conclusion) for p in _FORWARD_SIGNALS)
    has_reaffirm = any(p.search(conclusion) for p in _REAFFIRM_SIGNALS)

    elements = {
        'conclusion_heading': has_heading,
        'summary_statement': has_summary,
        'call_to_action': has_cta,
        'forward_looking': has_forward,
        'key_reaffirmation': has_reaffirm,
    }

    element_count = sum(1 for v in elements.values() if v)

    # 점수: 요소 수 기반 (5개 만점)
    score = round(min(100.0, element_count * 20.0), 1)

    # 강도 레벨
    if element_count >= 4:
        level = 'strong'
    elif element_count >= 2:
        level = 'moderate'
    elif element_count >= 1:
        level = 'weak'
    else:
        level = 'none'

    suggestions = _generate_suggestions(elements, level, element_count)

    return {
        'elements': elements,
        'summary': {
            'has_conclusion_heading': has_heading,
            'element_count': element_count,
            'strength_level': level,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _generate_suggestions(elements: Dict, level: str, count: int) -> List[str]:
    suggestions = []
    level_labels = {'strong': '강한', 'moderate': '보통', 'weak': '약한', 'none': '없는'}
    suggestions.append(f'결론 강도: {level_labels.get(level, level)} ({count}/5 요소).')

    missing = []
    if not elements['conclusion_heading']:
        missing.append('결론 헤딩')
    if not elements['summary_statement']:
        missing.append('요약문')
    if not elements['call_to_action']:
        missing.append('행동 유도(CTA)')
    if not elements['forward_looking']:
        missing.append('미래 전망')

    if missing:
        names = ', '.join(missing[:3])
        suggestions.append(f'부족한 요소: {names}. 추가하면 결론이 강화됩니다.')
    return suggestions
