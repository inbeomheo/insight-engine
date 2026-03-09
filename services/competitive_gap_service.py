"""
경쟁 갭 분석 서비스

자사 토픽과 경쟁사 토픽을 비교하여
커버리지 갭, 중복 영역, 고유 강점, 커버리지 비율을 분석합니다.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


@dataclass
class TopicGap:
    """토픽 갭 정보"""
    topic: str
    competitor_coverage: int
    opportunity_score: float


@dataclass
class GapAnalysis:
    """경쟁 갭 분석 결과"""
    gaps: List[TopicGap] = field(default_factory=list)
    overlaps: List[str] = field(default_factory=list)
    unique_strengths: List[str] = field(default_factory=list)
    coverage_ratio: float = 0.0


def _normalize_topic(topic: str) -> str:
    """토픽 문자열을 정규화합니다 (소문자, 공백 제거)."""
    return topic.lower().strip()


def _find_overlaps(own_set: Set[str], competitor_set: Set[str]) -> List[str]:
    """자사와 경쟁사가 모두 다루는 토픽을 찾습니다."""
    return sorted(own_set & competitor_set)


def _find_gaps(
    own_set: Set[str],
    competitor_topics: List[str],
) -> List[TopicGap]:
    """경쟁사만 다루는 토픽(갭)을 찾고 기회 점수를 계산합니다."""
    # 경쟁사 토픽 빈도 계산
    freq: Dict[str, int] = {}
    for t in competitor_topics:
        normalized = _normalize_topic(t)
        freq[normalized] = freq.get(normalized, 0) + 1

    competitor_set = set(freq.keys())
    gap_topics = {t for t in (competitor_set - own_set) if t.strip()}

    gaps: List[TopicGap] = []
    max_freq = max(freq.values()) if freq else 1

    for topic in gap_topics:
        coverage = freq[topic]
        # 기회 점수: 경쟁사 커버리지가 높을수록 중요한 토픽
        opportunity = round(coverage / max_freq, 4)
        gaps.append(TopicGap(
            topic=topic,
            competitor_coverage=coverage,
            opportunity_score=opportunity,
        ))

    # 기회 점수 내림차순 정렬
    gaps.sort(key=lambda g: g.opportunity_score, reverse=True)
    return gaps


def _find_unique_strengths(own_set: Set[str], competitor_set: Set[str]) -> List[str]:
    """자사만 다루는 고유 토픽(강점)을 찾습니다."""
    return sorted(own_set - competitor_set)


def _calculate_coverage_ratio(own_set: Set[str], competitor_set: Set[str]) -> float:
    """전체 토픽 대비 자사 커버리지 비율을 계산합니다."""
    all_topics = own_set | competitor_set
    if not all_topics:
        return 0.0
    return round(len(own_set) / len(all_topics), 4)


def find_gaps(
    own_topics: List[str],
    competitor_topics: List[str],
) -> GapAnalysis:
    """자사와 경쟁사 토픽 간 갭을 분석합니다.

    Args:
        own_topics: 자사가 다루는 토픽 리스트.
        competitor_topics: 경쟁사가 다루는 토픽 리스트.

    Returns:
        GapAnalysis: 갭, 중복, 고유 강점, 커버리지 비율 정보.
    """
    if not own_topics and not competitor_topics:
        logger.warning("자사/경쟁사 토픽 모두 비어있습니다.")
        return GapAnalysis()

    own_normalized = {_normalize_topic(t) for t in own_topics if t.strip()}
    competitor_normalized = {_normalize_topic(t) for t in competitor_topics if t.strip()}

    overlaps = _find_overlaps(own_normalized, competitor_normalized)
    gaps = _find_gaps(own_normalized, competitor_topics)
    unique_strengths = _find_unique_strengths(own_normalized, competitor_normalized)
    coverage_ratio = _calculate_coverage_ratio(own_normalized, competitor_normalized)

    logger.info(
        "경쟁 갭 분석 완료: 갭 %d개, 중복 %d개, 고유 강점 %d개, 커버리지 %.1f%%",
        len(gaps), len(overlaps), len(unique_strengths), coverage_ratio * 100,
    )

    return GapAnalysis(
        gaps=gaps,
        overlaps=overlaps,
        unique_strengths=unique_strengths,
        coverage_ratio=coverage_ratio,
    )
