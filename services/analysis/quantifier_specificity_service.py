"""
Quantifier Specificity Analyzer 서비스

"많은", "일부", "대부분" 같은 모호한 수량 표현을
구체적 수치가 있는 표현과 비교하여 명확성을 평가합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict

_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')

# 모호한 수량 표현 (한국어)
_KO_VAGUE = [
    re.compile(r'(?:많은|다수의|수많은|상당한|상당수)', re.IGNORECASE),
    re.compile(r'(?:일부|몇몇|약간의|소수의|몇\s*가지)', re.IGNORECASE),
    re.compile(r'(?:대부분의?|거의\s*(?:모든|대부분)|대다수)', re.IGNORECASE),
    re.compile(r'(?:꽤\s*(?:많|큰|높)|적지\s*않은|무수한)', re.IGNORECASE),
    re.compile(r'(?:여러|각종|다양한\s*(?:종류|방법|사례))', re.IGNORECASE),
]

# 모호한 수량 표현 (영어)
_EN_VAGUE = [
    re.compile(r'\b(?:many|numerous|lots?\s+of|a\s+lot\s+of|plenty\s+of)\b', re.IGNORECASE),
    re.compile(r'\b(?:some|several|a\s+few|a\s+number\s+of|a\s+couple\s+of)\b', re.IGNORECASE),
    re.compile(r'\b(?:most|almost\s+all|the\s+majority|largely|mostly)\b', re.IGNORECASE),
    re.compile(r'\b(?:significant|substantial|considerable|vast)\b', re.IGNORECASE),
    re.compile(r'\b(?:various|multiple|different\s+(?:types?|kinds?|ways?))\b', re.IGNORECASE),
]

# 구체적 수량 표현
_SPECIFIC_PATTERNS = [
    re.compile(r'\d+\s*(?:%|퍼센트|percent)', re.IGNORECASE),
    re.compile(r'\d+\s*(?:개|건|명|회|편|곳|가지|종류|배|배수)', re.IGNORECASE),
    re.compile(r'\d+\s*(?:times?|people|items?|cases?|types?)\b', re.IGNORECASE),
    re.compile(r'(?:약\s*)?\d+(?:\.\d+)?(?:\s*~\s*\d+)?', re.IGNORECASE),
]


def _find_vague(sentence: str) -> List[str]:
    """모호한 수량 표현을 찾습니다."""
    found = []
    seen = set()
    for pat in _KO_VAGUE + _EN_VAGUE:
        for m in pat.finditer(sentence):
            text = m.group().strip()
            if text.lower() not in seen:
                seen.add(text.lower())
                found.append(text)
    return found


def _has_specific(sentence: str) -> bool:
    """구체적 수치가 있는지 확인합니다."""
    return any(p.search(sentence) for p in _SPECIFIC_PATTERNS)


_EMPTY_RESULT = {
    'score': 100.0,
    'summary': {
        'total_sentences': 0,
        'vague_count': 0,
        'specific_count': 0,
        'specificity_ratio': 0.0,
        'level': 'none',
    },
    'vague_quantifiers': [],
    'suggestions': [],
}


def _scan_quantifiers(sentences: List[str]) -> tuple:
    """문장별 모호/구체적 수량 표현을 스캔합니다.

    Returns:
        (vague_items, vague_count, specific_count)
    """
    vague_items = []
    vague_count = 0
    specific_count = 0

    for s in sentences:
        vague_terms = _find_vague(s)
        has_spec = _has_specific(s)

        if vague_terms:
            vague_count += 1
            if not has_spec:
                vague_items.append({
                    'sentence': s[:80],
                    'vague_terms': vague_terms[:3],
                })
        if has_spec:
            specific_count += 1

    return vague_items, vague_count, specific_count


def _compute_specificity_score(pure_vague: int, specificity_ratio: float) -> tuple:
    """구체성 점수와 레벨을 계산합니다.

    Returns:
        (score, level)
    """
    if pure_vague == 0:
        level = 'specific'
    elif specificity_ratio >= 70:
        level = 'good'
    elif specificity_ratio >= 40:
        level = 'moderate'
    else:
        level = 'vague'

    if pure_vague == 0:
        score = 100.0
    else:
        score = max(15.0, specificity_ratio * 0.85 + 15.0)
        score -= min(15.0, pure_vague * 3.0)

    return round(max(0.0, min(100.0, score)), 1), level


def analyze_quantifier_specificity(content: str) -> dict:
    """수량 표현의 구체성을 분석합니다.

    Returns:
        score, summary, vague_quantifiers, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return dict(_EMPTY_RESULT)

    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(content)
                 if s.strip() and len(s.strip()) >= 5]

    if not sentences:
        return dict(_EMPTY_RESULT)

    vague_items, vague_count, specific_count = _scan_quantifiers(sentences)

    total_quantified = vague_count + specific_count
    specificity_ratio = (round(specific_count / total_quantified * 100, 1)
                         if total_quantified > 0 else 100.0)

    score, level = _compute_specificity_score(len(vague_items), specificity_ratio)

    suggestions = _generate_suggestions(
        vague_count, specific_count, len(vague_items),
        specificity_ratio, level, vague_items
    )

    return {
        'score': score,
        'summary': {
            'total_sentences': len(sentences),
            'vague_count': vague_count,
            'specific_count': specific_count,
            'specificity_ratio': specificity_ratio,
            'level': level,
        },
        'vague_quantifiers': vague_items[:10],
        'suggestions': suggestions,
    }


def _generate_suggestions(vague: int, specific: int,
                           pure_vague: int, ratio: float,
                           level: str, items: List[Dict]) -> List[str]:
    suggestions = []

    level_labels = {
        'specific': '구체적', 'good': '양호',
        'moderate': '보통', 'vague': '모호',
    }
    suggestions.append(
        f'수량 표현 구체성: {level_labels.get(level, level)}. '
        f'구체적 {specific}건, 모호 {vague}건 (구체성 {ratio}%).'
    )

    if pure_vague > 0:
        suggestions.append(
            '"많은", "일부" 같은 모호한 표현을 '
            '"73%", "5가지", "3배" 등 구체적 수치로 교체하세요.'
        )

    for item in items[:2]:
        terms = ', '.join(item['vague_terms'])
        suggestions.append(
            f'모호 문장: "{item["sentence"][:40]}..." — 표현: {terms}'
        )

    return suggestions
