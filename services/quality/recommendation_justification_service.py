"""
Recommendation Justification Analyzer 서비스

추천 항목이 왜 선택됐는지, 누구에게 맞는지,
왜 다른 대안보다 나은지 근거 부족을 감지합니다.
규칙 기반 (AI API 호출 없음).
"""
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

# 추천 항목 패턴 (랭킹/목록)
_ITEM_PATTERNS = [
    re.compile(r'^#{1,3}\s*(?:\d+[\.\)]\s*|TOP\s*\d+\s*[-:]\s*)(.+)', re.MULTILINE | re.IGNORECASE),
    re.compile(r'^(?:\d+[\.\)]\s+)(.{5,50})$', re.MULTILINE),
]

# "왜 추천하는지" 근거 패턴
_WHY_PATTERNS = [
    re.compile(r'(?:이유|근거|때문|왜냐하면|덕분에)', re.IGNORECASE),
    re.compile(r'(?:장점\s*(?:은|이|으로)|강점\s*(?:은|이)|특장점)', re.IGNORECASE),
    re.compile(r'(?:차별\s*(?:점|화)|다른\s*(?:제품|서비스).*?(?:달리|비해|대비))', re.IGNORECASE),
    re.compile(r'\b(?:because|reason|why|advantage|stands?\s+out|unlike|compared\s+to)\b', re.IGNORECASE),
]

# "누구에게 맞는지" 대상 패턴
_BEST_FOR_PATTERNS = [
    re.compile(r'(?:(?:적합|추천).*?(?:대상|분|사람|유저|사용자))', re.IGNORECASE),
    re.compile(r'(?:(?:초보자|전문가|학생|기업|개인|팀).*?(?:에게|한테|을\s*위한|용))', re.IGNORECASE),
    re.compile(r'(?:이런\s*(?:분|사람).*?(?:추천|적합|좋습니다))', re.IGNORECASE),
    re.compile(r'\b(?:best\s+for|ideal\s+for|suited\s+for|recommended\s+for|perfect\s+for)\b', re.IGNORECASE),
]

# 대안 비교 패턴
_COMPARISON_PATTERNS = [
    re.compile(r'(?:(?:보다|대비|비해)\s*(?:나은|좋은|뛰어난|우수한))', re.IGNORECASE),
    re.compile(r'(?:(?:대안|대체|경쟁|vs|versus))', re.IGNORECASE),
    re.compile(r'\b(?:better\s+than|compared\s+(?:to|with)|alternative|versus|vs\.?)\b', re.IGNORECASE),
]

# 추천 콘텐츠 신호
_RECOMMENDATION_SIGNALS = [
    re.compile(r'(?:추천|리뷰|비교|랭킹|베스트|톱\s*\d|top\s*\d)', re.IGNORECASE),
    re.compile(r'\b(?:recommend|review|comparison|ranking|best|top\s*\d)\b', re.IGNORECASE),
]

_HEADING_RE = re.compile(r'^#{1,3}\s+(.+)$', re.MULTILINE)


def _count_matches(content: str, patterns: list) -> int:
    return sum(len(p.findall(content)) for p in patterns)


def _has_pattern(content: str, patterns: list) -> bool:
    return any(p.search(content) for p in patterns)


_EMPTY_RESULT = {
    'score': 100.0,
    'summary': {
        'is_recommendation_content': False, 'total_items': 0,
        'has_why': False, 'has_best_for': False,
        'has_comparison': False, 'justification_level': 'none',
    },
    'missing_why': [],
    'missing_best_for': [],
    'suggestions': [],
}


def _analyze_item_sections(content: str) -> tuple:
    """추천 항목 섹션별 근거 누락을 분석합니다.

    Returns:
        (total_items, missing_why_sections, missing_best_for_sections)
    """
    sections = list(_HEADING_RE.finditer(content))
    missing_why = []
    missing_best_for = []
    total_items = 0

    for i, h in enumerate(sections):
        start = h.end()
        end = sections[i + 1].start() if i + 1 < len(sections) else len(content)
        section_text = content[start:end].strip()
        title = h.group(1).strip()

        if len(section_text) < 30:
            continue

        is_item = bool(re.match(r'\d+[\.\)]', title)) or _has_pattern(title, _RECOMMENDATION_SIGNALS)
        if not is_item:
            continue

        total_items += 1
        if not _has_pattern(section_text, _WHY_PATTERNS):
            missing_why.append(title[:30])
        if not _has_pattern(section_text, _BEST_FOR_PATTERNS):
            missing_best_for.append(title[:30])

    return total_items, missing_why, missing_best_for


