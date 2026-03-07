"""
콘텐츠 신선도 모니터링 서비스

발행된 콘텐츠의 정보 노후화를 감지하고 리프레시를 제안합니다.
날짜 참조, 시간 경과, 통계/수치, 기술 용어 등을 분석합니다.
"""
import re
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# 시간 기반 표현 패턴
_YEAR_PATTERN = re.compile(r'20[12]\d년?')
_DATE_PATTERNS = [
    re.compile(r'20[12]\d[-./]\d{1,2}[-./]\d{1,2}'),  # 2024-01-15
    re.compile(r'20[12]\d년\s*\d{1,2}월'),  # 2024년 3월
    re.compile(r'올해|금년|작년|지난해|최근'),
    re.compile(r'현재|지금|요즘'),
]

# 통계/수치 패턴 (노후화 가능성)
_STAT_PATTERNS = [
    re.compile(r'\d+[%％]'),
    re.compile(r'\d+만\s*(명|원|건|개)'),
    re.compile(r'\d+억'),
    re.compile(r'시장\s*규모'),
    re.compile(r'점유율'),
    re.compile(r'성장률'),
]

# 빠르게 변하는 기술 키워드
_VOLATILE_TECH = [
    'GPT', 'ChatGPT', 'Claude', 'Gemini', 'LLM',
    'API', '버전', 'version', r'v\d+',
    '프레임워크', 'React', 'Next.js', 'Vue',
    '알고리즘', '업데이트', '패치',
]


def check_freshness(content: str, published_date: str) -> dict:
    """콘텐츠의 신선도를 평가합니다.

    Args:
        content: 평가할 콘텐츠 텍스트
        published_date: 발행일 (ISO 8601 형식, 예: "2025-06-15")

    Returns:
        {
            "freshness_score": int (0~100, 높을수록 신선),
            "status": "fresh" | "aging" | "stale",
            "days_since_published": int,
            "risk_factors": list[dict],
            "refresh_suggestions": list[str],
        }
    """
    if not content or not content.strip():
        return {
            'freshness_score': 0,
            'status': 'stale',
            'days_since_published': 0,
            'risk_factors': [],
            'refresh_suggestions': ['콘텐츠가 비어 있습니다.'],
        }

    # 발행일 파싱
    try:
        pub_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
        if pub_date.tzinfo is None:
            pub_date = pub_date.replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        pub_date = datetime.now(timezone.utc)

    now = datetime.now(timezone.utc)
    days_elapsed = max(0, (now - pub_date).days)

    # 위험 요소 수집
    risk_factors = []

    # 1) 시간 경과 기반 감점
    time_score = _score_time_decay(days_elapsed)
    if days_elapsed > 180:
        risk_factors.append({
            'type': 'time_decay',
            'severity': 'high' if days_elapsed > 365 else 'medium',
            'detail': f'발행 후 {days_elapsed}일 경과',
        })

    # 2) 날짜 참조 감지
    date_refs = _find_date_references(content)
    date_score = 100
    for ref in date_refs:
        risk_factors.append({
            'type': 'outdated_date_reference',
            'severity': ref['severity'],
            'detail': ref['detail'],
        })
        if ref['severity'] == 'high':
            date_score -= 30
        elif ref['severity'] == 'medium':
            date_score -= 15
    date_score = max(0, date_score)

    # 3) 통계/수치 노후화 위험
    stat_refs = _find_stat_references(content)
    stat_score = 100
    if stat_refs and days_elapsed > 90:
        for ref in stat_refs:
            risk_factors.append({
                'type': 'outdated_statistics',
                'severity': 'medium' if days_elapsed < 365 else 'high',
                'detail': ref,
            })
            stat_score -= 10
    stat_score = max(0, stat_score)

    # 4) 기술 용어 변동성
    tech_score = 100
    tech_refs = _find_volatile_tech(content)
    if tech_refs and days_elapsed > 60:
        for ref in tech_refs:
            risk_factors.append({
                'type': 'volatile_technology',
                'severity': 'medium',
                'detail': f'빠르게 변하는 기술 언급: {ref}',
            })
            tech_score -= 8
    tech_score = max(0, tech_score)

    # 종합 점수
    freshness_score = round(
        time_score * 0.40
        + date_score * 0.25
        + stat_score * 0.20
        + tech_score * 0.15
    )
    freshness_score = max(0, min(100, freshness_score))

    # 상태 판정
    if freshness_score >= 70:
        status = 'fresh'
    elif freshness_score >= 40:
        status = 'aging'
    else:
        status = 'stale'

    # 리프레시 제안
    refresh_suggestions = _generate_refresh_suggestions(
        risk_factors, days_elapsed, status
    )

    return {
        'freshness_score': freshness_score,
        'status': status,
        'days_since_published': days_elapsed,
        'risk_factors': risk_factors,
        'refresh_suggestions': refresh_suggestions,
    }


