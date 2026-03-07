"""
Primary Source Preference Checker 서비스

인용 근거가 공식문서/원문/논문(1차 출처)보다
2차 요약 글에 치우쳤는지 분석합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict

# URL 추출
_URL_RE = re.compile(r'https?://[^\s\)\]>\"\']+', re.IGNORECASE)

# 1차 출처 도메인 패턴 (공식/학술/정부)
_PRIMARY_DOMAINS = [
    # 학술
    re.compile(r'(?:arxiv\.org|scholar\.google|doi\.org|pubmed|ncbi\.nlm|ieee\.org|acm\.org|springer\.com|nature\.com|science\.org)', re.IGNORECASE),
    # 공식 문서
    re.compile(r'(?:docs\.|documentation\.|developer\.|developers\.|api\.|official)', re.IGNORECASE),
    re.compile(r'(?:github\.com/.+/(?:docs|wiki|README)|readthedocs\.io)', re.IGNORECASE),
    # 정부/기관
    re.compile(r'(?:\.gov|\.go\.kr|\.ac\.kr|\.edu|\.org)', re.IGNORECASE),
    # RFC/표준
    re.compile(r'(?:rfc-editor\.org|w3\.org|ietf\.org|iso\.org)', re.IGNORECASE),
]

# 2차 출처 도메인 패턴 (블로그/뉴스/포럼)
_SECONDARY_DOMAINS = [
    re.compile(r'(?:medium\.com|blog\.|tistory\.com|velog\.io|brunch\.co\.kr|naver\.com/blog|wordpress\.com)', re.IGNORECASE),
    re.compile(r'(?:stackoverflow\.com|reddit\.com|quora\.com|forum)', re.IGNORECASE),
    re.compile(r'(?:youtube\.com|youtu\.be)', re.IGNORECASE),
    re.compile(r'(?:techcrunch|theverge|wired|zdnet|cnet|mashable|engadget)', re.IGNORECASE),
]

# 인용 패턴 (텍스트 내 출처 언급)
_CITATION_PATTERNS = [
    re.compile(r'(?:에\s*따르면|에\s*의하면|보고서에|연구에|논문에)', re.IGNORECASE),
    re.compile(r'(?:공식\s*(?:문서|사이트|홈페이지|발표))', re.IGNORECASE),
    re.compile(r'\b(?:according\s+to|cited\s+(?:in|from)|source:|reference:)\b', re.IGNORECASE),
    re.compile(r'\b(?:official\s+(?:docs?|documentation|site|announcement))\b', re.IGNORECASE),
]

# 학술 인용 패턴
_ACADEMIC_PATTERNS = [
    re.compile(r'\(\d{4}\)'),  # (2024)
    re.compile(r'(?:et\s+al\.)', re.IGNORECASE),
    re.compile(r'(?:Vol\.\s*\d|pp\.\s*\d)', re.IGNORECASE),
]


def _classify_url(url: str) -> str:
    """URL을 1차/2차/불분명으로 분류합니다."""
    for pat in _PRIMARY_DOMAINS:
        if pat.search(url):
            return 'primary'
    for pat in _SECONDARY_DOMAINS:
        if pat.search(url):
            return 'secondary'
    return 'unknown'


def check_primary_source_preference(content: str) -> dict:
    """인용 출처의 1차/2차 비율을 분석합니다.

    Returns:
        score, summary, suggestions, source_tiers를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'score': 100.0,
            'summary': {
                'total_urls': 0,
                'primary_count': 0,
                'secondary_count': 0,
                'unknown_count': 0,
                'primary_ratio': 0.0,
                'citation_mentions': 0,
                'academic_citations': 0,
                'level': 'none',
            },
            'source_tiers': [],
            'suggestions': [],
        }

    # URL 추출 및 분류
    urls = _URL_RE.findall(content)
    source_tiers = []
    primary_count = 0
    secondary_count = 0
    unknown_count = 0

    seen = set()
    for url in urls:
        # 중복 제거 (쿼리 파라미터 무시)
        base = url.split('?')[0].rstrip('/')
        if base in seen:
            continue
        seen.add(base)

        tier = _classify_url(url)
        source_tiers.append({'url': url[:80], 'tier': tier})

        if tier == 'primary':
            primary_count += 1
        elif tier == 'secondary':
            secondary_count += 1
        else:
            unknown_count += 1

    total_urls = primary_count + secondary_count + unknown_count

    # 텍스트 인용 패턴
    citation_mentions = sum(
        len(pat.findall(content)) for pat in _CITATION_PATTERNS
    )

    # 학술 인용 패턴
    academic_citations = sum(
        len(pat.findall(content)) for pat in _ACADEMIC_PATTERNS
    )

    # 1차 출처 비율
    classified = primary_count + secondary_count
    primary_ratio = round(
        primary_count / max(classified, 1) * 100, 1
    )

    # 레벨 판정
    if total_urls == 0 and citation_mentions == 0:
        level = 'none'
    elif primary_ratio >= 60:
        level = 'excellent'
    elif primary_ratio >= 40:
        level = 'good'
    elif primary_ratio >= 20:
        level = 'fair'
    else:
        level = 'poor'

    # 학술 인용 보정
    if academic_citations >= 3 and level == 'fair':
        level = 'good'

    # 점수 계산
    if level == 'none':
        # 출처 없음 — 인용이 필요한 콘텐츠인지 판단 불가
        word_count = len(content.split())
        score = 80.0 if word_count < 200 else 50.0
    elif level == 'excellent':
        score = 100.0
    elif level == 'good':
        score = 80.0
    elif level == 'fair':
        score = 60.0
    else:
        score = 35.0

    # 인용 문구 보너스
    if citation_mentions >= 3 and score < 100:
        score = min(100.0, score + 10.0)

    score = round(max(0.0, min(100.0, score)), 1)

    suggestions = _generate_suggestions(
        total_urls, primary_count, secondary_count,
        primary_ratio, citation_mentions, academic_citations, level
    )

    return {
        'score': score,
        'summary': {
            'total_urls': total_urls,
            'primary_count': primary_count,
            'secondary_count': secondary_count,
            'unknown_count': unknown_count,
            'primary_ratio': primary_ratio,
            'citation_mentions': citation_mentions,
            'academic_citations': academic_citations,
            'level': level,
        },
        'source_tiers': source_tiers[:20],
        'suggestions': suggestions,
    }


def _generate_suggestions(total: int, primary: int, secondary: int,
                           ratio: float, citations: int,
                           academic: int, level: str) -> List[str]:
    suggestions = []

    level_labels = {
        'excellent': '우수', 'good': '양호',
        'fair': '보통', 'poor': '미흡', 'none': '출처 없음',
    }

    suggestions.append(
        f'출처 품질: {level_labels.get(level, level)}. '
        f'1차 출처 {primary}개, 2차 출처 {secondary}개 '
        f'(1차 비율 {ratio}%).'
    )

    if level == 'none' and total == 0:
        suggestions.append(
            '출처 URL이 없습니다. 주장의 근거를 1차 출처로 뒷받침하세요.'
        )

    if level in ('poor', 'fair'):
        suggestions.append(
            '2차 출처(블로그/뉴스) 비중이 높습니다. '
            '공식 문서, 논문, 정부 사이트 등 1차 출처를 추가하세요.'
        )

    if secondary > 3 and primary == 0:
        suggestions.append(
            '모든 출처가 2차 자료입니다. '
            '최소 1개 이상의 공식/학술 출처를 포함하세요.'
        )

    return suggestions
