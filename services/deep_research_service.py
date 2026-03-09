"""
멀티소스 리서치 서비스

여러 소스(학술, 뉴스, 소셜, 특허, 블로그)에서 쿼리 기반으로
시뮬레이션된 리서치 보고서를 생성합니다.
외부 API 호출 없이 규칙 기반으로 동작합니다.
"""
import hashlib
import re
from dataclasses import dataclass, field
from typing import List, Optional


# 지원 소스 목록
AVAILABLE_SOURCES = ["academic", "news", "social", "patent", "blog"]

# 소스별 기본 관련도 가중치
_SOURCE_WEIGHTS = {
    "academic": 0.95,
    "patent": 0.90,
    "news": 0.80,
    "blog": 0.70,
    "social": 0.60,
}

# 소스별 시뮬레이션 템플릿
_SOURCE_TEMPLATES = {
    "academic": {
        "title_prefix": "연구 논문",
        "content_template": "'{query}'에 대한 학술 연구 결과에 따르면, 해당 주제는 최근 연구 동향에서 주목받고 있습니다.",
        "citation_format": "[학술] {query} 관련 연구, Journal of {domain}, 2026",
    },
    "news": {
        "title_prefix": "뉴스 보도",
        "content_template": "'{query}' 관련 최신 뉴스에 의하면, 이 분야에서 새로운 변화가 관측되고 있습니다.",
        "citation_format": "[뉴스] {query} 동향 보도, {domain} 뉴스, 2026-03",
    },
    "social": {
        "title_prefix": "소셜 미디어 분석",
        "content_template": "'{query}'에 대한 소셜 미디어 반응을 분석한 결과, 사용자들의 관심이 증가하고 있습니다.",
        "citation_format": "[소셜] {query} 관련 SNS 트렌드 분석, 2026",
    },
    "patent": {
        "title_prefix": "특허 문서",
        "content_template": "'{query}' 관련 특허 문서를 조사한 결과, 기술적 진보가 확인됩니다.",
        "citation_format": "[특허] {query} 기술 특허, 특허번호 KR-2026-{hash}, 2026",
    },
    "blog": {
        "title_prefix": "블로그 분석",
        "content_template": "'{query}'에 대한 전문 블로그 콘텐츠를 분석한 결과, 실무 적용 사례가 다수 존재합니다.",
        "citation_format": "[블로그] {query} 실무 가이드, {domain} 블로그, 2026",
    },
}


@dataclass
class Finding:
    """개별 리서치 결과."""
    source: str
    title: str
    content: str
    relevance_score: float
    citation: str


@dataclass
class ResearchReport:
    """멀티소스 리서치 보고서."""
    query: str
    findings: List[Finding] = field(default_factory=list)
    sources_used: List[str] = field(default_factory=list)
    summary: str = ""
    confidence: float = 0.0


def _generate_hash(text: str) -> str:
    """텍스트 기반 짧은 해시 생성 (특허 번호 등에 사용)."""
    return hashlib.md5(text.encode()).hexdigest()[:8].upper()


def _extract_domain(query: str) -> str:
    """쿼리에서 도메인 키워드를 추출합니다."""
    # 쿼리의 첫 번째 명사/키워드를 도메인으로 사용
    words = re.split(r'\s+', query.strip())
    if not words or not words[0]:
        return "Technology"
    return words[0]


def _calculate_relevance(query: str, source: str) -> float:
    """쿼리와 소스 기반으로 관련도 점수를 계산합니다."""
    base_weight = _SOURCE_WEIGHTS.get(source, 0.5)
    # 쿼리 길이가 길수록 구체적 → 관련도 약간 증가
    length_bonus = min(len(query) / 100, 0.05)
    return min(base_weight + length_bonus, 1.0)


def _create_finding(query: str, source: str) -> Finding:
    """단일 소스에 대한 Finding을 생성합니다."""
    template = _SOURCE_TEMPLATES[source]
    domain = _extract_domain(query)
    hash_val = _generate_hash(f"{query}_{source}")

    title = f"{template['title_prefix']}: {query}"
    content = template["content_template"].format(query=query)
    citation = template["citation_format"].format(
        query=query, domain=domain, hash=hash_val
    )
    relevance_score = _calculate_relevance(query, source)

    return Finding(
        source=source,
        title=title,
        content=content,
        relevance_score=relevance_score,
        citation=citation,
    )


def _calculate_confidence(findings: List[Finding], total_sources: int) -> float:
    """전체 신뢰도를 계산합니다.

    소스 수 비율 × 평균 관련도로 산출 (0~1.0).
    """
    if not findings:
        return 0.0

    source_coverage = len(findings) / len(AVAILABLE_SOURCES)
    avg_relevance = sum(f.relevance_score for f in findings) / len(findings)
    confidence = source_coverage * 0.4 + avg_relevance * 0.6
    return round(min(confidence, 1.0), 4)


def _build_summary(query: str, findings: List[Finding]) -> str:
    """리서치 결과 요약문을 생성합니다."""
    if not findings:
        return f"'{query}'에 대한 리서치 결과가 없습니다."

    source_names = ", ".join(sorted(set(f.source for f in findings)))
    count = len(findings)
    avg_score = sum(f.relevance_score for f in findings) / count

    return (
        f"'{query}'에 대해 {count}건의 결과를 {source_names} 소스에서 수집했습니다. "
        f"평균 관련도는 {avg_score:.2f}입니다."
    )


def multi_source_research(
    query: str, sources: Optional[List[str]] = None
) -> ResearchReport:
    """멀티소스 리서치 보고서를 생성합니다.

    Args:
        query: 검색 쿼리 문자열
        sources: 사용할 소스 목록 (None이면 전체 소스 사용)

    Returns:
        ResearchReport 데이터클래스

    Raises:
        ValueError: 쿼리가 비어 있거나 유효하지 않은 소스가 포함된 경우
    """
    if not query or not query.strip():
        raise ValueError("쿼리가 비어 있습니다.")

    query = query.strip()

    # 소스 검증 및 기본값 설정
    if sources is None:
        sources = list(AVAILABLE_SOURCES)
    else:
        invalid = [s for s in sources if s not in AVAILABLE_SOURCES]
        if invalid:
            raise ValueError(f"유효하지 않은 소스: {', '.join(invalid)}")
        # 빈 리스트이면 전체 사용
        if not sources:
            sources = list(AVAILABLE_SOURCES)

    # 각 소스별 Finding 생성
    findings = []
    for source in sources:
        finding = _create_finding(query, source)
        findings.append(finding)

    # 관련도 내림차순 정렬
    findings.sort(key=lambda f: f.relevance_score, reverse=True)

    confidence = _calculate_confidence(findings, len(sources))
    summary = _build_summary(query, findings)

    return ResearchReport(
        query=query,
        findings=findings,
        sources_used=sorted(sources),
        summary=summary,
        confidence=confidence,
    )
