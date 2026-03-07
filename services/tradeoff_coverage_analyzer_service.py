"""
Trade-off Coverage Analyzer 서비스

추천형 콘텐츠가 장점만 나열하고 단점/한계/비추천 대상을 누락했는지 분석합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict

# 긍정 표현 (한국어 + 영어)
_POSITIVE_PATTERNS = [
    re.compile(r'(?:장점|강점|이점|좋은\s*점|뛰어난|우수한|편리한|효율적)', re.IGNORECASE),
    re.compile(r'(?:추천|최고|최적|완벽|탁월|훌륭한|강력한|혁신적)', re.IGNORECASE),
    re.compile(r'\b(?:advantage|strength|benefit|excellent|superior|great|amazing|best)\b', re.IGNORECASE),
    re.compile(r'\b(?:recommended|perfect|outstanding|powerful|innovative)\b', re.IGNORECASE),
]

# 부정/한계 표현 (한국어 + 영어)
_NEGATIVE_PATTERNS = [
    re.compile(r'(?:단점|약점|한계|아쉬운\s*점|부족한|불편한|개선\s*(?:필요|사항))', re.IGNORECASE),
    re.compile(r'(?:주의\s*(?:사항|점)|비추천|제한\s*(?:사항|적)|리스크|위험)', re.IGNORECASE),
    re.compile(r'(?:그러나|하지만|반면|다만|아쉽게도)', re.IGNORECASE),
    re.compile(r'\b(?:disadvantage|weakness|limitation|drawback|downside|caveat)\b', re.IGNORECASE),
    re.compile(r'\b(?:however|but|although|despite|unfortunately|risk|caution)\b', re.IGNORECASE),
    re.compile(r'\b(?:not\s+(?:recommended|suitable|ideal)|cons?)\b', re.IGNORECASE),
]

# 역접 패턴 (장단점 균형 지표)
_CONTRAST_PATTERNS = [
    re.compile(r'(?:장점.*단점|단점.*장점|pros.*cons|cons.*pros)', re.IGNORECASE | re.DOTALL),
    re.compile(r'(?:좋은\s*점.*아쉬운\s*점|아쉬운\s*점.*좋은\s*점)', re.IGNORECASE | re.DOTALL),
]

# 대상 제한 패턴 (누구에게 안 맞는지)
_TARGET_LIMIT_PATTERNS = [
    re.compile(r'(?:(?:적합하지|맞지|추천하지)\s*않)', re.IGNORECASE),
    re.compile(r'(?:(?:초보자|전문가|기업|개인).*?(?:에게는|에겐)\s*(?:부적합|어려울|맞지))', re.IGNORECASE),
    re.compile(r'\b(?:not\s+(?:for|suitable\s+for|recommended\s+for))\b', re.IGNORECASE),
    re.compile(r'(?:비추천\s*대상|추천하지\s*않는\s*(?:사람|경우|분))', re.IGNORECASE),
]

# 추천 콘텐츠 신호
_RECOMMENDATION_SIGNALS = [
    re.compile(r'(?:추천|리뷰|비교|랭킹|베스트|톱\s*\d|top\s*\d)', re.IGNORECASE),
    re.compile(r'\b(?:review|recommend|comparison|ranking|best|top\s*\d)\b', re.IGNORECASE),
]

_HEADING_RE = re.compile(r'^#{1,3}\s+(.+)$', re.MULTILINE)


def _count_matches(content: str, patterns: list) -> int:
    """패턴 매칭 수를 반환합니다."""
    count = 0
    for pat in patterns:
        count += len(pat.findall(content))
    return count


def _find_matches_list(content: str, patterns: list) -> List[str]:
    """매칭된 텍스트 목록을 반환합니다."""
    matches = []
    seen = set()
    for pat in patterns:
        for m in pat.finditer(content):
            text = m.group().strip()
            if text.lower() not in seen:
                seen.add(text.lower())
                matches.append(text)
    return matches


def analyze_tradeoff_coverage(content: str) -> dict:
    """장단점 균형을 분석합니다.

    Returns:
        score, summary, suggestions, one_sided_sections를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'score': 100.0,
            'summary': {
                'is_recommendation_content': False,
                'positive_count': 0,
                'negative_count': 0,
                'balance_ratio': 0.0,
                'has_contrast': False,
                'has_target_limits': False,
                'level': 'none',
            },
            'positive_expressions': [],
            'negative_expressions': [],
            'one_sided_sections': [],
            'suggestions': [],
        }

    # 추천 콘텐츠 여부
    is_rec = _count_matches(content, _RECOMMENDATION_SIGNALS) > 0

    # 긍정/부정 표현 수
    positive_count = _count_matches(content, _POSITIVE_PATTERNS)
    negative_count = _count_matches(content, _NEGATIVE_PATTERNS)

    positive_exprs = _find_matches_list(content, _POSITIVE_PATTERNS)
    negative_exprs = _find_matches_list(content, _NEGATIVE_PATTERNS)

    # 역접 패턴 여부
    has_contrast = _count_matches(content, _CONTRAST_PATTERNS) > 0

    # 대상 제한 여부
    has_target_limits = _count_matches(content, _TARGET_LIMIT_PATTERNS) > 0

    # 균형 비율 (부정 / 전체)
    total = positive_count + negative_count
    balance_ratio = round(negative_count / max(total, 1) * 100, 1)

    # 섹션별 편향 분석
    one_sided = _find_one_sided_sections(content)

    # 레벨 판정
    if not is_rec or total == 0:
        level = 'none'
    elif balance_ratio >= 25 and has_contrast:
        level = 'balanced'
    elif balance_ratio >= 15:
        level = 'acceptable'
    elif balance_ratio >= 5:
        level = 'one_sided'
    else:
        level = 'heavily_one_sided'

    # 연속 점수 — balance_ratio 기반
    if not is_rec or total == 0:
        score = 100.0
    else:
        score = 30.0 + (min(balance_ratio, 30.0) / 30.0 * 60.0)
        if has_contrast:
            score += 5.0
        if has_target_limits:
            score += 5.0

    score = round(max(0.0, min(100.0, score)), 1)

    suggestions = _generate_suggestions(
        is_rec, positive_count, negative_count,
        balance_ratio, has_contrast, has_target_limits,
        level, one_sided
    )

    return {
        'score': score,
        'summary': {
            'is_recommendation_content': is_rec,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'balance_ratio': balance_ratio,
            'has_contrast': has_contrast,
            'has_target_limits': has_target_limits,
            'level': level,
        },
        'positive_expressions': positive_exprs[:10],
        'negative_expressions': negative_exprs[:10],
        'one_sided_sections': one_sided[:5],
        'suggestions': suggestions,
    }


