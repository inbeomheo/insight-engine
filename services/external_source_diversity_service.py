"""
External Source Diversity Auditor 서비스

콘텐츠에서 인용된 외부 소스(URL, 도메인)의 다양성을 평가합니다.
단일 소스 의존 위험을 감지하고 소스 다각화를 권장합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from collections import Counter
from typing import List, Dict
from urllib.parse import urlparse


# URL 추출 패턴
_URL_RE = re.compile(
    r'https?://[^\s)<>\]"\']+',
    re.IGNORECASE
)

# 마크다운 링크: [text](url)
_MD_LINK_RE = re.compile(r'\[([^\]]+)\]\((https?://[^)]+)\)')

# 인용 표현 패턴 (한국어)
_CITATION_PATTERNS_KO = [
    re.compile(r'(?:에\s*따르면|에\s*의하면)'),
    re.compile(r'(?:보고서|연구|조사|논문|발표)(?:에서|에\s*따르면)'),
    re.compile(r'(?:출처|참고|참조)\s*[:：]'),
]

# 인용 표현 패턴 (영어)
_CITATION_PATTERNS_EN = [
    re.compile(r'\baccording\s+to\b', re.IGNORECASE),
    re.compile(r'\b(?:study|research|report|survey)\s+(?:by|from|shows)\b', re.IGNORECASE),
    re.compile(r'\bsource:\s', re.IGNORECASE),
]

# 제외할 도메인 (자기 참조, CDN 등)
_EXCLUDE_DOMAINS = {
    'localhost', '127.0.0.1', 'example.com', 'example.org',
    'cdn.jsdelivr.net', 'unpkg.com', 'cdnjs.cloudflare.com',
    'fonts.googleapis.com', 'fonts.gstatic.com',
}


def _extract_domain(url: str) -> str:
    """URL에서 도메인을 추출합니다."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # www. 제거
        if domain.startswith('www.'):
            domain = domain[4:]
        # 포트 제거
        if ':' in domain:
            domain = domain.split(':')[0]
        return domain
    except Exception:
        return ''


def audit_external_source_diversity(content: str) -> dict:
    """외부 소스의 다양성을 평가합니다.

    Args:
        content: 분석할 콘텐츠

    Returns:
        sources, domain_distribution, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'sources': [],
            'domain_distribution': [],
            'summary': {'total_sources': 0, 'unique_domains': 0,
                        'diversity_score': 0.0, 'citation_count': 0},
            'score': 50.0,
            'suggestions': ['콘텐츠가 비어 있습니다.'],
        }

    # URL 추출
    urls = set()
    for match in _URL_RE.finditer(content):
        urls.add(match.group(0).rstrip('.,;:'))
    for match in _MD_LINK_RE.finditer(content):
        urls.add(match.group(2).rstrip('.,;:'))

    # 도메인 추출 및 필터링
    sources = []
    domain_counter = Counter()
    for url in urls:
        domain = _extract_domain(url)
        if not domain or domain in _EXCLUDE_DOMAINS:
            continue
        sources.append({'url': url, 'domain': domain})
        domain_counter[domain] += 1

    # 인용 표현 카운트
    citation_count = 0
    for pattern in _CITATION_PATTERNS_KO + _CITATION_PATTERNS_EN:
        citation_count += len(pattern.findall(content))

    if not sources:
        score = 50.0 if citation_count == 0 else 60.0
        suggestions = ['외부 링크가 없습니다. 신뢰할 수 있는 출처를 인용하면 E-E-A-T 점수가 향상됩니다.']
        return {
            'sources': [],
            'domain_distribution': [],
            'summary': {'total_sources': 0, 'unique_domains': 0,
                        'diversity_score': 0.0, 'citation_count': citation_count},
            'score': score,
            'suggestions': suggestions,
        }

    unique_domains = len(domain_counter)
    total_sources = len(sources)

    # 다양성 점수: 고유 도메인 / 전체 소스
    diversity_ratio = unique_domains / total_sources if total_sources > 0 else 0.0

    # 도메인 분포
    domain_distribution = [
        {'domain': domain, 'count': count,
         'percentage': round(count / total_sources * 100, 1)}
        for domain, count in domain_counter.most_common()
    ]

    # 점수 계산
    # 기본: 다양성 비율 × 70 + 소스 수 보너스(최대 30)
    source_bonus = min(30.0, unique_domains * 10.0)
    score = round(min(100.0, diversity_ratio * 70.0 + source_bonus), 1)

    # 단일 도메인 과의존 페널티
    if domain_distribution and domain_distribution[0]['percentage'] > 60:
        score = round(max(0.0, score - 20.0), 1)

    suggestions = _generate_suggestions(
        unique_domains, total_sources, domain_distribution, citation_count
    )

    return {
        'sources': sources,
        'domain_distribution': domain_distribution,
        'summary': {
            'total_sources': total_sources,
            'unique_domains': unique_domains,
            'diversity_score': round(diversity_ratio * 100, 1),
            'citation_count': citation_count,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _generate_suggestions(
    unique: int, total: int, dist: List[Dict], citations: int
) -> List[str]:
    suggestions = []

    if unique == 1:
        suggestions.append(f'단일 도메인({dist[0]["domain"]})만 인용 중입니다. 다양한 출처를 추가하세요.')
    elif unique < 3:
        suggestions.append(f'고유 도메인 {unique}개로 다양성이 부족합니다. 3개 이상의 출처를 권장합니다.')
    else:
        suggestions.append(f'고유 도메인 {unique}개로 소스 다양성이 양호합니다.')

    if dist and dist[0]['percentage'] > 60:
        suggestions.append(
            f'{dist[0]["domain"]}이 {dist[0]["percentage"]}%를 차지합니다. '
            f'단일 소스 의존도를 낮추세요.'
        )

    if citations == 0 and total > 0:
        suggestions.append('인용 표현(~에 따르면, according to 등)이 없습니다. 출처 귀속을 명시하세요.')

    return suggestions
