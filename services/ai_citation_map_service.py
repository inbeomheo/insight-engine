"""AI 인용 소스 맵 서비스

AI 응답 텍스트에서 인용된 도메인, URL, 인용 유형을 분석하여
인용 소스 맵을 생성합니다.
"""
import re
from dataclasses import dataclass, field
from collections import Counter
from urllib.parse import urlparse


@dataclass
class CitationEntry:
    """개별 인용 항목"""
    domain: str                      # 인용 도메인 (예: "wikipedia.org")
    url: str | None                  # 전체 URL (감지된 경우)
    citation_type: str               # "direct" | "indirect" | "paraphrase"
    context: str                     # 인용 주변 문맥
    frequency: int                   # 해당 도메인의 등장 횟수


@dataclass
class CitationMap:
    """인용 소스 맵 종합 보고서"""
    total_citations: int              # 총 인용 수
    by_domain: dict[str, int]         # {도메인: 횟수}
    by_type: dict[str, int]           # {인용유형: 횟수}
    entries: list[CitationEntry] = field(default_factory=list)  # 개별 항목
    top_domains: list[str] = field(default_factory=list)        # 상위 도메인


# URL 패턴 (http/https 프로토콜 포함)
_URL_PATTERN = re.compile(
    r'https?://[^\s<>\"\'\)\],;]+',
    re.IGNORECASE,
)

# 직접 인용 패턴: "인용문" 또는 「인용문」 또는 '인용문'
_DIRECT_QUOTE_PATTERN = re.compile(
    r'["\u201C\u300C\u2018]([^"\u201D\u300D\u2019]{5,})["\u201D\u300D\u2019]'
)

# 간접 인용 지시어 (한국어 + 영어)
_INDIRECT_MARKERS = re.compile(
    r'(?i)(?:according\s+to|에\s*따르면|에\s*의하면|발표한|보도한|주장한|'
    r'연구에서|보고서에\s*따르면|said|stated|reported|claimed|suggests?\s+that)',
)

# 패러프레이즈 지시어
_PARAPHRASE_MARKERS = re.compile(
    r'(?i)(?:based\s+on|참고로|참조|인용|출처|source|reference|cited|'
    r'기반으로|근거로|바탕으로)',
)

# 도메인 언급 패턴 (www. 포함 또는 알려진 TLD)
# \b 대신 (?=[^a-zA-Z0-9.-]|$) 사용: 한국어 등 유니코드 뒤에서도 매칭
_DOMAIN_PATTERN = re.compile(
    r'(?:www\.)?([a-zA-Z0-9][-a-zA-Z0-9]*\.(?:com|org|net|io|gov|edu|co\.kr|kr|jp|ai|dev))(?=[^a-zA-Z0-9.-]|$)',
    re.IGNORECASE,
)


def _extract_domain(url: str) -> str:
    """URL에서 도메인을 추출한다.

    Args:
        url: 전체 URL 문자열

    Returns:
        도메인 문자열 (예: "example.com")
    """
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ''
        # www. 접두사 제거
        if host.startswith('www.'):
            host = host[4:]
        return host.lower()
    except Exception:
        return ''


def _get_context(text: str, start: int, end: int, window: int = 80) -> str:
    """매칭 위치 주변의 문맥을 추출한다.

    Args:
        text: 원본 텍스트
        start: 매칭 시작 인덱스
        end: 매칭 끝 인덱스
        window: 전후로 가져올 문자 수

    Returns:
        잘라낸 문맥 문자열
    """
    ctx_start = max(0, start - window)
    ctx_end = min(len(text), end + window)
    return text[ctx_start:ctx_end].strip()


def _classify_citation_type(context: str) -> str:
    """문맥에서 인용 유형을 분류한다.

    Args:
        context: 인용 주변 문맥

    Returns:
        "direct" | "indirect" | "paraphrase"
    """
    # 직접 인용 (따옴표 안에 있는지 확인)
    if _DIRECT_QUOTE_PATTERN.search(context):
        return 'direct'

    # 간접 인용 (~에 따르면, according to 등)
    if _INDIRECT_MARKERS.search(context):
        return 'indirect'

    # 패러프레이즈 (출처, 참고 등)
    if _PARAPHRASE_MARKERS.search(context):
        return 'paraphrase'

    # 기본값: 간접 인용
    return 'indirect'


