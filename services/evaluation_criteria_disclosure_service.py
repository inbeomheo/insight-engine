"""
Evaluation Criteria Disclosure Checker 서비스

리뷰/비교 글에 평가 기준, 테스트 방법, 기준일, 샘플 수 같은
판단 근거가 빠졌는지 확인합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List

# 리뷰/비교 콘텐츠 신호
_REVIEW_SIGNALS = [
    re.compile(r'(?:리뷰|비교|랭킹|평가|테스트|벤치마크|순위)', re.IGNORECASE),
    re.compile(r'(?:베스트|톱\s*\d|추천\s*(?:제품|서비스)|선정)', re.IGNORECASE),
    re.compile(r'\b(?:review|comparison|ranking|benchmark|evaluation|best|top\s*\d)\b', re.IGNORECASE),
]

# 평가 기준 관련 패턴
_CRITERIA_PATTERNS = {
    'evaluation_criteria': [
        re.compile(r'(?:평가\s*(?:기준|항목|지표|요소)|채점\s*기준|점수\s*기준)', re.IGNORECASE),
        re.compile(r'(?:선정\s*(?:기준|이유)|판단\s*(?:기준|근거))', re.IGNORECASE),
        re.compile(r'\b(?:evaluation\s+criteria|scoring\s+(?:criteria|rubric)|rating\s+(?:system|scale))\b', re.IGNORECASE),
    ],
    'test_method': [
        re.compile(r'(?:테스트\s*(?:방법|환경|조건|기간)|실험\s*(?:방법|설계))', re.IGNORECASE),
        re.compile(r'(?:측정\s*(?:방법|도구)|사용\s*(?:환경|조건))', re.IGNORECASE),
        re.compile(r'\b(?:test\s*(?:method|setup|environment|conditions)|methodology|how\s+(?:we|I)\s+tested)\b', re.IGNORECASE),
    ],
    'sample_size': [
        re.compile(r'(?:표본\s*(?:수|크기)|샘플\s*(?:수|크기)|참가자\s*\d)', re.IGNORECASE),
        re.compile(r'(?:\d+\s*(?:명|개|건|대)\s*(?:을|를)?\s*(?:테스트|평가|비교|조사))', re.IGNORECASE),
        re.compile(r'\b(?:sample\s+size|n\s*=\s*\d+|participants?|respondents?)\b', re.IGNORECASE),
    ],
    'test_date': [
        re.compile(r'(?:테스트\s*(?:일|날짜|시점|기간)|작성\s*(?:일|날짜)|기준\s*(?:일|날짜|시점))', re.IGNORECASE),
        re.compile(r'(?:20\d{2}년\s*\d{1,2}월|20\d{2}\.\d{1,2})', re.IGNORECASE),
        re.compile(r'\b(?:tested\s+(?:on|in)|as\s+of|date\s+(?:of|tested)|last\s+updated)\b', re.IGNORECASE),
    ],
    'limitations': [
        re.compile(r'(?:한계|제한\s*(?:사항|점)|주의\s*(?:사항|점)|유의\s*(?:사항|점))', re.IGNORECASE),
        re.compile(r'(?:이\s*(?:리뷰|비교|평가).*?(?:한계|제한|참고))', re.IGNORECASE),
        re.compile(r'\b(?:limitation|caveat|note|disclaimer|important\s+to\s+note)\b', re.IGNORECASE),
    ],
}

_HEADING_RE = re.compile(r'^#{1,3}\s+(.+)$', re.MULTILINE)


def _has_pattern(content: str, patterns: list) -> bool:
    """패턴 중 하나라도 매칭되면 True."""
    return any(p.search(content) for p in patterns)


def _count_matches(content: str, patterns: list) -> int:
    return sum(len(p.findall(content)) for p in patterns)


def check_evaluation_criteria_disclosure(content: str) -> dict:
    """리뷰/비교 글의 평가 기준 공시를 점검합니다.

    Returns:
        score, summary, suggestions, missing_criteria를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'score': 100.0,
            'summary': {
                'is_review_content': False,
                'criteria_found': [],
                'criteria_missing': [],
                'completeness_ratio': 0.0,
                'level': 'none',
            },
            'criteria_details': {},
            'missing_criteria': [],
            'suggestions': [],
        }

    # 리뷰/비교 콘텐츠 여부
    is_review = _count_matches(content, _REVIEW_SIGNALS) >= 2

    # 각 기준 항목 존재 여부
    criteria_found = []
    criteria_missing = []
    criteria_details = {}

    for name, patterns in _CRITERIA_PATTERNS.items():
        found = _has_pattern(content, patterns)
        criteria_details[name] = found
        if found:
            criteria_found.append(name)
        else:
            criteria_missing.append(name)

    # 완성도 비율
    total_criteria = len(_CRITERIA_PATTERNS)
    completeness = round(len(criteria_found) / max(total_criteria, 1) * 100, 1)

    # 레벨 판정
    if not is_review:
        level = 'none'
    elif completeness >= 80:
        level = 'excellent'
    elif completeness >= 60:
        level = 'good'
    elif completeness >= 40:
        level = 'fair'
    else:
        level = 'poor'

    # 연속 점수 — 충족 비율 기반
    if not is_review:
        score = 100.0
    else:
        score = 30.0 + (completeness / 100.0 * 70.0)

    score = round(max(0.0, min(100.0, score)), 1)

    # 라벨 매핑
    criteria_labels = {
        'evaluation_criteria': '평가 기준',
        'test_method': '테스트 방법',
        'sample_size': '표본/샘플 수',
        'test_date': '테스트 날짜',
        'limitations': '한계/주의사항',
    }

    suggestions = _generate_suggestions(
        is_review, criteria_found, criteria_missing,
        completeness, level, criteria_labels
    )

    return {
        'score': score,
        'summary': {
            'is_review_content': is_review,
            'criteria_found': criteria_found,
            'criteria_missing': criteria_missing,
            'completeness_ratio': completeness,
            'level': level,
        },
        'criteria_details': criteria_details,
        'missing_criteria': [
            {'name': m, 'label': criteria_labels.get(m, m)}
            for m in criteria_missing
        ],
        'suggestions': suggestions,
    }


def _generate_suggestions(is_review: bool, found: List[str],
                           missing: List[str], completeness: float,
                           level: str, labels: dict) -> List[str]:
    suggestions = []

    if not is_review:
        suggestions.append('리뷰/비교 콘텐츠가 아닌 것으로 판단됩니다.')
        return suggestions

    level_labels = {
        'excellent': '우수', 'good': '양호',
        'fair': '보통', 'poor': '미흡',
    }

    suggestions.append(
        f'평가 기준 공시: {level_labels.get(level, level)} '
        f'({len(found)}/{len(found) + len(missing)} 항목, {completeness}%).'
    )

    for m in missing[:3]:
        label = labels.get(m, m)
        if m == 'evaluation_criteria':
            suggestions.append(f'"{label}"을 명시하세요. 어떤 기준으로 평가했는지 독자가 알아야 합니다.')
        elif m == 'test_method':
            suggestions.append(f'"{label}"을 설명하세요. 어떤 환경/조건에서 테스트했는지 밝히세요.')
        elif m == 'sample_size':
            suggestions.append(f'"{label}"을 명시하세요. 몇 개의 제품/서비스를 비교했는지 알려주세요.')
        elif m == 'test_date':
            suggestions.append(f'"{label}"을 추가하세요. 정보의 시의성을 위해 기준일이 필요합니다.')
        elif m == 'limitations':
            suggestions.append(f'"{label}"을 추가하세요. 이 평가의 한계를 투명하게 밝히세요.')

    return suggestions
