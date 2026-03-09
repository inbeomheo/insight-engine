"""
인용 갭 분석 서비스

경쟁사 콘텐츠의 인용(출처 참조) 현황과 우리 콘텐츠를 비교하여
인용이 부족한 주제(갭)를 발견합니다.
AI API 호출 없이 순수 규칙 기반으로 동작합니다.
"""
import re
import logging
from dataclasses import dataclass
from collections import Counter

logger = logging.getLogger(__name__)

# 인용 패턴: [숫자], (출처: ...), [MM:SS], 각주 형식 등
_CITATION_PATTERNS = [
    re.compile(r'\[\d+\]'),                           # [1], [23]
    re.compile(r'\(출처\s*[:：]\s*[^)]+\)'),           # (출처: ...)
    re.compile(r'\(source\s*[:：]\s*[^)]+\)', re.I),   # (source: ...)
    re.compile(r'\(참고\s*[:：]\s*[^)]+\)'),           # (참고: ...)
    re.compile(r'\(ref\s*[:：]\s*[^)]+\)', re.I),      # (ref: ...)
    re.compile(r'https?://\S+'),                       # URL 인용
    re.compile(r'「[^」]+」'),                          # 한국어 서명 인용
    re.compile(r'"[^"]{5,}"'),                         # 영문 서명/인용
]

# 주제 추출용 키워드 최소/최대 길이
_MIN_KEYWORD_LEN = 2
_MAX_KEYWORD_LEN = 12

# 불용어
_STOPWORDS = {
    '그리고', '하지만', '그래서', '따라서', '그러나', '또한', '이것',
    '저것', '여기', '거기', '우리', '이런', '저런', '그런', '어떤',
    '모든', '같은', '다른', '있는', '없는', '하는', '되는', '위한',
    '대한', '통해', '때문', '경우', '이상', '이하', '정도', '이후',
    '사이', '사용', '활용', '방법', '내용', '부분', '관련', '기반',
    '것이', '수가', '것은', '등의', '에서', '으로', '하고', '에는',
    'the', 'and', 'for', 'that', 'this', 'with', 'from', 'are',
    'was', 'were', 'been', 'have', 'has', 'not', 'but', 'all',
    'can', 'will', 'one', 'two', 'its', 'you', 'they', 'may',
}


@dataclass
class GapOpportunity:
    """인용 갭 기회"""
    topic: str
    competitor_citations: int
    our_citations: int
    gap_score: float             # 0~1 (높을수록 기회 큼)
    recommendation: str


def _count_citations_in_text(text: str) -> int:
    """텍스트 내 인용 마커 개수를 셉니다."""
    seen_positions: set[int] = set()
    total = 0
    for pattern in _CITATION_PATTERNS:
        for match in pattern.finditer(text):
            # 동일 위치 중복 방지
            if match.start() not in seen_positions:
                seen_positions.add(match.start())
                total += 1
    return total


def _extract_topics_from_text(text: str) -> list[str]:
    """텍스트에서 주제 키워드를 추출합니다.

    마크다운 헤딩(##), 굵은 글씨(**), 반복 키워드 기반.
    """
    topics: list[str] = []

    # 1. 마크다운 헤딩 추출
    headings = re.findall(r'^#{1,4}\s+(.+)$', text, re.MULTILINE)
    for h in headings:
        clean = re.sub(r'[#*`\[\]()]', '', h).strip()
        if clean and len(clean) >= _MIN_KEYWORD_LEN:
            topics.append(clean)

    # 2. 굵은 글씨 추출
    bold_items = re.findall(r'\*\*([^*]{2,30})\*\*', text)
    for b in bold_items:
        clean = b.strip()
        if clean and clean not in topics:
            topics.append(clean)

    # 3. 빈도 기반 키워드 (3회 이상 등장)
    words = re.findall(r'[가-힣a-zA-Z]+', text)
    filtered = [
        w.lower() for w in words
        if _MIN_KEYWORD_LEN <= len(w) <= _MAX_KEYWORD_LEN
        and w.lower() not in _STOPWORDS
    ]
    freq = Counter(filtered)
    for word, count in freq.most_common(10):
        if count >= 3 and word not in [t.lower() for t in topics]:
            topics.append(word)

    return topics


def _extract_topics_from_citations(competitor_citations: list[dict]) -> dict[str, int]:
    """경쟁사 인용 데이터에서 주제별 인용 수를 집계합니다.

    Args:
        competitor_citations: [{"topic": str, "citation_count": int}, ...]
            또는 [{"topic": str, "content": str}, ...]
    """
    topic_counts: dict[str, int] = {}

    for item in competitor_citations:
        topic = item.get('topic', '').strip()
        if not topic:
            continue

        # citation_count가 명시된 경우 사용
        if 'citation_count' in item:
            count = item['citation_count']
        elif 'content' in item:
            # content에서 인용 수 세기
            count = _count_citations_in_text(item['content'])
        else:
            count = 1

        if topic in topic_counts:
            topic_counts[topic] += count
        else:
            topic_counts[topic] = count

    return topic_counts


def _count_our_citations_by_topic(
    our_content: list[str],
    topics: list[str],
) -> dict[str, int]:
    """우리 콘텐츠에서 각 주제별 인용 수를 셉니다.

    주제 키워드가 포함된 문단 내의 인용 수를 집계합니다.
    """
    topic_counts: dict[str, int] = {}

    for topic in topics:
        total = 0
        pattern = re.compile(re.escape(topic), re.IGNORECASE)

        for content in our_content:
            # 문단 단위로 분리
            paragraphs = re.split(r'\n{2,}', content)
            for para in paragraphs:
                if pattern.search(para):
                    total += _count_citations_in_text(para)

        topic_counts[topic] = total

    return topic_counts