def _extract_citations_from_text(text: str) -> list[dict]:
    """단일 텍스트에서 인용 정보를 추출한다.

    URL 기반 인용과 도메인 기반 인용을 모두 감지한다.

    Args:
        text: AI 응답 텍스트

    Returns:
        [{'domain': ..., 'url': ..., 'type': ..., 'context': ...}, ...]
    """
    citations = []
    seen_urls = set()

    # 1단계: URL에서 인용 추출
    for match in _URL_PATTERN.finditer(text):
        url = match.group(0).rstrip('.')  # 문장 끝 마침표 제거
        if url in seen_urls:
            continue
        seen_urls.add(url)

        domain = _extract_domain(url)
        if not domain:
            continue

        context = _get_context(text, match.start(), match.end())
        ctype = _classify_citation_type(context)

        citations.append({
            'domain': domain,
            'url': url,
            'type': ctype,
            'context': context,
        })

    # 2단계: URL 없이 도메인만 언급된 경우
    for match in _DOMAIN_PATTERN.finditer(text):
        domain = match.group(1).lower()

        # 이미 URL로 감지된 도메인은 건너뜀
        if any(c['domain'] == domain for c in citations):
            continue

        context = _get_context(text, match.start(), match.end())
        ctype = _classify_citation_type(context)

        citations.append({
            'domain': domain,
            'url': None,
            'type': ctype,
            'context': context,
        })

    return citations


def map_citations(
    ai_responses: list[str],
    top_n: int = 10,
) -> CitationMap:
    """AI 응답들에서 인용 도메인/URL/유형을 분석한다.

    Args:
        ai_responses: AI 응답 텍스트 리스트
        top_n: 상위 도메인 수 (기본 10)

    Returns:
        CitationMap 데이터클래스

    Raises:
        ValueError: ai_responses가 None인 경우
    """
    if ai_responses is None:
        raise ValueError("ai_responses는 None일 수 없습니다")

    all_raw: list[dict] = []
    for response in ai_responses:
        if not response or not response.strip():
            continue
        raw_citations = _extract_citations_from_text(response)
        all_raw.extend(raw_citations)

    # 도메인별 집계
    domain_counter: Counter[str] = Counter()
    type_counter: Counter[str] = Counter()

    for c in all_raw:
        domain_counter[c['domain']] += 1
        type_counter[c['type']] += 1

    # CitationEntry 목록 생성 (도메인별 대표 항목)
    entries: list[CitationEntry] = []
    seen_domains: set[str] = set()

    for c in all_raw:
        domain = c['domain']
        if domain in seen_domains:
            continue
        seen_domains.add(domain)

        entries.append(CitationEntry(
            domain=domain,
            url=c['url'],
            citation_type=c['type'],
            context=c['context'],
            frequency=domain_counter[domain],
        ))

    # 빈도 내림차순 정렬
    entries.sort(key=lambda e: e.frequency, reverse=True)

    # 상위 도메인
    top_domains = [d for d, _ in domain_counter.most_common(top_n)]

    return CitationMap(
        total_citations=len(all_raw),
        by_domain=dict(domain_counter),
        by_type=dict(type_counter),
        entries=entries,
        top_domains=top_domains,
    )


def get_citation_summary(citation_map: CitationMap) -> dict:
    """인용 맵의 요약 통계를 반환한다.

    Args:
        citation_map: map_citations()의 반환값

    Returns:
        {'total': int, 'unique_domains': int, 'primary_type': str, 'top_domain': str}
    """
    primary_type = ''
    if citation_map.by_type:
        primary_type = max(citation_map.by_type, key=citation_map.by_type.get)

    top_domain = citation_map.top_domains[0] if citation_map.top_domains else ''

    return {
        'total': citation_map.total_citations,
        'unique_domains': len(citation_map.by_domain),
        'primary_type': primary_type,
        'top_domain': top_domain,
    }
