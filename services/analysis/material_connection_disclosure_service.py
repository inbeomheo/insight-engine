"""
Material Connection Disclosure Checker 서비스

제휴/협찬/무료제공 등 이해관계 공시 누락 및 위치 부적절을 점검합니다.
FTC 가이드라인 기반 규칙 적용.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict

# 한국어 이해관계 키워드
_KO_MATERIAL = [
    re.compile(r'(?:제휴|협찬|무료\s*제공|광고|스폰서|후원|유료\s*광고|제공\s*받)', re.IGNORECASE),
    re.compile(r'(?:파트너십|수수료|커미션|대가\s*없)', re.IGNORECASE),
    re.compile(r'(?:쿠팡\s*파트너스|애드\s*포스트|체험단|원고료)', re.IGNORECASE),
]

# 영어 이해관계 키워드
_EN_MATERIAL = [
    re.compile(r'\b(?:sponsored|affiliate|partnership|commission|complimentary|gifted|paid\s+promotion)\b', re.IGNORECASE),
    re.compile(r'\b(?:free\s+(?:product|sample|copy)|brand\s+(?:deal|partner)|endorsement)\b', re.IGNORECASE),
    re.compile(r'\b(?:FTC|disclosure|material\s+connection|ad|#ad|#sponsored)\b', re.IGNORECASE),
]

# 공시 문구 패턴 (적절한 공시가 있는지 확인)
_DISCLOSURE_PATTERNS = [
    re.compile(r'(?:본\s*(?:포스팅|글|콘텐츠|리뷰).*?(?:제공|협찬|광고|제휴))', re.IGNORECASE),
    re.compile(r'(?:(?:제공|협찬|광고|제휴).*?(?:포함|있습니다|됩니다|밝힙니다))', re.IGNORECASE),
    re.compile(r'(?:이\s*글은\s*(?:광고|협찬|제휴))', re.IGNORECASE),
    re.compile(r'(?:소정의\s*(?:원고료|대가|수수료))', re.IGNORECASE),
    re.compile(r'\b(?:this\s+(?:post|article|review)\s+(?:contains|includes|is)\s+(?:affiliate|sponsored|paid))\b', re.IGNORECASE),
    re.compile(r'\b(?:disclosure|disclaimer)\s*:', re.IGNORECASE),
    re.compile(r'#(?:ad|광고|협찬|sponsored)\b', re.IGNORECASE),
]

# 추천/리뷰 콘텐츠 신호
_REVIEW_SIGNALS = [
    re.compile(r'(?:추천|리뷰|비교|랭킹|베스트|톱\s*\d|top\s*\d)', re.IGNORECASE),
    re.compile(r'(?:구매\s*(?:링크|가이드)|할인\s*코드|쿠폰)', re.IGNORECASE),
    re.compile(r'\b(?:review|recommend|best|ranking|buy|purchase)\b', re.IGNORECASE),
]

_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')


def _find_matches(content: str, patterns: list) -> List[Dict]:
    """패턴 매칭 결과를 반환합니다."""
    matches = []
    for pat in patterns:
        for m in pat.finditer(content):
            matches.append({
                'text': m.group(),
                'position': m.start(),
                'position_ratio': round(m.start() / max(len(content), 1) * 100, 1),
            })
    return matches


_EMPTY_RESULT = {
    'score': 100.0,
    'summary': {
        'has_material_connection': False, 'disclosure_found': False,
        'review_content': False, 'placement_ok': True, 'material_markers': 0,
    },
    'material_markers': [],
    'disclosure_markers': [],
    'suggestions': [],
}


def _detect_signals(content: str) -> tuple:
    """이해관계/공시/리뷰 신호를 탐지합니다.

    Returns:
        (material_markers, disclosure_markers, is_review)
    """
    material_markers = _find_matches(content, _KO_MATERIAL) + _find_matches(content, _EN_MATERIAL)
    disclosure_markers = _find_matches(content, _DISCLOSURE_PATTERNS)
    is_review = len(_find_matches(content, _REVIEW_SIGNALS)) > 0
    return material_markers, disclosure_markers, is_review


def _evaluate_placement(disclosure_markers: list) -> tuple:
    """공시 위치를 평가합니다.

    Returns:
        (placement_ok, placement_issues)
    """
    placement_issues = []
    for d in disclosure_markers:
        if d['position_ratio'] > 50:
            placement_issues.append(
                f"공시 문구 \"{d['text'][:20]}...\"가 글의 {d['position_ratio']}% 위치에 있습니다. "
                f"상단(20% 이내)에 배치하세요."
            )
    return len(placement_issues) == 0, placement_issues


def _compute_disclosure_score(has_material: bool, has_disclosure: bool,
                               is_review: bool, placement_ok: bool) -> float:
    """공시 점수를 계산합니다."""
    score = 100.0
    if has_material and not has_disclosure:
        score -= 50.0
    elif has_material and has_disclosure and not placement_ok:
        score -= 20.0
    elif is_review and not has_material and not has_disclosure:
        score -= 5.0
    return round(max(0.0, min(100.0, score)), 1)


def check_material_connection_disclosure(content: str) -> dict:
    """제휴/협찬 공시 누락 및 위치를 점검합니다.

    Returns:
        score, summary, suggestions, material_markers, disclosure_markers를 포함하는 dict
    """
    if not content or not content.strip():
        return dict(_EMPTY_RESULT)

    material_markers, disclosure_markers, is_review = _detect_signals(content)
    has_material = len(material_markers) > 0
    has_disclosure = len(disclosure_markers) > 0
    placement_ok, placement_issues = _evaluate_placement(disclosure_markers)
    score = _compute_disclosure_score(has_material, has_disclosure, is_review, placement_ok)

    return {
        'score': score,
        'summary': {
            'has_material_connection': has_material,
            'disclosure_found': has_disclosure,
            'review_content': is_review,
            'placement_ok': placement_ok,
            'material_markers': len(material_markers),
        },
        'material_markers': material_markers[:10],
        'disclosure_markers': disclosure_markers[:10],
        'suggestions': _generate_suggestions(
            has_material, has_disclosure, is_review,
            placement_ok, placement_issues, material_markers, score
        ),
    }


def _generate_suggestions(has_material: bool, has_disclosure: bool,
                           is_review: bool, placement_ok: bool,
                           placement_issues: List[str],
                           material_markers: List[Dict],
                           score: float) -> List[str]:
    suggestions = []

    if has_material and not has_disclosure:
        suggestions.append(
            '이해관계(제휴/협찬/무료제공)가 감지되었으나 공시 문구가 없습니다. '
            '글 상단에 명확한 공시를 추가하세요.'
        )
        markers_text = ', '.join(m['text'] for m in material_markers[:3])
        suggestions.append(f'감지된 이해관계 표현: {markers_text}')

    if has_material and has_disclosure and not placement_ok:
        suggestions.extend(placement_issues[:3])

    if is_review and not has_material:
        suggestions.append(
            '추천/리뷰 콘텐츠입니다. 이해관계가 있다면 반드시 공시하세요.'
        )

    if not suggestions:
        if has_material and has_disclosure and placement_ok:
            suggestions.append('이해관계 공시가 적절히 배치되어 있습니다.')
        else:
            suggestions.append('이해관계 공시 관련 문제가 발견되지 않았습니다.')

    return suggestions
