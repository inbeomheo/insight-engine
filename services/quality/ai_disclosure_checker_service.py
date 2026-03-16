"""
AI/Automation Disclosure Checker 서비스

AI 작성/보조/자동화 흔적이 있는 문서에서 생성 방식 설명이나
편집 책임 표시 누락을 점검합니다.
규칙 기반 (AI API 호출 없음).
"""
import logging
import re
from typing import List, Dict

logger = logging.getLogger(__name__)

# AI 관련 마커 (한국어)
_KO_AI_MARKERS = [
    re.compile(r'(?:AI\s*(?:작성|생성|보조|활용|기반)|인공지능\s*(?:작성|생성|활용))', re.IGNORECASE),
    re.compile(r'(?:자동\s*(?:생성|작성|번역|요약)|GPT|ChatGPT|Claude|Gemini|LLM)', re.IGNORECASE),
    re.compile(r'(?:대규모\s*언어\s*모델|생성형\s*AI|기계\s*학습\s*(?:기반|활용))', re.IGNORECASE),
]

# AI 관련 마커 (영어)
_EN_AI_MARKERS = [
    re.compile(r'\b(?:AI[- ](?:generated|written|assisted|powered|created))\b', re.IGNORECASE),
    re.compile(r'\b(?:machine[- ](?:generated|written|translated))\b', re.IGNORECASE),
    re.compile(r'\b(?:auto[- ](?:generated|summarized|translated))\b', re.IGNORECASE),
    re.compile(r'\b(?:ChatGPT|GPT-\d|Claude|Gemini|Copilot|LLM|large\s+language\s+model)\b', re.IGNORECASE),
]

# AI 공시 문구 패턴
_AI_DISCLOSURE_PATTERNS = [
    re.compile(r'(?:본\s*(?:글|콘텐츠|기사).*?AI.*?(?:작성|생성|활용|보조))', re.IGNORECASE),
    re.compile(r'(?:AI.*?(?:도움|활용|사용).*?(?:작성|편집|검토))', re.IGNORECASE),
    re.compile(r'(?:(?:편집|검토|감수).*?(?:사람|편집자|전문가|담당자))', re.IGNORECASE),
    re.compile(r'\b(?:written\s+(?:with|by)\s+(?:AI|ChatGPT|Claude|GPT))\b', re.IGNORECASE),
    re.compile(r'\b(?:AI[- ](?:disclosure|notice|generated\s+content))\b', re.IGNORECASE),
    re.compile(r'\b(?:human[- ](?:reviewed|edited|verified))\b', re.IGNORECASE),
    re.compile(r'(?:편집\s*(?:책임|담당)\s*:)', re.IGNORECASE),
]

# 자동화 흔적 (AI가 생성한 텍스트의 특징적 패턴)
_AUTOMATION_TRACES = [
    re.compile(r'(?:요약하자면|결론적으로|종합하면)\s*,?\s*(?:다음과\s*같습니다|아래와\s*같습니다)', re.IGNORECASE),
    re.compile(r'\b(?:as\s+an\s+AI|I\'m\s+an?\s+(?:AI|language\s+model))\b', re.IGNORECASE),
    re.compile(r'(?:도움이\s*되었으면\s*좋겠습니다|궁금한\s*점이\s*있으시면)', re.IGNORECASE),
]


_EMPTY_RESULT = {
    'score': 100.0,
    'summary': {
        'has_ai_markers': False,
        'disclosure_found': False,
        'automation_traces': 0,
        'human_review_noted': False,
    },
    'ai_markers': [],
    'disclosure_markers': [],
    'automation_traces': [],
    'suggestions': [],
}


def _find_matches(content: str, patterns: list) -> List[Dict]:
    """패턴 매칭 결과를 반환합니다."""
    matches = []
    seen = set()
    for pat in patterns:
        for m in pat.finditer(content):
            text = m.group()
            if text.lower() not in seen:
                seen.add(text.lower())
                matches.append({
                    'text': text,
                    'position': m.start(),
                    'position_ratio': round(m.start() / max(len(content), 1) * 100, 1),
                })
    return matches


