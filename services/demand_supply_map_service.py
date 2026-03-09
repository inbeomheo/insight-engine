"""
수요-공급 매핑 서비스

토픽별 수요(검색량, 관심도)와 공급(기존 콘텐츠 수, 경쟁도)을 비교하여
콘텐츠 기회(갭), 과포화 토픽, 균형 토픽을 분류합니다.
규칙 기반 (AI API 호출 없음).
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class Opportunity:
    """수요-공급 갭이 있는 기회 토픽"""
    topic: str
    demand_score: float
    supply_score: float
    gap: float
    priority: str  # "high", "medium", "low"


@dataclass
class DemandSupplyMap:
    """수요-공급 분석 결과"""
    opportunities: List[Opportunity] = field(default_factory=list)
    oversaturated: List[str] = field(default_factory=list)
    balanced: List[str] = field(default_factory=list)


# ── 임계값 ──
_GAP_HIGH_THRESHOLD = 40.0     # 갭 40+ → 높은 기회
_GAP_MEDIUM_THRESHOLD = 20.0   # 갭 20~40 → 중간 기회
_OVERSATURATED_THRESHOLD = -15.0  # 공급 > 수요 15 이상 → 과포화
_BALANCED_TOLERANCE = 15.0      # 갭 절대값 15 이내 → 균형


def _normalize_score(value: float, max_val: float = 100.0) -> float:
    """점수를 0~100 범위로 정규화합니다."""
    return round(max(0.0, min(100.0, (value / max_val) * 100 if max_val > 0 else 0.0)), 1)


def _extract_demand_score(topic_data: dict) -> float:
    """토픽 데이터에서 수요 점수를 추출합니다."""
    # 여러 수요 지표를 가중 합산
    search_volume = topic_data.get("search_volume", 0)
    interest = topic_data.get("interest", 0)
    trend_score = topic_data.get("trend_score", 0)
    mentions = topic_data.get("mentions", 0)

    # 직접 점수가 있으면 우선 사용
    if "demand_score" in topic_data:
        return float(topic_data["demand_score"])

    # 개별 지표 정규화 후 가중 평균
    scores = []
    if search_volume > 0:
        scores.append(min(search_volume / 1000, 100))  # 1000을 100점으로 매핑
    if interest > 0:
        scores.append(float(interest))
    if trend_score > 0:
        scores.append(float(trend_score))
    if mentions > 0:
        scores.append(min(mentions / 50, 100))

    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 1)


def _extract_supply_score(supply_data: dict) -> float:
    """공급 데이터에서 공급 점수를 추출합니다."""
    # 직접 점수가 있으면 우선 사용
    if "supply_score" in supply_data:
        return float(supply_data["supply_score"])

    content_count = supply_data.get("content_count", 0)
    competition = supply_data.get("competition", 0)
    saturation = supply_data.get("saturation", 0)

    scores = []
    if content_count > 0:
        scores.append(min(content_count / 100, 100))  # 100개를 100점으로 매핑
    if competition > 0:
        scores.append(float(competition))
    if saturation > 0:
        scores.append(float(saturation))

    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 1)


def _determine_priority(gap: float) -> str:
    """갭 크기에 따른 우선순위를 결정합니다."""
    if gap >= _GAP_HIGH_THRESHOLD:
        return "high"
    if gap >= _GAP_MEDIUM_THRESHOLD:
        return "medium"
    return "low"


def map_demand_supply(topics: list, supply: list) -> DemandSupplyMap:
    """토픽별 수요-공급을 매핑하여 기회/과포화/균형을 분류합니다.

    Args:
        topics: 수요 데이터 리스트. 각 항목은 최소 {"topic": str} + 수요 지표 포함.
        supply: 공급 데이터 리스트. 각 항목은 최소 {"topic": str} + 공급 지표 포함.

    Returns:
        DemandSupplyMap 분석 결과
    """
    if not topics:
        return DemandSupplyMap()

    # 공급 데이터를 토픽명으로 인덱싱
    supply_index = {}
    for s in (supply or []):
        topic_name = s.get("topic", "")
        if topic_name:
            supply_index[topic_name.lower().strip()] = s

    opportunities: List[Opportunity] = []
    oversaturated: List[str] = []
    balanced: List[str] = []

    for t in topics:
        topic_name = t.get("topic", "")
        if not topic_name:
            continue

        demand = _extract_demand_score(t)
        supply_data = supply_index.get(topic_name.lower().strip(), {})
        supply_score = _extract_supply_score(supply_data)

        gap = round(demand - supply_score, 1)

        if gap >= _GAP_MEDIUM_THRESHOLD:
            # 수요 > 공급 → 기회
            opportunities.append(Opportunity(
                topic=topic_name,
                demand_score=demand,
                supply_score=supply_score,
                gap=gap,
                priority=_determine_priority(gap),
            ))
        elif gap <= _OVERSATURATED_THRESHOLD:
            # 공급 >> 수요 → 과포화
            oversaturated.append(topic_name)
        elif abs(gap) <= _BALANCED_TOLERANCE:
            # 수요 ≈ 공급 → 균형
            balanced.append(topic_name)
        else:
            # 약한 기회 (갭 15~20 사이)
            opportunities.append(Opportunity(
                topic=topic_name,
                demand_score=demand,
                supply_score=supply_score,
                gap=gap,
                priority="low",
            ))

    # 기회는 갭 크기 내림차순 정렬
    opportunities.sort(key=lambda o: o.gap, reverse=True)

    return DemandSupplyMap(
        opportunities=opportunities,
        oversaturated=oversaturated,
        balanced=balanced,
    )