def _compute_justification_score(is_rec: bool, has_why: bool, has_best_for: bool,
                                  has_comparison: bool, total_items: int,
                                  missing_why: list) -> tuple:
    """근거 충분성 점수와 레벨을 계산합니다.

    Returns:
        (score, level)
    """
    if not is_rec:
        return 100.0, 'none'

    score_val = sum([has_why, has_best_for, has_comparison])

    if score_val >= 3:
        level = 'thorough'
    elif score_val >= 2:
        level = 'adequate'
    elif score_val >= 1:
        level = 'partial'
    else:
        level = 'missing'

    score = 25.0 + (score_val / 3.0 * 70.0)
    if total_items > 0:
        why_missing_ratio = len(missing_why) / total_items
        score -= min(15.0, why_missing_ratio * 15.0)

    return round(max(0.0, min(100.0, score)), 1), level


def analyze_recommendation_justification(content: str) -> dict:
    """추천 항목의 근거 충분성을 분석합니다.

    Returns:
        score, summary, suggestions, missing_why, missing_best_for를 포함하는 dict
    """
    if not content or not content.strip():
        return dict(_EMPTY_RESULT)
    try:

        is_rec = _count_matches(content, _RECOMMENDATION_SIGNALS) >= 2
        has_why = _count_matches(content, _WHY_PATTERNS) >= 2
        has_best_for = _count_matches(content, _BEST_FOR_PATTERNS) >= 1
        has_comparison = _count_matches(content, _COMPARISON_PATTERNS) >= 1

        total_items, missing_why_sections, missing_best_for_sections = (
            _analyze_item_sections(content)
        )
        score, level = _compute_justification_score(
            is_rec, has_why, has_best_for, has_comparison,
            total_items, missing_why_sections
        )

        suggestions = _generate_suggestions(
            is_rec, has_why, has_best_for, has_comparison,
            level, missing_why_sections, missing_best_for_sections
        )

        return {
            'score': score,
            'summary': {
                'is_recommendation_content': is_rec,
                'total_items': total_items,
                'has_why': has_why,
                'has_best_for': has_best_for,
                'has_comparison': has_comparison,
                'justification_level': level,
            },
            'missing_why': missing_why_sections[:5],
            'missing_best_for': missing_best_for_sections[:5],
            'suggestions': suggestions,
        }
    except Exception as e:
        logger.error(f"추천 근거 분석 처리 실패: {e}")
        return dict(_EMPTY_RESULT)
def _generate_suggestions(is_rec: bool, has_why: bool, has_best_for: bool,
                           has_comparison: bool, level: str,
                           missing_why: List[str],
                           missing_best_for: List[str]) -> List[str]:
    suggestions = []

    if not is_rec:
        suggestions.append('추천/리뷰 콘텐츠가 아닌 것으로 판단됩니다.')
        return suggestions

    level_labels = {
        'thorough': '충분', 'adequate': '적절',
        'partial': '부분적', 'missing': '부족',
    }
    suggestions.append(f'추천 근거 수준: {level_labels.get(level, level)}.')

    if not has_why:
        suggestions.append(
            '각 추천 항목에 "왜 추천하는지" 이유를 명확히 설명하세요.'
        )

    if not has_best_for:
        suggestions.append(
            '"이런 분에게 추천" 또는 "Best for" 섹션을 추가하여 '
            '대상 독자를 명시하세요.'
        )

    if not has_comparison:
        suggestions.append(
            '다른 대안과의 비교를 포함하면 추천 근거가 강화됩니다.'
        )

    for sec in missing_why[:2]:
        suggestions.append(f'"{sec}" 섹션에 추천 이유가 부족합니다.')

    return suggestions
