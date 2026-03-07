"""
Numeric & Unit Consistency Checker 서비스

%, 배수, 통화, 날짜, 버전, 단위 표기가
문서 내에서 충돌하거나 기준이 바뀌는지 검사합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict

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


def check_numeric_unit_consistency(content: str) -> dict:
    """숫자/단위 표기 일관성을 검사합니다.

    Returns:
        score, summary, consistency_issues, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'score': 100.0,
            'summary': {
                'categories_checked': 0,
                'inconsistent_count': 0,
                'level': 'none',
            },
            'consistency_issues': [],
            'suggestions': [],
        }

    issues = []
    categories_checked = 0

    # 통화 표기 검사
    currency_check = _check_format_consistency(content, _CURRENCY_PATTERNS)
    if currency_check['formats_used']:
        categories_checked += 1
        if not currency_check['is_consistent']:
            issues.append({
                'category': 'currency',
                'label': '통화 표기',
                'formats': currency_check['formats_used'],
                'message': '통화 표기가 혼용됨',
            })

    # 퍼센트 표기 검사
    percent_check = _check_format_consistency(content, _PERCENT_PATTERNS)
    if percent_check['formats_used']:
        categories_checked += 1
        if not percent_check['is_consistent']:
            issues.append({
                'category': 'percent',
                'label': '퍼센트 표기',
                'formats': percent_check['formats_used'],
                'message': '퍼센트 표기가 혼용됨 (% vs 퍼센트)',
            })

    # 날짜 표기 검사
    date_check = _check_format_consistency(content, _DATE_PATTERNS)
    if date_check['formats_used']:
        categories_checked += 1
        if not date_check['is_consistent']:
            issues.append({
                'category': 'date',
                'label': '날짜 형식',
                'formats': date_check['formats_used'],
                'message': '날짜 형식이 혼용됨',
            })

    # 숫자 구분자 검사
    number_check = _check_format_consistency(content, _NUMBER_FORMAT)
    if len(number_check['formats_used']) >= 2:
        categories_checked += 1
        issues.append({
            'category': 'number_format',
            'label': '숫자 구분자',
            'formats': number_check['formats_used'],
            'message': '숫자 구분자 사용이 혼용됨 (쉼표 vs 없음)',
        })
    elif number_check['formats_used']:
        categories_checked += 1

    inconsistent_count = len(issues)

    # 레벨 판정
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

    # 점수 계산
    if level in ('none', 'consistent'):
        score = 100.0
    elif level == 'minor':
        score = 80.0
    elif level == 'moderate':
        score = 55.0
    else:
        score = 30.0

    score = round(max(0.0, min(100.0, score)), 1)

    suggestions = _generate_suggestions(issues, level, categories_checked)

    return {
        'score': score,
        'summary': {
            'categories_checked': categories_checked,
            'inconsistent_count': inconsistent_count,
            'level': level,
        },
        'consistency_issues': issues[:10],
        'suggestions': suggestions,
    }


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
