"""
High-Stakes Advice Risk Detector 서비스

의료/금융/법률/안전 조언에서 면책문구, 공식출처,
전문가 검토 부재를 탐지합니다 (YMYL 콘텐츠 안전성 점검).
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)

# YMYL 도메인별 키워드
_YMYL_DOMAINS = {
    'medical': [
        re.compile(r'(?:의료|진단|처방|약물|투약|복용|부작용|증상|질환|질병|치료|수술)', re.IGNORECASE),
        re.compile(r'(?:건강|영양제|보충제|식이요법|다이어트|체중\s*감량)', re.IGNORECASE),
        re.compile(r'\b(?:medical|diagnosis|prescription|medication|dosage|symptom|treatment|surgery)\b', re.IGNORECASE),
        re.compile(r'\b(?:health|supplement|diet|weight\s*loss|side\s*effect)\b', re.IGNORECASE),
    ],
    'financial': [
        re.compile(r'(?:투자|주식|펀드|채권|부동산\s*투자|수익률|배당|대출|금리)', re.IGNORECASE),
        re.compile(r'(?:세금|절세|연말정산|보험\s*(?:가입|청구)|연금|퇴직금)', re.IGNORECASE),
        re.compile(r'\b(?:invest|stock|fund|bond|mortgage|loan|interest\s*rate|dividend)\b', re.IGNORECASE),
        re.compile(r'\b(?:tax|insurance|pension|retirement|financial\s*advice)\b', re.IGNORECASE),
    ],
    'legal': [
        re.compile(r'(?:법률|법적|소송|계약|합의|판결|변호사|법원|형사|민사)', re.IGNORECASE),
        re.compile(r'(?:저작권|특허|상표|개인정보|GDPR|약관|면책)', re.IGNORECASE),
        re.compile(r'\b(?:legal|lawsuit|contract|court|attorney|lawyer|litigation)\b', re.IGNORECASE),
        re.compile(r'\b(?:copyright|patent|trademark|privacy|GDPR|terms\s+of\s+service)\b', re.IGNORECASE),
    ],
    'safety': [
        re.compile(r'(?:안전|위험|사고|응급|구조|화재|전기\s*(?:작업|공사))', re.IGNORECASE),
        re.compile(r'(?:독성|유해\s*물질|방사선|감전|추락|폭발)', re.IGNORECASE),
        re.compile(r'\b(?:safety|danger|emergency|hazard|toxic|electrical|fire)\b', re.IGNORECASE),
    ],
}

# 면책문구 패턴
_DISCLAIMER_PATTERNS = [
    re.compile(r'(?:본\s*(?:글|콘텐츠|정보).*?(?:참고|참조)\s*(?:용|목적|자료))', re.IGNORECASE),
    re.compile(r'(?:전문가.*?(?:상담|자문|조언).*?(?:받으|구하|권장))', re.IGNORECASE),
    re.compile(r'(?:(?:의사|변호사|전문가|회계사).*?(?:상담|상의|확인))', re.IGNORECASE),
    re.compile(r'(?:(?:책임|보장).*?(?:지지\s*않|없|드리지))', re.IGNORECASE),
    re.compile(r'(?:개인\s*(?:상황|사정).*?(?:다를|다릅니다|상이))', re.IGNORECASE),
    re.compile(r'\b(?:disclaimer|not\s+(?:medical|legal|financial)\s+advice)\b', re.IGNORECASE),
    re.compile(r'\b(?:consult\s+(?:a|your)\s+(?:doctor|lawyer|advisor|professional))\b', re.IGNORECASE),
    re.compile(r'\b(?:for\s+(?:informational|educational)\s+purposes?\s+only)\b', re.IGNORECASE),
]

# 전문가/권위 신호
_AUTHORITY_PATTERNS = [
    re.compile(r'(?:(?:의사|변호사|세무사|약사|전문가|교수|박사).*?(?:감수|검토|확인|작성))', re.IGNORECASE),
    re.compile(r'(?:(?:감수|검토|자문)\s*:\s*.+)', re.IGNORECASE),
    re.compile(r'\b(?:reviewed\s+by|verified\s+by|written\s+by\s+(?:Dr|MD|JD|CPA))\b', re.IGNORECASE),
    re.compile(r'\b(?:peer[- ]reviewed|evidence[- ]based|clinically\s+(?:tested|proven))\b', re.IGNORECASE),
]


def _detect_ymyl_domains(content: str) -> List[Tuple[str, int]]:
    """YMYL 도메인 감지 및 매칭 수를 반환합니다."""
    results = []
    for domain, patterns in _YMYL_DOMAINS.items():
        count = sum(len(p.findall(content)) for p in patterns)
        if count >= 2:  # 최소 2건 이상 매칭
            results.append((domain, count))
    return sorted(results, key=lambda x: x[1], reverse=True)


def _find_matches(content: str, patterns: list) -> List[str]:
    """매칭된 텍스트를 반환합니다."""
    matches = []
    seen = set()
    for pat in patterns:
        for m in pat.finditer(content):
            text = m.group().strip()
            if text.lower() not in seen:
                seen.add(text.lower())
                matches.append(text)
    return matches


_EMPTY_RESULT = {
    'score': 100.0,
    'summary': {
        'is_ymyl': False, 'ymyl_domains': [],
        'has_disclaimer': False, 'has_authority': False, 'risk_level': 'none',
    },
    'risk_spans': [],
    'missing_safety_signals': [],
    'suggestions': [],
}

_DOMAIN_LABELS = {
    'medical': '의료/건강',
    'financial': '금융/투자',
    'legal': '법률',
    'safety': '안전',
}


def _assess_risk(is_ymyl: bool, has_disclaimer: bool, has_authority: bool,
                 ymyl_domains: list) -> tuple:
    """위험 수준, 누락 항목, 점수를 판정합니다.

    Returns:
        (risk_level, missing, score)
    """
    if not is_ymyl:
        return 'none', [], 100.0

    missing = []
    if not has_disclaimer:
        missing.append('면책문구(disclaimer) 누락')
    if not has_authority:
        missing.append('전문가 검토/감수 표시 누락')

    if not has_disclaimer and not has_authority:
        risk_level = 'high'
    elif not has_disclaimer or not has_authority:
        risk_level = 'medium'
    else:
        risk_level = 'low'

    score = 30.0 + (sum([has_disclaimer, has_authority]) * 30.0)
    if len(ymyl_domains) >= 2 and risk_level != 'low':
        score -= 10.0

    return risk_level, missing, round(max(0.0, min(100.0, score)), 1)


def detect_high_stakes_advice_risk(content: str) -> dict:
    """고위험 조언 콘텐츠의 안전성을 점검합니다.

    Returns:
        score, summary, suggestions, risk_spans, missing_safety_signals를 포함하는 dict
    """
    try:
        if not content or not content.strip():
            return dict(_EMPTY_RESULT)

        ymyl_domains = _detect_ymyl_domains(content)
        is_ymyl = len(ymyl_domains) > 0
        has_disclaimer = len(_find_matches(content, _DISCLAIMER_PATTERNS)) > 0
        has_authority = len(_find_matches(content, _AUTHORITY_PATTERNS)) > 0
        risk_level, missing, score = _assess_risk(is_ymyl, has_disclaimer, has_authority, ymyl_domains)

        return {
            'score': score,
            'summary': {
                'is_ymyl': is_ymyl,
                'ymyl_domains': [
                    {'domain': d, 'label': _DOMAIN_LABELS.get(d, d), 'count': c}
                    for d, c in ymyl_domains
                ],
                'has_disclaimer': has_disclaimer,
                'has_authority': has_authority,
                'risk_level': risk_level,
            },
            'risk_spans': [{'domain': d, 'count': c} for d, c in ymyl_domains[:5]],
            'missing_safety_signals': missing,
            'suggestions': _generate_suggestions(
                is_ymyl, ymyl_domains, has_disclaimer, has_authority,
                risk_level, missing, _DOMAIN_LABELS
            ),
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}



def _generate_suggestions(is_ymyl: bool, domains: list,
                           has_disclaimer: bool, has_authority: bool,
                           risk_level: str, missing: List[str],
                           labels: dict) -> List[str]:
    suggestions = []

    if not is_ymyl:
        suggestions.append('YMYL(Your Money or Your Life) 콘텐츠가 아닌 것으로 판단됩니다.')
        return suggestions

    domain_names = ', '.join(labels.get(d, d) for d, _ in domains[:3])
    risk_labels = {'high': '높음', 'medium': '보통', 'low': '낮음'}

    suggestions.append(
        f'YMYL 도메인 감지: {domain_names}. '
        f'위험 수준: {risk_labels.get(risk_level, risk_level)}.'
    )

    for m in missing:
        suggestions.append(f'⚠ {m}')

    if not has_disclaimer:
        suggestions.append(
            '"본 글은 참고용이며, 전문가 상담을 권장합니다" 등의 '
            '면책문구를 추가하세요.'
        )

    if not has_authority:
        suggestions.append(
            '전문가 감수/검토 표시(예: "감수: 홍길동 의사")를 추가하세요.'
        )

    if has_disclaimer and has_authority:
        suggestions.append('면책문구와 전문가 검토 표시가 모두 포함되어 있습니다.')

    return suggestions