def _score_time_decay(days: int) -> int:
    """시간 경과에 따른 감쇠 점수."""
    if days <= 30:
        return 100
    elif days <= 90:
        return 85
    elif days <= 180:
        return 70
    elif days <= 365:
        return 50
    elif days <= 730:
        return 30
    else:
        return 15


def _find_date_references(content: str) -> list:
    """콘텐츠 내 날짜 참조를 감지합니다."""
    refs = []
    current_year = datetime.now().year

    # 연도 참조
    years_found = _YEAR_PATTERN.findall(content)
    for year_str in years_found:
        year_num = int(re.search(r'\d{4}', year_str).group())
        age = current_year - year_num
        if age >= 2:
            refs.append({
                'severity': 'high' if age >= 3 else 'medium',
                'detail': f'{year_str} 참조 발견 ({age}년 전 정보)',
            })

    # 상대적 시간 표현
    for pat in _DATE_PATTERNS[2:]:  # '올해', '최근' 등
        matches = pat.findall(content)
        if matches:
            refs.append({
                'severity': 'low',
                'detail': f'상대적 시간 표현 "{matches[0]}" — 발행일 기준 해석 필요',
            })
            break  # 하나만

    return refs


def _find_stat_references(content: str) -> list:
    """통계/수치 참조를 감지합니다."""
    refs = []
    for pat in _STAT_PATTERNS:
        matches = pat.findall(content)
        for m in matches[:3]:  # 최대 3개
            refs.append(f'통계 수치 "{m}" — 최신 데이터 확인 필요')
    return refs


def _find_volatile_tech(content: str) -> list:
    """빠르게 변하는 기술 키워드를 감지합니다."""
    found = []
    for keyword in _VOLATILE_TECH:
        if re.search(keyword, content, re.IGNORECASE):
            found.append(keyword)
    return found[:5]  # 최대 5개


def _generate_refresh_suggestions(
    risk_factors: list, days_elapsed: int, status: str
) -> list:
    suggestions = []

    if status == 'fresh':
        suggestions.append('콘텐츠가 아직 신선합니다. 현재 상태로 충분합니다.')
        return suggestions

    # 시간 경과
    if days_elapsed > 365:
        suggestions.append('발행 후 1년 이상 경과했습니다. 전체 리프레시를 권장합니다.')
    elif days_elapsed > 180:
        suggestions.append('6개월 이상 경과했습니다. 핵심 정보의 최신성을 확인하세요.')

    # 위험 유형별 제안
    risk_types = {rf['type'] for rf in risk_factors}

    if 'outdated_date_reference' in risk_types:
        suggestions.append('오래된 연도 참조를 최신 날짜로 업데이트하세요.')

    if 'outdated_statistics' in risk_types:
        suggestions.append('통계 수치를 최신 데이터로 갱신하세요.')

    if 'volatile_technology' in risk_types:
        suggestions.append('언급된 기술의 최신 버전/변경사항을 반영하세요.')

    if not suggestions:
        suggestions.append('콘텐츠를 검토하여 최신 정보로 업데이트하세요.')

    return suggestions
