"""
콘텐츠 건강도 서비스

콘텐츠의 신선도(freshness), 완성도(completeness), 고아 위험(orphan risk)을
분석하여 종합 건강도 점수를 산출합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class HealthReport:
    """콘텐츠 건강도 보고서"""
    overall_score: float         # 0~100 종합 점수
    freshness_score: float       # 0~100 신선도 점수
    completeness_score: float    # 0~100 완성도 점수
    orphan_risk: float           # 0~100 고아 위험 점수 (높을수록 위험)
    recommendations: List[str] = field(default_factory=list)


# ── 마크다운 구조 패턴 ──

_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
_LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
_IMAGE_RE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
_CODE_BLOCK_RE = re.compile(r'```[\s\S]*?```')
_LIST_RE = re.compile(r'^\s*[-*+]\s+|^\s*\d+\.\s+', re.MULTILINE)
_BOLD_RE = re.compile(r'\*\*[^*]+\*\*|__[^_]+__')

# ── 신선도 관련 패턴 ──

# 시간 참조 (높은 감쇠): 구체적 연도/날짜
_TIME_REF_HIGH = [
    re.compile(r'20[0-9]{2}년'),
    re.compile(r'20[0-9]{2}[-./]\d{1,2}'),
    re.compile(
        r'(?:January|February|March|April|May|June|July|August|September|'
        r'October|November|December)\s+20[0-9]{2}',
        re.IGNORECASE,
    ),
]

# 시간 참조 (중간 감쇠): 상대적 시간 표현
_TIME_REF_MED = [
    re.compile(r'(?:올해|작년|내년|최근|지난\s*(?:달|해|주))'),
    re.compile(r'\b(?:this|last|next)\s+(?:year|month|quarter)\b', re.IGNORECASE),
    re.compile(r'최근\s+\d+\s*(?:일|주|개월|년)'),
]

# ── 완성도 체크 항목 ──

_PLACEHOLDER_PATTERNS = [
    re.compile(r'TODO', re.IGNORECASE),
    re.compile(r'TBD', re.IGNORECASE),
    re.compile(r'FIXME', re.IGNORECASE),
    re.compile(r'\[?\s*미정\s*\]?'),
    re.compile(r'\[?\s*추후\s*(?:작성|추가|업데이트)\s*\]?'),
    re.compile(r'\.{3,}'),  # ... 연속
    re.compile(r'\[insert\b', re.IGNORECASE),
    re.compile(r'placeholder', re.IGNORECASE),
]

# ── 문장 분리 ──

_SENTENCE_RE = re.compile(r'(?<=[.!?。])\s+|\n{2,}')


def _count_words(text: str) -> int:
    """한국어+영어 혼합 단어 수 추정"""
    # 영어 단어 수
    en_words = len(re.findall(r'[a-zA-Z]+', text))
    # 한국어 글자 수 (한 글자 ≈ 0.5단어로 환산)
    ko_chars = len(re.findall(r'[가-힣]', text))
    return en_words + ko_chars


def _compute_freshness(content: str, metadata: Optional[dict]) -> tuple:
    """신선도 점수 계산.

    시간 참조가 많을수록 감쇠(decay) 위험이 높아 점수가 낮아집니다.

    Returns:
        (freshness_score, recommendations)
    """
    score = 100.0
    recs = []

    # 시간 참조 감지
    high_count = sum(
        len(p.findall(content)) for p in _TIME_REF_HIGH
    )
    med_count = sum(
        len(p.findall(content)) for p in _TIME_REF_MED
    )

    # 높은 감쇠: 건당 -8점
    score -= high_count * 8.0
    # 중간 감쇠: 건당 -4점
    score -= med_count * 4.0

    if high_count > 0:
        recs.append(f'구체적 날짜/연도 참조 {high_count}건 — 주기적 업데이트 필요')
    if med_count > 0:
        recs.append(f'상대적 시간 표현 {med_count}건 — 시간이 지나면 의미 변질 가능')

    # metadata에 created_at/updated_at이 있으면 추가 감점 판단 가능
    # (현재는 메타데이터 없이도 동작)
    if metadata and metadata.get('days_since_update'):
        days = metadata['days_since_update']
        if days > 365:
            score -= 20.0
            recs.append(f'마지막 업데이트로부터 {days}일 경과 — 전면 검토 권장')
        elif days > 180:
            score -= 10.0
            recs.append(f'마지막 업데이트로부터 {days}일 경과 — 부분 검토 권장')

    return max(0.0, min(100.0, round(score, 1))), recs


def _compute_completeness(content: str) -> tuple:
    """완성도 점수 계산.

    헤딩 구조, 리스트, 링크, 이미지, 코드블록, 볼드체 사용,
    플레이스홀더 존재 여부 등을 종합 판단합니다.

    Returns:
        (completeness_score, recommendations)
    """
    score = 100.0
    recs = []

    word_count = _count_words(content)

    # 1) 최소 분량 체크
    if word_count < 50:
        score -= 40.0
        recs.append('콘텐츠 분량이 매우 적습니다 (50단어 미만)')
    elif word_count < 150:
        score -= 15.0
        recs.append('콘텐츠 분량이 부족합니다 (150단어 미만)')

    # 2) 구조 요소 점검
    headings = _HEADING_RE.findall(content)
    links = _LINK_RE.findall(content)
    images = _IMAGE_RE.findall(content)
    lists = _LIST_RE.findall(content)
    code_blocks = _CODE_BLOCK_RE.findall(content)
    bolds = _BOLD_RE.findall(content)

    # 헤딩 없으면 감점
    if not headings and word_count > 200:
        score -= 15.0
        recs.append('헤딩(제목) 없음 — 섹션 구분으로 가독성 개선 가능')

    # 링크 없으면 약간 감점 (참조/출처)
    if not links and word_count > 300:
        score -= 5.0
        recs.append('외부 링크 없음 — 참조/출처 추가 권장')

    # 리스트도 볼드체도 없으면 감점 (스캔 가독성)
    if not lists and not bolds and word_count > 200:
        score -= 5.0
        recs.append('리스트/볼드체 없음 — 스캔 가독성 개선 권장')

    # 3) 플레이스홀더 감지 → 미완성
    placeholder_count = sum(
        len(p.findall(content)) for p in _PLACEHOLDER_PATTERNS
    )
    if placeholder_count > 0:
        penalty = min(30.0, placeholder_count * 10.0)
        score -= penalty
        recs.append(f'미완성 표시 {placeholder_count}건 감지 (TODO/TBD/미정 등)')

    return max(0.0, min(100.0, round(score, 1))), recs


def _compute_orphan_risk(content: str, metadata: Optional[dict]) -> tuple:
    """고아 위험 점수 계산.

    다른 콘텐츠로부터 참조되지 않을 가능성을 추정합니다.
    내부 링크가 적고 구조가 독립적일수록 위험이 높아집니다.

    Returns:
        (orphan_risk, recommendations)  — 높을수록 위험
    """
    risk = 0.0
    recs = []

    links = _LINK_RE.findall(content)
    headings = _HEADING_RE.findall(content)
    word_count = _count_words(content)

    # 링크가 전혀 없으면 고아 위험 증가
    if not links:
        risk += 30.0
        recs.append('내부/외부 링크 없음 — 다른 콘텐츠와 연결 부족')
    elif len(links) < 2:
        risk += 15.0
        recs.append('링크가 1개뿐 — 추가 연결 권장')

    # 제목이 없으면 검색/네비게이션에서 누락 위험
    if not headings:
        risk += 20.0
        recs.append('헤딩 없음 — 목차/사이트맵에서 누락될 수 있음')

    # 분량이 너무 적으면 고아 위험
    if word_count < 100:
        risk += 25.0
        recs.append('분량 부족 — 독립 콘텐츠로 가치 낮음')

    # metadata에 incoming_links 정보가 있으면 활용
    if metadata and metadata.get('incoming_links') is not None:
        incoming = metadata['incoming_links']
        if incoming == 0:
            risk += 25.0
            recs.append('인바운드 링크 0건 — 다른 콘텐츠에서 참조되지 않음')
        elif incoming < 3:
            risk += 10.0

    return max(0.0, min(100.0, round(risk, 1))), recs


def compute_health_score(
    content: str,
    metadata: Optional[dict] = None,
) -> HealthReport:
    """콘텐츠 건강도 점수를 산출합니다.

    freshness(신선도) + completeness(완성도) + orphan_risk(고아위험)를
    가중 합산하여 overall_score를 계산합니다.

    Args:
        content: 분석할 콘텐츠 텍스트
        metadata: 선택적 메타데이터 (days_since_update, incoming_links 등)

    Returns:
        HealthReport (overall_score, freshness_score, completeness_score,
                      orphan_risk, recommendations)
    """
    if not content or not content.strip():
        return HealthReport(
            overall_score=0.0,
            freshness_score=0.0,
            completeness_score=0.0,
            orphan_risk=100.0,
            recommendations=['콘텐츠가 비어 있습니다.'],
        )

    freshness, fresh_recs = _compute_freshness(content, metadata)
    completeness, comp_recs = _compute_completeness(content)
    orphan_risk, orphan_recs = _compute_orphan_risk(content, metadata)

    # 가중 합산: 신선도 30% + 완성도 50% + (100 - 고아위험) 20%
    overall = (
        freshness * 0.3
        + completeness * 0.5
        + (100.0 - orphan_risk) * 0.2
    )
    overall = max(0.0, min(100.0, round(overall, 1)))

    recommendations = fresh_recs + comp_recs + orphan_recs

    return HealthReport(
        overall_score=overall,
        freshness_score=freshness,
        completeness_score=completeness,
        orphan_risk=orphan_risk,
        recommendations=recommendations,
    )
