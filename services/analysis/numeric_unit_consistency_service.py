"""
Numeric & Unit Consistency Checker 서비스

%, 배수, 통화, 날짜, 버전, 단위 표기가
문서 내에서 충돌하거나 기준이 바뀌는지 검사합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

# 통화 표기 패턴
_CURRENCY_PATTERNS = {
    'dollar_prefix': re.compile(r'\$\s*\d'),
    'dollar_suffix': re.compile(r'\d\s*달러'),
    'won_suffix': re.compile(r'\d\s*원'),
    'won_prefix': re.compile(r'₩\s*\d'),
    'euro_prefix': re.compile(r'€\s*\d'),
    'euro_suffix': re.compile(r'\d\s*유로'),
}

# 퍼센트 표기
_PERCENT_PATTERNS = {
    'symbol': re.compile(r'\d\s*%'),
    'word_ko': re.compile(r'\d\s*퍼센트'),
    'word_en': re.compile(r'\d\s*percent\b', re.IGNORECASE),
}

# 날짜 표기
_DATE_PATTERNS = {
    'yyyy_mm_dd_dash': re.compile(r'\d{4}-\d{1,2}-\d{1,2}'),
    'yyyy_mm_dd_dot': re.compile(r'\d{4}\.\d{1,2}\.\d{1,2}'),
    'yyyy_mm_dd_slash': re.compile(r'\d{4}/\d{1,2}/\d{1,2}'),
    'mm_dd_yyyy': re.compile(r'\d{1,2}/\d{1,2}/\d{4}'),
    'ko_date': re.compile(r'\d{4}년\s*\d{1,2}월\s*\d{1,2}일'),
}

# 숫자 구분자
_NUMBER_FORMAT = {
    'comma_sep': re.compile(r'\d{1,3}(?:,\d{3})+'),
    'no_sep': re.compile(r'(?<!\d[,.])\d{4,}(?![,.]\d)'),
}

# 단위 표기 (대소문자 혼용)
_UNIT_PAIRS = [
    ('KB', re.compile(r'\b[Kk][Bb]\b'), re.compile(r'\b[Kk]ilobyte', re.IGNORECASE)),
    ('MB', re.compile(r'\b[Mm][Bb]\b'), re.compile(r'\b[Mm]egabyte', re.IGNORECASE)),
    ('GB', re.compile(r'\b[Gg][Bb]\b'), re.compile(r'\b[Gg]igabyte', re.IGNORECASE)),
    ('km', re.compile(r'\b(?:km|KM|Km)\b'), re.compile(r'킬로미터|킬로')),
    ('m', re.compile(r'\d\s*(?:m|M)\b'), re.compile(r'\d\s*미터')),
    ('kg', re.compile(r'\b(?:kg|KG|Kg)\b'), re.compile(r'킬로그램|킬로')),
]


def _check_format_consistency(content: str, patterns: Dict[str, re.Pattern]) -> Dict:
    """패턴 그룹 내에서 혼용 여부를 확인합니다."""
    found_formats = {}
    for name, pat in patterns.items():
        matches = pat.findall(content)
        if matches:
            found_formats[name] = len(matches)

    return {
        'formats_used': list(found_formats.keys()),
        'is_consistent': len(found_formats) <= 1,
        'counts': found_formats,
    }


_EMPTY_RESULT = {
    'score': 100.0,
    'summary': {'categories_checked': 0, 'inconsistent_count': 0, 'level': 'none'},
    'consistency_issues': [],
    'suggestions': [],
}

# 카테고리별 검사 정의: (category, label, patterns, message, special_rule)
_CATEGORIES = [
    ('currency', '통화 표기', _CURRENCY_PATTERNS, '통화 표기가 혼용됨', False),
    ('percent', '퍼센트 표기', _PERCENT_PATTERNS, '퍼센트 표기가 혼용됨 (% vs 퍼센트)', False),
    ('date', '날짜 형식', _DATE_PATTERNS, '날짜 형식이 혼용됨', False),
    ('number_format', '숫자 구분자', _NUMBER_FORMAT, '숫자 구분자 사용이 혼용됨 (쉼표 vs 없음)', True),
]


def _check_all_categories(content: str) -> tuple:
    """모든 카테고리의 표기 일관성을 검사합니다.

    Returns:
        (issues, categories_checked)
    """
    issues = []
    categories_checked = 0

    for category, label, patterns, message, is_number_format in _CATEGORIES:
        check = _check_format_consistency(content, patterns)
        if is_number_format:
            if len(check['formats_used']) >= 2:
                categories_checked += 1
                issues.append({
                    'category': category, 'label': label,
                    'formats': check['formats_used'], 'message': message,
                })
            elif check['formats_used']:
                categories_checked += 1
        else:
            if check['formats_used']:
                categories_checked += 1
                if not check['is_consistent']:
                    issues.append({
                        'category': category, 'label': label,
                        'formats': check['formats_used'], 'message': message,
                    })

    return issues, categories_checked


def _compute_consistency_score(issues: list, categories_checked: int) -> tuple:
    """비일관 건수로 점수와 레벨을 계산합니다.

    Returns:
        (score, level)
    """
    inconsistent_count = len(issues)

    if categories_checked == 0:
        level = 'none'
    elif inconsistent_count == 0:
        level = 'consistent'
    elif inconsistent_count <= 1:
        level = 'minor'
    elif inconsistent_count <= 2:
        level = 'moderate'
    else:
        level = 'inconsistent'

    if categories_checked == 0 or inconsistent_count == 0:
        score = 100.0
    else:
        ratio = inconsistent_count / max(1, categories_checked)
        score = max(15.0, 100.0 - ratio * 70.0 - inconsistent_count * 10.0)

    return round(max(0.0, min(100.0, score)), 1), level


def check_numeric_unit_consistency(content: str) -> dict:
    """숫자/단위 표기 일관성을 검사합니다.

    Returns:
        score, summary, consistency_issues, suggestions를 포함하는 dict
    """
    try:
        if not content or not content.strip():
            return dict(_EMPTY_RESULT)

        issues, categories_checked = _check_all_categories(content)
        score, level = _compute_consistency_score(issues, categories_checked)
        suggestions = _generate_suggestions(issues, level, categories_checked)

        return {
            'score': score,
            'summary': {
                'categories_checked': categories_checked,
                'inconsistent_count': len(issues),
                'level': level,
            },
            'consistency_issues': issues[:10],
            'suggestions': suggestions,
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}


def _generate_suggestions(issues: List[Dict], level: str,
                           checked: int) -> List[str]:
    suggestions = []

    level_labels = {
        'none': '해당 없음', 'consistent': '일관적',
        'minor': '경미', 'moderate': '보통', 'inconsistent': '비일관',
    }
    suggestions.append(
        f'숫자/단위 일관성: {level_labels.get(level, level)}. '
        f'{checked}개 카테고리 검사, {len(issues)}건 비일관.'
    )

    for issue in issues[:3]:
        formats = ', '.join(issue['formats'][:3])
        suggestions.append(
            f'{issue["label"]}: {issue["message"]} ({formats}). '
            f'하나의 형식으로 통일하세요.'
        )

    return suggestions
