"""
Cliché Detector 서비스

콘텐츠에서 진부한 표현(클리셰)을 감지합니다.
한국어/영어의 흔한 상투적 표현을 찾아 대안을 제안합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict

_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)

# 한국어 클리셰 목록 (카테고리별)
_KO_CLICHES = {
    'opening': [
        (re.compile(r'오늘날\s*(?:현대\s*)?사회에서', re.UNICODE), '오늘날 현대 사회에서'),
        (re.compile(r'(?:급변하는|빠르게\s*변화하는)\s*시대', re.UNICODE), '급변하는 시대'),
        (re.compile(r'4차\s*산업혁명\s*시대', re.UNICODE), '4차 산업혁명 시대'),
        (re.compile(r'누구나\s*(?:한\s*번쯤|한번쯤)', re.UNICODE), '누구나 한 번쯤'),
        (re.compile(r'말할\s*(?:필요도|나위도)\s*없', re.UNICODE), '말할 필요도 없'),
    ],
    'filler': [
        (re.compile(r'다양한\s*(?:방면|측면|관점)에서', re.UNICODE), '다양한 관점에서'),
        (re.compile(r'지대한\s*(?:영향|공헌)', re.UNICODE), '지대한 영향'),
        (re.compile(r'불가분의\s*관계', re.UNICODE), '불가분의 관계'),
        (re.compile(r'(?:삼가|각별한)\s*주의', re.UNICODE), '각별한 주의'),
        (re.compile(r'일석이조', re.UNICODE), '일석이조'),
        (re.compile(r'(?:눈부신|괄목할\s*만한)\s*(?:성장|발전)', re.UNICODE), '눈부신 성장'),
    ],
    'closing': [
        (re.compile(r'(?:다같이|모두\s*함께)\s*(?:노력|힘을)', re.UNICODE), '모두 함께 노력'),
        (re.compile(r'더\s*(?:나은|밝은)\s*(?:미래|내일)', re.UNICODE), '더 나은 미래'),
        (re.compile(r'거듭\s*강조', re.UNICODE), '거듭 강조'),
    ],
}

# 영어 클리셰 목록
_EN_CLICHES = [
    (re.compile(r'\bat\s+the\s+end\s+of\s+the\s+day\b', re.IGNORECASE), 'at the end of the day'),
    (re.compile(r'\bin\s+this\s+day\s+and\s+age\b', re.IGNORECASE), 'in this day and age'),
    (re.compile(r'\bthink\s+outside\s+the\s+box\b', re.IGNORECASE), 'think outside the box'),
    (re.compile(r'\blow\s*-?\s*hanging\s+fruit\b', re.IGNORECASE), 'low-hanging fruit'),
    (re.compile(r'\bgame\s*-?\s*changer\b', re.IGNORECASE), 'game-changer'),
    (re.compile(r'\btip\s+of\s+the\s+iceberg\b', re.IGNORECASE), 'tip of the iceberg'),
    (re.compile(r'\bparadigm\s+shift\b', re.IGNORECASE), 'paradigm shift'),
    (re.compile(r'\bsynergy\b', re.IGNORECASE), 'synergy'),
    (re.compile(r'\blever(?:age|aging)\b', re.IGNORECASE), 'leverage'),
    (re.compile(r'\bscalable\s+solution\b', re.IGNORECASE), 'scalable solution'),
    (re.compile(r'\bneedle\s+in\s+a\s+haystack\b', re.IGNORECASE), 'needle in a haystack'),
    (re.compile(r'\brocket\s+science\b', re.IGNORECASE), 'rocket science'),
]


_EMPTY_RESULT = {
    'cliches': [],
    'summary': {'total_cliches': 0, 'categories': {}, 'level': 'none'},
    'score': 100.0,
    'suggestions': [],
}


def _scan_cliches(cleaned: str) -> tuple:
    """한국어/영어 클리셰를 검색합니다.

    Returns:
        (found_cliches, category_count, total)
    """
    found_cliches = []
    category_count = {}

    for category, patterns in _KO_CLICHES.items():
        for pattern, label in patterns:
            matches = pattern.findall(cleaned)
            if matches:
                found_cliches.append({'text': label, 'category': category,
                                      'language': 'ko', 'count': len(matches)})
                category_count[category] = category_count.get(category, 0) + len(matches)

    for pattern, label in _EN_CLICHES:
        matches = pattern.findall(cleaned)
        if matches:
            found_cliches.append({'text': label, 'category': 'english',
                                  'language': 'en', 'count': len(matches)})
            category_count['english'] = category_count.get('english', 0) + len(matches)

    return found_cliches, category_count, sum(item['count'] for item in found_cliches)


def _compute_cliche_score(total: int) -> tuple:
    """클리셰 점수와 레벨을 계산합니다.

    Returns:
        (score, level)
    """
    if total == 0:
        level = 'clean'
    elif total <= 2:
        level = 'low'
    elif total <= 5:
        level = 'moderate'
    else:
        level = 'high'

    if total == 0:
        score = 100.0
    else:
        score = max(15.0, 100.0 - total ** 1.15 * 8.0)

    return round(max(0.0, min(100.0, score)), 1), level


def detect_cliches(content: str) -> dict:
    """진부한 표현을 감지합니다.

    Returns:
        cliches, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return dict(_EMPTY_RESULT)

    found_cliches, category_count, total = _scan_cliches(_HEADING_RE.sub('', content))
    score, level = _compute_cliche_score(total)

    return {
        'cliches': found_cliches[:20],
        'summary': {'total_cliches': total, 'categories': category_count, 'level': level},
        'score': score,
        'suggestions': _generate_suggestions(found_cliches, total, level),
    }


def _generate_suggestions(cliches: List[Dict], total: int, level: str) -> List[str]:
    suggestions = []
    level_labels = {
        'clean': '깨끗', 'low': '적음',
        'moderate': '보통', 'high': '많음',
    }

    suggestions.append(
        f'클리셰 {total}개 ({level_labels.get(level, level)}).'
    )

    if level in ('moderate', 'high'):
        suggestions.append(
            '진부한 표현이 많습니다. 구체적이고 독창적인 표현으로 바꾸세요.'
        )
        # 대안 제안
        if cliches:
            example = cliches[0]['text']
            suggestions.append(
                f'예: "{example}" → 구체적 사례나 데이터로 대체하세요.'
            )

    return suggestions
