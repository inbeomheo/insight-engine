"""
오디언스 히트맵 서비스

참여도 데이터를 분석하여 세그먼트별 핫존/콜드존 히트맵을 생성합니다.
"""
import logging
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class SegmentData:
    """개별 세그먼트 데이터"""
    segment_name: str
    engagement_rate: float
    size: int
    trend: str  # "up", "down", "stable"


@dataclass
class AudienceHeatmap:
    """오디언스 히트맵 결과"""
    segments: List[SegmentData] = field(default_factory=list)
    hot_zones: List[str] = field(default_factory=list)
    cold_zones: List[str] = field(default_factory=list)
    total_audience: int = 0


# 참여율 임계값
_HOT_THRESHOLD = 0.6
_COLD_THRESHOLD = 0.2


def _classify_trend(values: List[float]) -> str:
    """시계열 값 리스트로 추세를 판별합니다."""
    if len(values) < 2:
        return "stable"
    diff = values[-1] - values[0]
    if diff > 0.05:
        return "up"
    elif diff < -0.05:
        return "down"
    return "stable"


def _build_segment(name: str, entries: List[dict]) -> SegmentData:
    """동일 세그먼트의 항목들을 집계하여 SegmentData를 생성합니다."""
    total_engagement = 0.0
    total_size = 0
    rate_series: List[float] = []

    for entry in entries:
        rate = float(entry.get("engagement_rate", 0))
        size = int(entry.get("size", 0))
        total_engagement += rate * size
        total_size += size
        rate_series.append(rate)

    avg_rate = total_engagement / total_size if total_size > 0 else 0.0
    trend = _classify_trend(rate_series)

    return SegmentData(
        segment_name=name,
        engagement_rate=round(avg_rate, 4),
        size=total_size,
        trend=trend,
    )


def generate_audience_heatmap(engagement_data: List[dict]) -> AudienceHeatmap:
    """참여도 데이터로 오디언스 히트맵을 생성합니다.

    Args:
        engagement_data: 세그먼트별 참여 데이터 리스트.
            각 항목은 {"segment": str, "engagement_rate": float, "size": int} 형태.

    Returns:
        AudienceHeatmap: 세그먼트 분석, 핫존, 콜드존 정보를 포함한 히트맵.
    """
    if not engagement_data:
        logger.warning("빈 참여도 데이터가 전달되었습니다.")
        return AudienceHeatmap()

    # 세그먼트별 그룹핑
    groups: dict[str, List[dict]] = {}
    for entry in engagement_data:
        seg_name = entry.get("segment", "unknown")
        groups.setdefault(seg_name, []).append(entry)

    segments: List[SegmentData] = []
    hot_zones: List[str] = []
    cold_zones: List[str] = []
    total_audience = 0

    for name, entries in groups.items():
        seg = _build_segment(name, entries)
        segments.append(seg)
        total_audience += seg.size

        if seg.engagement_rate >= _HOT_THRESHOLD:
            hot_zones.append(seg.segment_name)
        elif seg.engagement_rate <= _COLD_THRESHOLD:
            cold_zones.append(seg.segment_name)

    # 참여율 내림차순 정렬
    segments.sort(key=lambda s: s.engagement_rate, reverse=True)

    logger.info(
        "히트맵 생성 완료: %d개 세그먼트, 핫존 %d개, 콜드존 %d개",
        len(segments), len(hot_zones), len(cold_zones),
    )

    return AudienceHeatmap(
        segments=segments,
        hot_zones=hot_zones,
        cold_zones=cold_zones,
        total_audience=total_audience,
    )
