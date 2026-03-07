"""
Geo Scope Assumption Detector 서비스

가격, 법규, 세금, 배송, 정책 등 지역 의존 정보가
국가/지역 라벨 없이 단정적으로 쓰인 부분을 탐지합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict

# 지역 의존 키워드 (라벨 없이 쓰이면 문제)
_GEO_SENSITIVE_CATEGORIES = {
    'price': {
        'label': '가격/통화',
        'patterns': [
            re.compile(r'(?:가격|요금|비용|월\s*\d|연\s*\d).*?(?:원|만원|\$|달러|유로|엔)', re.IGNORECASE),
            re.compile(r'(?:\$\d|₩\d|€\d|¥\d)', re.IGNORECASE),
        ],
    },
    'tax': {
        'label': '세금/관세',
        'patterns': [
            re.compile(r'(?:세금|부가세|VAT|관세|세율|면세|소득세|법인세)', re.IGNORECASE),
            re.compile(r'\b(?:tax|VAT|duty|tariff|GST|sales\s*tax)\b', re.IGNORECASE),
        ],
    },
    'regulation': {
        'label': '법규/규제',
        'patterns': [
            re.compile(r'(?:법률|규정|규제|합법|불법|허가|면허|인증|법적)', re.IGNORECASE),
            re.compile(r'\b(?:legal|illegal|regulation|compliance|license|permit|law)\b', re.IGNORECASE),
        ],
    },
    'shipping': {
        'label': '배송/물류',
        'patterns': [
            re.compile(r'(?:배송|택배|무료\s*배송|배송비|배송\s*기간)', re.IGNORECASE),
            re.compile(r'\b(?:shipping|delivery|free\s*shipping|freight)\b', re.IGNORECASE),
        ],
    },
    'availability': {
        'label': '가용성/서비스 지역',
        'patterns': [
            re.compile(r'(?:서비스\s*(?:지역|범위)|이용\s*(?:가능|불가)|출시|런칭)', re.IGNORECASE),
            re.compile(r'\b(?:available\s+in|not\s+available|launch|rollout|region)\b', re.IGNORECASE),
        ],
    },
}

# 지역 라벨 패턴 (이게 있으면 OK)
_GEO_LABEL_PATTERNS = [
    re.compile(r'(?:한국|미국|일본|중국|유럽|영국|독일|프랑스|호주|캐나다)', re.IGNORECASE),
    re.compile(r'(?:국내|해외|글로벌|현지|북미|아시아|EU)', re.IGNORECASE),
    re.compile(r'\b(?:US|USA|UK|EU|Korea|Japan|China|Canada|Australia|global|domestic|international)\b', re.IGNORECASE),
    re.compile(r'(?:기준\s*(?:국가|지역)|적용\s*(?:국가|지역))', re.IGNORECASE),
]


def _has_pattern(content: str, patterns: list) -> bool:
    return any(p.search(content) for p in patterns)


def _find_matches(content: str, patterns: list) -> List[str]:
    matches = []
    seen = set()
    for pat in patterns:
        for m in pat.finditer(content):
            text = m.group().strip()
            if text.lower() not in seen:
                seen.add(text.lower())
                matches.append(text)
    return matches


def detect_geo_scope_assumptions(content: str) -> dict:
    """지역 의존 정보의 범위 라벨 누락을 탐지합니다.

    Returns:
        score, summary, unlabeled_scope_issues, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'score': 100.0,
            'summary': {
                'geo_sensitive_found': [],
                'has_geo_label': False,
                'unlabeled_count': 0,
                'level': 'none',
            },
            'geo_sensitive_terms': [],
            'unlabeled_scope_issues': [],
            'suggestions': [],
        }

    # 지역 의존 카테고리 탐지
    sensitive_found = []
    sensitive_terms = []
    for cat_name, cat_info in _GEO_SENSITIVE_CATEGORIES.items():
        if _has_pattern(content, cat_info['patterns']):
            sensitive_found.append(cat_name)
            terms = _find_matches(content, cat_info['patterns'])
            for t in terms[:3]:
                sensitive_terms.append({'category': cat_name, 'label': cat_info['label'], 'text': t})

    # 지역 라벨 존재 여부
    has_geo_label = _has_pattern(content, _GEO_LABEL_PATTERNS)

    # 라벨 없는 민감 항목
    unlabeled = []
    if sensitive_found and not has_geo_label:
        for cat in sensitive_found:
            unlabeled.append({
                'category': cat,
                'label': _GEO_SENSITIVE_CATEGORIES[cat]['label'],
                'issue': '지역/국가 라벨 없이 사용됨',
            })

    # 레벨 판정
    if not sensitive_found:
        level = 'none'
    elif has_geo_label and not unlabeled:
        level = 'labeled'
    elif has_geo_label and unlabeled:
        level = 'partial'
    else:
        level = 'unlabeled'

    # 연속 점수 — 라벨 충족 비율 기반
    if not sensitive_found:
        score = 100.0
    elif has_geo_label and not unlabeled:
        score = 95.0
    else:
        labeled_ratio = 1.0 - (len(unlabeled) / max(1, len(sensitive_found)))
        score = 35.0 + (labeled_ratio * 55.0)
        score -= min(15.0, len(sensitive_found) * 3.0)

    score = round(max(0.0, min(100.0, score)), 1)

    suggestions = _generate_suggestions(
        sensitive_found, has_geo_label, unlabeled, level
    )

    return {
        'score': score,
        'summary': {
            'geo_sensitive_found': sensitive_found,
            'has_geo_label': has_geo_label,
            'unlabeled_count': len(unlabeled),
            'level': level,
        },
        'geo_sensitive_terms': sensitive_terms[:10],
        'unlabeled_scope_issues': unlabeled[:5],
        'suggestions': suggestions,
    }


def _generate_suggestions(found: List[str], has_label: bool,
                           unlabeled: List[Dict], level: str) -> List[str]:
    suggestions = []

    level_labels = {
        'none': '해당 없음', 'labeled': '적절',
        'partial': '부분적', 'unlabeled': '라벨 누락',
    }
    suggestions.append(
        f'지역 범위 표시: {level_labels.get(level, level)}.'
    )

    if not found:
        suggestions.append('지역 의존 정보가 감지되지 않았습니다.')
        return suggestions

    if not has_label:
        labels = {c: _GEO_SENSITIVE_CATEGORIES[c]['label'] for c in _GEO_SENSITIVE_CATEGORIES}
        found_labels = ', '.join(labels.get(f, f) for f in found[:3])
        suggestions.append(
            f'{found_labels} 정보가 있으나 국가/지역 라벨이 없습니다. '
            f'"(한국 기준)", "(US only)" 등을 추가하세요.'
        )

    for u in unlabeled[:2]:
        suggestions.append(
            f'{u["label"]} 항목에 적용 국가/지역을 명시하세요.'
        )

    return suggestions