def _find_one_sided_sections(content: str) -> List[Dict]:
    """긍정만 있는 섹션을 찾습니다."""
    headings = list(_HEADING_RE.finditer(content))
    if not headings:
        return []

    sections = []
    for i, h in enumerate(headings):
        start = h.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(content)
        section_text = content[start:end].strip()
        if len(section_text) < 20:
            continue

        pos = _count_matches(section_text, _POSITIVE_PATTERNS)
        neg = _count_matches(section_text, _NEGATIVE_PATTERNS)

        if pos >= 3 and neg == 0:
            sections.append({
                'title': h.group(1).strip()[:30],
                'positive': pos,
                'negative': neg,
            })

    return sections


def _generate_suggestions(is_rec: bool, pos: int, neg: int,
                           ratio: float, has_contrast: bool,
                           has_limits: bool, level: str,
                           one_sided: List[Dict]) -> List[str]:
    suggestions = []

    if not is_rec:
        suggestions.append('추천/리뷰 콘텐츠가 아닌 것으로 판단됩니다.')
        return suggestions

    level_labels = {
        'balanced': '균형적', 'acceptable': '수용 가능',
        'one_sided': '편향적', 'heavily_one_sided': '심각하게 편향적',
    }

    suggestions.append(
        f'장단점 균형: {level_labels.get(level, level)}. '
        f'긍정 {pos}건, 부정 {neg}건 (부정 비율 {ratio}%).'
    )

    if level in ('one_sided', 'heavily_one_sided'):
        suggestions.append(
            '단점, 한계, 주의사항을 추가하여 균형 잡힌 리뷰를 작성하세요.'
        )

    if not has_contrast and pos > 0 and neg > 0:
        suggestions.append(
            '"장점/단점" 또는 "Pros/Cons" 섹션을 분리하면 가독성이 높아집니다.'
        )

    if not has_limits and is_rec:
        suggestions.append(
            '"추천하지 않는 경우" 또는 "이런 분에게는 비추천" 섹션을 추가하세요.'
        )

    for sec in one_sided[:2]:
        suggestions.append(
            f'"{sec["title"]}" 섹션에 긍정 표현만 {sec["positive"]}건 있습니다. '
            f'한계나 주의사항을 추가하세요.'
        )

    return suggestions
