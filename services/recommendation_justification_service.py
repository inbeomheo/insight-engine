"""
Recommendation Justification Analyzer 서비스

추천 항목이 왜 선택됐는지, 누구에게 맞는지,
왜 다른 대안보다 나은지 근거 부족을 감지합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict

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


def analyze_recommendation_justification(content: str) -> dict:
    """추천 항목의 근거 충분성을 분석합니다.

    Returns:
        score, summary, suggestions, missing_why, missing_best_for를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'score': 100.0,
            'summary': {
                'is_recommendation_content': False,
                'total_items': 0,
                'has_why': False,
                'has_best_for': False,
                'has_comparison': False,
                'justification_level': 'none',
            },
            'missing_why': [],
            'missing_best_for': [],
            'suggestions': [],
        }

    is_rec = _count_matches(content, _RECOMMENDATION_SIGNALS) >= 2

    # 전체 텍스트에서 근거 패턴 탐지
    why_count = _count_matches(content, _WHY_PATTERNS)
    best_for_count = _count_matches(content, _BEST_FOR_PATTERNS)
    comparison_count = _count_matches(content, _COMPARISON_PATTERNS)

    has_why = why_count >= 2
    has_best_for = best_for_count >= 1
    has_comparison = comparison_count >= 1

    # 섹션별 분석
    sections = list(_HEADING_RE.finditer(content))
    missing_why_sections = []
    missing_best_for_sections = []
    total_items = 0

    for i, h in enumerate(sections):
        start = h.end()
        end = sections[i + 1].start() if i + 1 < len(sections) else len(content)
        section_text = content[start:end].strip()
        title = h.group(1).strip()

        if len(section_text) < 30:
            continue

        # 추천 항목 섹션인지 확인 (번호/제목 패턴)
        is_item = bool(re.match(r'\d+[\.\)]', title)) or _has_pattern(title, _RECOMMENDATION_SIGNALS)
        if not is_item:
            continue

        total_items += 1

        if not _has_pattern(section_text, _WHY_PATTERNS):
            missing_why_sections.append(title[:30])

        if not _has_pattern(section_text, _BEST_FOR_PATTERNS):
            missing_best_for_sections.append(title[:30])

    # 근거 수준 판정
    if not is_rec:
        level = 'none'
    else:
        score_val = 0
        if has_why:
            score_val += 1
        if has_best_for:
            score_val += 1
        if has_comparison:
            score_val += 1

        if score_val >= 3:
            level = 'thorough'
        elif score_val >= 2:
            level = 'adequate'
        elif score_val >= 1:
            level = 'partial'
        else:
            level = 'missing'

    # 점수 계산
    if not is_rec:
        score = 100.0
    elif level == 'thorough':
        score = 95.0
    elif level == 'adequate':
        score = 75.0
    elif level == 'partial':
        score = 50.0
    else:
        score = 25.0

    # 섹션별 누락 감점
    if total_items > 0:
        why_missing_ratio = len(missing_why_sections) / total_items
        if why_missing_ratio > 0.5 and score > 30:
            score -= 15.0

    score = round(max(0.0, min(100.0, score)), 1)

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
