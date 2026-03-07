"""
Absolute Claim Risk Detector 서비스

"항상", "절대", "최고", "보장" 같은 절대 표현이
조건이나 근거 없이 쓰인 문장을 표시합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict

_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')

# 한국어 절대 표현
_KO_ABSOLUTE = [
    re.compile(r'(?:항상|언제나|반드시|절대|절대로|무조건|예외\s*없이)', re.IGNORECASE),
    re.compile(r'(?:최고의|최상의|최강의|최적의|유일한|독보적)', re.IGNORECASE),
    re.compile(r'(?:보장|확실|확정|틀림없이|의심\s*(?:할\s*)?여지\s*없)', re.IGNORECASE),
    re.compile(r'(?:100%|완벽하게|완전히|전혀|절대\s*(?:안|없|불))', re.IGNORECASE),
    re.compile(r'(?:모든\s*(?:경우|상황|사람)|누구나|어디서나)', re.IGNORECASE),
]

# 영어 절대 표현
_EN_ABSOLUTE = [
    re.compile(r'\b(?:always|never|every|all|none|no\s+one|everyone|everything)\b', re.IGNORECASE),
    re.compile(r'\b(?:best|worst|only|guaranteed|proven|definite|absolute|certain)\b', re.IGNORECASE),
    re.compile(r'\b(?:100%|perfect|flawless|impossible|undoubtedly|unquestionably)\b', re.IGNORECASE),
    re.compile(r'\b(?:must|will\s+(?:always|never)|without\s+(?:exception|fail|doubt))\b', re.IGNORECASE),
]

# 조건/한정 표현 (이게 같은 문장에 있으면 OK)
_QUALIFIER_PATTERNS = [
    re.compile(r'(?:일반적으로|대부분|대체로|보통|경우에\s*따라|상황에\s*따라)', re.IGNORECASE),
    re.compile(r'(?:~할\s*수\s*있|~일\s*수\s*있|가능성|경향|추세)', re.IGNORECASE),
    re.compile(r'(?:단,|다만|그러나|하지만|예외|조건)', re.IGNORECASE),
    re.compile(r'\b(?:usually|generally|typically|often|tend|may|might|could|possibly)\b', re.IGNORECASE),
    re.compile(r'\b(?:in\s+most\s+cases|depending\s+on|under\s+certain|with\s+(?:some|few)\s+exceptions)\b', re.IGNORECASE),
]


def _has_absolute(sentence: str) -> List[str]:
    """절대 표현을 찾아 반환합니다."""
    found = []
    seen = set()
    for pat in _KO_ABSOLUTE + _EN_ABSOLUTE:
        for m in pat.finditer(sentence):
            text = m.group().strip()
            if text.lower() not in seen:
                seen.add(text.lower())
                found.append(text)
    return found


def _has_qualifier(sentence: str) -> bool:
    """조건/한정 표현이 있는지 확인합니다."""
    return any(p.search(sentence) for p in _QUALIFIER_PATTERNS)


def detect_absolute_claim_risk(content: str) -> dict:
    """절대 표현의 위험도를 분석합니다.

    Returns:
        score, summary, risky_claims, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'score': 100.0,
            'summary': {
                'total_sentences': 0,
                'absolute_count': 0,
                'qualified_count': 0,
                'unqualified_count': 0,
                'risk_ratio': 0.0,
                'level': 'none',
            },
            'risky_claims': [],
            'suggestions': [],
        }

    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(content) if s.strip() and len(s.strip()) >= 5]

    if not sentences:
        return {
            'score': 100.0,
            'summary': {
                'total_sentences': 0,
                'absolute_count': 0,
                'qualified_count': 0,
                'unqualified_count': 0,
                'risk_ratio': 0.0,
                'level': 'none',
            },
            'risky_claims': [],
            'suggestions': [],
        }

    risky_claims = []
    absolute_count = 0
    qualified_count = 0

    for s in sentences:
        absolutes = _has_absolute(s)
        if absolutes:
            absolute_count += 1
            if _has_qualifier(s):
                qualified_count += 1
            else:
                risky_claims.append({
                    'sentence': s[:80],
                    'absolute_terms': absolutes[:3],
                })

    unqualified = absolute_count - qualified_count
    total = len(sentences)
    risk_ratio = round(unqualified / max(total, 1) * 100, 1)

    # 레벨 판정
    if unqualified == 0:
        level = 'safe'
    elif risk_ratio <= 5:
        level = 'low'
    elif risk_ratio <= 15:
        level = 'moderate'
    else:
        level = 'high'

    # 연속 점수 계산 — risk_ratio(0~100%)를 기반으로 감점
    # risk_ratio 0% → 100점, 5% → 85점, 15% → 60점, 30%+ → 30점
    if risk_ratio == 0:
        score = 100.0
    else:
        score = 100.0 - (risk_ratio * 2.3)  # 30% → ~31점, 15% → ~65.5점, 5% → ~88.5점

    score = round(max(0.0, min(100.0, score)), 1)

    suggestions = _generate_suggestions(
        absolute_count, qualified_count, unqualified,
        risk_ratio, level, risky_claims
    )

    return {
        'score': score,
        'summary': {
            'total_sentences': total,
            'absolute_count': absolute_count,
            'qualified_count': qualified_count,
            'unqualified_count': unqualified,
            'risk_ratio': risk_ratio,
            'level': level,
        },
        'risky_claims': risky_claims[:10],
        'suggestions': suggestions,
    }


def _generate_suggestions(absolute: int, qualified: int,
                           unqualified: int, ratio: float,
                           level: str, claims: List[Dict]) -> List[str]:
    suggestions = []

    level_labels = {
        'safe': '안전', 'low': '낮음',
        'moderate': '보통', 'high': '높음',
    }
    suggestions.append(
        f'절대 표현 위험: {level_labels.get(level, level)}. '
        f'절대 표현 {absolute}건 중 한정 없는 것 {unqualified}건 ({ratio}%).'
    )

    if unqualified > 0:
        suggestions.append(
            '"항상", "절대", "최고" 같은 절대 표현에 '
            '"일반적으로", "대부분의 경우" 등 한정어를 추가하세요.'
        )

    for claim in claims[:2]:
        terms = ', '.join(claim['absolute_terms'])
        suggestions.append(
            f'위험 문장: "{claim["sentence"][:40]}..." — 표현: {terms}'
        )

    return suggestions
