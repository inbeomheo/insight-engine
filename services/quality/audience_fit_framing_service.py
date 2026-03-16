"""
Audience-Fit Framing Analyzer 서비스

글이 누구에게 맞고, 어떤 상황에서 유효하며,
누구에게는 맞지 않는지 초반에 분명히 밝혔는지 평가합니다.
규칙 기반 (AI API 호출 없음).
"""
import logging
import re
from typing import List, Dict

logger = logging.getLogger(__name__)

# 대상 독자 명시 패턴
_AUDIENCE_PATTERNS = [
    re.compile(r'(?:(?:이\s*글|본\s*(?:글|포스팅|가이드)).*?(?:대상|독자|위한|적합))', re.IGNORECASE),
    re.compile(r'(?:(?:초보자|입문자|전문가|개발자|디자이너|마케터|학생|기업|팀).*?(?:위한|대상|적합|맞는))', re.IGNORECASE),
    re.compile(r'(?:(?:이런\s*분|이런\s*사람|다음.*?분).*?(?:추천|적합|좋습니다))', re.IGNORECASE),
    re.compile(r'\b(?:(?:this|for)\s+(?:beginners?|experts?|developers?|teams?|professionals?))\b', re.IGNORECASE),
    re.compile(r'\b(?:who\s+(?:this|should)\s+(?:is\s+for|read)|target\s+audience|intended\s+for)\b', re.IGNORECASE),
]

# 상황/맥락 명시 패턴
_CONTEXT_PATTERNS = [
    re.compile(r'(?:(?:이\s*방법|이\s*도구).*?(?:적합|유효|효과적|사용).*?(?:경우|상황|때))', re.IGNORECASE),
    re.compile(r'(?:(?:사용\s*(?:사례|케이스)|활용\s*(?:사례|방법)))', re.IGNORECASE),
    re.compile(r'(?:(?:이런|다음)\s*(?:경우|상황).*?(?:유용|적합|효과))', re.IGNORECASE),
    re.compile(r'\b(?:use\s*case|when\s+to\s+use|suitable\s+(?:for|when)|works?\s+(?:best|well)\s+(?:for|when))\b', re.IGNORECASE),
]

# 비적합 대상 패턴 (누구에게 안 맞는지)
_NOT_FOR_PATTERNS = [
    re.compile(r'(?:(?:적합하지|맞지|추천하지)\s*않)', re.IGNORECASE),
    re.compile(r'(?:(?:아닌|안\s*되는)\s*(?:분|사람|경우|상황))', re.IGNORECASE),
    re.compile(r'(?:비추천|주의\s*(?:사항|점))', re.IGNORECASE),
    re.compile(r'\b(?:not\s+(?:for|suitable|recommended|ideal)|avoid\s+if|don\'t\s+use\s+(?:if|when))\b', re.IGNORECASE),
]

# 초반 위치 확인용 (상위 30% 이내)
_POSITION_THRESHOLD = 0.3


def _find_early_matches(content: str, patterns: list) -> List[Dict]:
    """상위 30% 이내에서 패턴 매칭을 찾습니다."""
    matches = []
    threshold = int(len(content) * _POSITION_THRESHOLD)
    for pat in patterns:
        for m in pat.finditer(content):
            matches.append({
                'text': m.group()[:50],
                'position': m.start(),
                'is_early': m.start() <= threshold,
            })
    return matches


def _has_pattern(content: str, patterns: list) -> bool:
    return any(p.search(content) for p in patterns)


def _count_matches(content: str, patterns: list) -> int:
    return sum(len(p.findall(content)) for p in patterns)


_EMPTY_RESULT = {
    'score': 50.0,
    'summary': {'has_audience': False, 'has_context': False, 'has_not_for': False,
                'audience_early': False, 'framing_signals': 0, 'level': 'none'},
    'audience_matches': [],
    'suggestions': [],
}


def _detect_framing_signals(content: str) -> tuple:
    """대상/상황/비적합 신호를 탐지합니다.

    Returns:
        (audience_matches, has_audience, audience_early, has_context, has_not_for)
    """
    audience_matches = _find_early_matches(content, _AUDIENCE_PATTERNS)
    has_audience = len(audience_matches) > 0
    audience_early = any(m['is_early'] for m in audience_matches)
    has_context = _has_pattern(content, _CONTEXT_PATTERNS)
    has_not_for = _has_pattern(content, _NOT_FOR_PATTERNS)
    return audience_matches, has_audience, audience_early, has_context, has_not_for


def _compute_framing_score(has_audience: bool, has_context: bool,
                            has_not_for: bool, audience_early: bool) -> tuple:
    """프레이밍 점수와 레벨을 계산합니다.

    Returns:
        (score, level)
    """
    signals = sum([has_audience, has_context, has_not_for])

    if signals >= 3:
        level = 'comprehensive'
    elif signals >= 2:
        level = 'good'
    elif signals >= 1:
        level = 'partial'
    else:
        level = 'missing'

    score = 25.0
    if has_audience:
        score += 30.0
    if has_context:
        score += 25.0
    if has_not_for:
        score += 20.0
    if audience_early:
        score = min(100.0, score + 10.0)

    return round(max(0.0, min(100.0, score)), 1), level


def analyze_audience_fit_framing(content: str) -> dict:
    """대상 독자/상황/비적합 명시를 분석합니다.

    Returns:
        score, summary, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return dict(_EMPTY_RESULT)
    try:

        audience_matches, has_audience, audience_early, has_context, has_not_for = \
            _detect_framing_signals(content)
        score, level = _compute_framing_score(has_audience, has_context, has_not_for, audience_early)

        return {
            'score': score,
            'summary': {
                'has_audience': has_audience, 'has_context': has_context,
                'has_not_for': has_not_for, 'audience_early': audience_early,
                'framing_signals': sum([has_audience, has_context, has_not_for]),
                'level': level,
            },
            'audience_matches': [m['text'] for m in audience_matches[:5]],
            'suggestions': _generate_suggestions(has_audience, has_context, has_not_for,
                                                  audience_early, level),
        }
    except Exception as e:
        logger.error(f"대상 프레이밍 분석 처리 실패: {e}")
        return dict(_EMPTY_RESULT)
def _generate_suggestions(has_audience: bool, has_context: bool,
                           has_not_for: bool, early: bool,
                           level: str) -> List[str]:
    suggestions = []

    level_labels = {
        'comprehensive': '포괄적', 'good': '양호',
        'partial': '부분적', 'missing': '없음',
    }
    suggestions.append(
        f'대상 프레이밍: {level_labels.get(level, level)}.'
    )

    if not has_audience:
        suggestions.append(
            '"이 글은 ~를 위한 글입니다" 형태로 대상 독자를 명시하세요.'
        )

    if has_audience and not early:
        suggestions.append(
            '대상 독자 정보를 글 상단(첫 30% 이내)에 배치하세요.'
        )

    if not has_context:
        suggestions.append(
            '"이런 경우에 유용합니다" 또는 "Use case" 섹션을 추가하세요.'
        )

    if not has_not_for:
        suggestions.append(
            '"이런 분에게는 맞지 않습니다" 또는 "Not for" 안내를 추가하세요.'
        )

    return suggestions