def _calculate_gap_score(competitor_count: int, our_count: int) -> float:
    """갭 점수를 계산합니다 (0~1).

    경쟁사 인용이 많고 우리 인용이 적을수록 높은 점수.
    """
    if competitor_count == 0:
        return 0.0

    # 갭 비율: (경쟁사 - 우리) / 경쟁사
    gap_ratio = max(0, competitor_count - our_count) / competitor_count

    # 경쟁사 인용이 많을수록 가중치 (최대 1.0)
    importance = min(competitor_count / 5, 1.0)

    return round(gap_ratio * importance, 3)


def _generate_recommendation(
    topic: str,
    competitor_count: int,
    our_count: int,
    gap_score: float,
) -> str:
    """주제별 개선 추천 메시지를 생성합니다."""
    if our_count == 0:
        return (
            f"'{topic}' 주제에 인용이 전혀 없습니다. "
            f"경쟁사는 {competitor_count}개의 인용을 포함하고 있으므로 "
            f"출처나 데이터를 추가하세요."
        )
    elif gap_score >= 0.7:
        return (
            f"'{topic}' 주제의 인용이 크게 부족합니다 "
            f"(우리: {our_count}개, 경쟁사: {competitor_count}개). "
            f"신뢰성 있는 출처를 보강하세요."
        )
    elif gap_score >= 0.4:
        return (
            f"'{topic}' 주제에서 경쟁사 대비 인용이 다소 부족합니다 "
            f"(우리: {our_count}개, 경쟁사: {competitor_count}개). "
            f"추가 출처를 검토하세요."
        )
    else:
        return (
            f"'{topic}' 주제의 인용 수준이 경쟁사와 유사합니다 "
            f"(우리: {our_count}개, 경쟁사: {competitor_count}개)."
        )


def find_citation_gaps(
    our_content: list[str],
    competitor_citations: list[dict],
) -> list[GapOpportunity]:
    """경쟁사 인용 대비 우리 콘텐츠의 인용 갭을 발견합니다.

    Args:
        our_content: 우리 콘텐츠 텍스트 목록
        competitor_citations: 경쟁사 인용 데이터
            [{"topic": str, "citation_count": int}, ...]
            또는 [{"topic": str, "content": str}, ...]

    Returns:
        GapOpportunity 리스트 (gap_score 내림차순, 최소 3개 보장)
    """
    if not our_content and not competitor_citations:
        return _ensure_minimum_gaps([], our_content)

    # 1. 경쟁사 주제별 인용 수 집계
    comp_topic_counts = _extract_topics_from_citations(competitor_citations)

    # 2. 우리 콘텐츠에서도 주제 추출 (경쟁사 주제에 없는 것 보완)
    our_topics: set[str] = set(comp_topic_counts.keys())
    for content in (our_content or []):
        for t in _extract_topics_from_text(content):
            our_topics.add(t)

    all_topics = list(our_topics)

    # 3. 우리 콘텐츠의 주제별 인용 수
    our_topic_counts = _count_our_citations_by_topic(
        our_content or [], all_topics,
    )

    # 4. 갭 분석
    gaps: list[GapOpportunity] = []
    for topic in all_topics:
        comp_count = comp_topic_counts.get(topic, 0)
        our_count = our_topic_counts.get(topic, 0)
        gap_score = _calculate_gap_score(comp_count, our_count)

        recommendation = _generate_recommendation(
            topic, comp_count, our_count, gap_score,
        )

        gaps.append(GapOpportunity(
            topic=topic,
            competitor_citations=comp_count,
            our_citations=our_count,
            gap_score=gap_score,
            recommendation=recommendation,
        ))

    # gap_score 내림차순 정렬
    gaps.sort(key=lambda g: g.gap_score, reverse=True)

    # 최소 3개 보장
    return _ensure_minimum_gaps(gaps, our_content)


def _ensure_minimum_gaps(
    gaps: list[GapOpportunity],
    our_content: list[str] | None,
) -> list[GapOpportunity]:
    """최소 3개의 갭 결과를 보장합니다.

    실제 갭이 3개 미만이면 일반적인 인용 개선 권장사항을 추가합니다.
    """
    # 기본 권장 주제 (인용이 부족할 때 일반적으로 필요한 영역)
    default_topics = [
        ('통계/데이터', '수치 근거와 통계 데이터 인용을 추가하면 콘텐츠 신뢰도가 높아집니다.'),
        ('전문가 의견', '해당 분야 전문가나 연구자의 의견을 인용하면 권위가 강화됩니다.'),
        ('사례 연구', '구체적인 사례나 케이스 스터디를 인용하면 설득력이 높아집니다.'),
        ('최신 연구', '최신 논문이나 보고서를 인용하면 콘텐츠 시의성이 향상됩니다.'),
        ('업계 보고서', '업계 보고서나 시장 분석 자료를 인용하면 전문성이 높아집니다.'),
    ]

    existing_topics = {g.topic.lower() for g in gaps}
    idx = 0

    while len(gaps) < 3 and idx < len(default_topics):
        topic, rec = default_topics[idx]
        if topic.lower() not in existing_topics:
            # 우리 콘텐츠 전체에서 해당 주제 인용 수 체크
            our_count = 0
            if our_content:
                for content in our_content:
                    our_count += _count_citations_in_text(content)
                # 전체 인용을 주제 수로 나눔 (대략적 추정)
                our_count = our_count // max(len(gaps) + 1, 1)

            gaps.append(GapOpportunity(
                topic=topic,
                competitor_citations=0,
                our_citations=our_count,
                gap_score=0.5 if our_count == 0 else 0.2,
                recommendation=rec,
            ))
            existing_topics.add(topic.lower())
        idx += 1

    return gaps