def _detect_all_markers(content: str) -> tuple:
    """모든 유형의 마커를 탐지합니다.

    Returns:
        (ai_markers, disclosure_markers, trace_matches, human_review)
    """
    ko_markers = _find_matches(content, _KO_AI_MARKERS)
    en_markers = _find_matches(content, _EN_AI_MARKERS)
    ai_markers = ko_markers + en_markers

    disclosure_markers = _find_matches(content, _AI_DISCLOSURE_PATTERNS)
    trace_matches = _find_matches(content, _AUTOMATION_TRACES)

    human_review = any(
        re.search(r'(?:편집|검토|감수|reviewed|edited|verified)', d['text'], re.IGNORECASE)
        for d in disclosure_markers
    )

    return ai_markers, disclosure_markers, trace_matches, human_review


def _compute_disclosure_score(has_ai: bool, has_disclosure: bool,
                               has_traces: bool, human_review: bool) -> float:
    """공시 점수를 계산합니다."""
    score = 100.0
    if has_ai and not has_disclosure:
        score -= 40.0
    elif has_ai and has_disclosure and not human_review:
        score -= 15.0
    if has_traces and not has_disclosure:
        score -= 20.0
    elif has_traces and not has_ai:
        score -= 10.0
    return round(max(0.0, min(100.0, score)), 1)


def check_ai_disclosure(content: str) -> dict:
    """AI 작성/보조 표시 누락을 점검합니다.

    Returns:
        score, summary, suggestions, ai_markers, disclosure_found를 포함하는 dict
    """
    if not content or not content.strip():
        return dict(_EMPTY_RESULT)
    try:

        ai_markers, disclosure_markers, trace_matches, human_review = _detect_all_markers(content)
        has_ai = len(ai_markers) > 0
        has_disclosure = len(disclosure_markers) > 0
        has_traces = len(trace_matches) > 0

        score = _compute_disclosure_score(has_ai, has_disclosure, has_traces, human_review)

        return {
            'score': score,
            'summary': {
                'has_ai_markers': has_ai,
                'disclosure_found': has_disclosure,
                'automation_traces': len(trace_matches),
                'human_review_noted': human_review,
            },
            'ai_markers': ai_markers[:10],
            'disclosure_markers': disclosure_markers[:10],
            'automation_traces': trace_matches[:5],
            'suggestions': _generate_suggestions(
                has_ai, has_disclosure, has_traces,
                human_review, ai_markers, trace_matches, score
            ),
        }
    except Exception as e:
        logger.error(f"AI 공시 점검 처리 실패: {e}")
        return dict(_EMPTY_RESULT)
def _generate_suggestions(has_ai: bool, has_disclosure: bool,
                           has_traces: bool, human_review: bool,
                           ai_markers: List[Dict],
                           traces: List[Dict],
                           score: float) -> List[str]:
    suggestions = []

    if has_ai and not has_disclosure:
        markers_text = ', '.join(m['text'] for m in ai_markers[:3])
        suggestions.append(
            f'AI 관련 표현({markers_text})이 감지되었으나 공시 문구가 없습니다. '
            f'AI 활용 방식과 편집 책임자를 명시하세요.'
        )

    if has_ai and has_disclosure and not human_review:
        suggestions.append(
            'AI 공시는 있으나 편집 책임자(사람)가 명시되지 않았습니다. '
            '"편집 담당: [이름]" 형태로 추가하세요.'
        )

    if has_traces and not has_ai:
        traces_text = ', '.join(f'"{t["text"][:20]}"' for t in traces[:2])
        suggestions.append(
            f'AI 생성 흔적({traces_text})이 감지됩니다. '
            f'AI를 활용했다면 투명하게 공시하세요.'
        )

    if not suggestions:
        if has_ai and has_disclosure and human_review:
            suggestions.append('AI 활용 공시와 편집 책임이 적절히 명시되어 있습니다.')
        else:
            suggestions.append('AI 관련 공시 문제가 발견되지 않았습니다.')

    return suggestions
