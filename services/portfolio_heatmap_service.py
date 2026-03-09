"""
포트폴리오 히트맵 서비스

콘텐츠 라이브러리를 시장 토픽과 대조하여
주제별 커버리지 히트맵을 생성하고, 리프레시가 필요한 콘텐츠를 식별합니다.
"""
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ── 데이터 모델 ──────────────────────────────────────────────

@dataclass
class HeatmapCell:
    """히트맵 단일 셀 — 하나의 토픽에 대한 커버리지 정보"""
    topic: str
    coverage: str       # "oversaturated" | "well_covered" | "underexplored" | "gap"
    content_count: int  # 해당 토픽을 다루는 콘텐츠 수
    market_demand: float  # 0~1 범위, 시장 수요 지수


@dataclass
class HeatmapData:
    """히트맵 전체 데이터"""
    cells: list[HeatmapCell] = field(default_factory=list)
    total_topics: int = 0
    oversaturated: list[str] = field(default_factory=list)  # 과포화 토픽명
    gaps: list[str] = field(default_factory=list)            # 미진출 토픽명


# ── 커버리지 분류 기준 ────────────────────────────────────────

# (콘텐츠 수 기준, 커버리지 라벨)
# market_demand가 높을수록 "well_covered" 임계치가 올라감
_COVERAGE_LABELS = {
    "oversaturated": "oversaturated",
    "well_covered": "well_covered",
    "underexplored": "underexplored",
    "gap": "gap",
}


def _classify_coverage(content_count: int, market_demand: float) -> str:
    """콘텐츠 수와 시장 수요를 기반으로 커버리지 분류.

    분류 로직:
    - gap: 콘텐츠 0개
    - underexplored: 콘텐츠 1~2개이고 수요가 중간 이상 (>0.3)
    - well_covered: 적정 수준 (수요 대비 콘텐츠 균형)
    - oversaturated: 수요 대비 콘텐츠 과다
    """
    if content_count == 0:
        return "gap"

    # 수요 기반 적정 콘텐츠 수 산출 (수요 0.5 → 적정 3개, 수요 1.0 → 적정 5개)
    optimal = max(1, round(market_demand * 5))

    ratio = content_count / optimal if optimal > 0 else content_count

    if ratio > 2.0:
        return "oversaturated"
    elif ratio >= 0.6:
        return "well_covered"
    else:
        return "underexplored"


def _count_topic_in_library(topic: str, library: list[dict]) -> int:
    """라이브러리에서 특정 토픽을 다루는 콘텐츠 수를 계산.

    매칭 기준:
    1. topics 리스트에 토픽이 포함 (대소문자 무시)
    2. title에 토픽이 포함 (대소문자 무시)
    """
    topic_lower = topic.lower()
    count = 0
    for item in library:
        # topics 리스트 매칭
        topics = item.get("topics", [])
        if any(topic_lower == t.lower() for t in topics):
            count += 1
            continue
        # title 폴백 매칭
        title = item.get("title", "")
        if topic_lower in title.lower():
            count += 1
    return count


def _compute_market_demand(
    topic: str,
    market_topics: list[str],
) -> float:
    """시장 토픽 리스트에서의 위치(순서) 기반 수요 점수 산출.

    리스트 앞쪽일수록 수요가 높다고 가정합니다.
    수요 = 1.0 - (index / total) → 1위는 ~1.0, 마지막은 ~0.0+
    """
    if not market_topics:
        return 0.5  # 기본값

    topic_lower = topic.lower()
    for i, mt in enumerate(market_topics):
        if mt.lower() == topic_lower:
            # 선형 감소: 0번째 → 1.0에 가까움, 마지막 → 0.0에 가까움
            return round(1.0 - (i / len(market_topics)), 4)

    return 0.0  # 시장 토픽에 없는 경우


# ── 리프레시 큐 관련 ──────────────────────────────────────────

def _compute_freshness(content: dict) -> float:
    """콘텐츠의 신선도 점수 (0~1). 1에 가까울수록 신선.

    지수 감쇠(exponential decay) 사용:
    - freshness = e^(-lambda * days)
    - lambda = 0.01 → 반감기 약 69일
    """
    published = content.get("published_at") or content.get("created_at")
    if not published:
        return 0.0  # 날짜 없으면 리프레시 필요로 간주

    try:
        if isinstance(published, str):
            # ISO 형식 파싱
            dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
        elif isinstance(published, datetime):
            dt = published
        else:
            return 0.0

        # timezone-aware 비교
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        days = (now - dt).days
        decay_lambda = 0.01
        return round(math.exp(-decay_lambda * max(0, days)), 4)
    except (ValueError, TypeError):
        return 0.0


def _compute_performance_score(content: dict) -> float:
    """성과 점수 정규화 (0~1). performance 필드가 없으면 0.5 기본값."""
    perf = content.get("performance")
    if perf is None:
        return 0.5
    if isinstance(perf, (int, float)):
        return max(0.0, min(1.0, perf / 100)) if perf > 1 else max(0.0, min(1.0, perf))
    return 0.5


# ── 공개 API ─────────────────────────────────────────────────

def generate_heatmap(
    library: list[dict],
    market_topics: list[str],
) -> HeatmapData:
    """콘텐츠 라이브러리 vs 시장 토픽 매트릭스 히트맵을 생성합니다.

    Args:
        library: 콘텐츠 목록. 각 항목은 {"title": str, "topics": list[str], "performance": float}
        market_topics: 시장 수요 토픽 리스트 (앞쪽일수록 수요 높음)

    Returns:
        HeatmapData: 셀 목록, 과포화/갭 토픽 요약
    """
    if not market_topics:
        return HeatmapData(cells=[], total_topics=0, oversaturated=[], gaps=[])

    cells: list[HeatmapCell] = []
    oversaturated: list[str] = []
    gaps: list[str] = []

    for topic in market_topics:
        count = _count_topic_in_library(topic, library)
        demand = _compute_market_demand(topic, market_topics)
        coverage = _classify_coverage(count, demand)

        cells.append(HeatmapCell(
            topic=topic,
            coverage=coverage,
            content_count=count,
            market_demand=demand,
        ))

        if coverage == "oversaturated":
            oversaturated.append(topic)
        elif coverage == "gap":
            gaps.append(topic)

    result = HeatmapData(
        cells=cells,
        total_topics=len(market_topics),
        oversaturated=oversaturated,
        gaps=gaps,
    )

    logger.info(
        "히트맵 생성 완료: %d 토픽 (과포화: %d, 갭: %d)",
        result.total_topics, len(oversaturated), len(gaps),
    )
    return result


def queue_for_refresh(
    content_list: list[dict],
    decay_threshold: float = 0.5,
) -> list[dict]:
    """리프레시가 필요한 콘텐츠 큐를 생성합니다.

    신선도가 decay_threshold 미만이거나, 성과가 낮은 콘텐츠를 선별합니다.

    Args:
        content_list: 콘텐츠 목록. 각 항목에 published_at/created_at, performance 필드 권장.
        decay_threshold: 신선도 임계치 (기본 0.5). 이 미만이면 리프레시 후보.

    Returns:
        리프레시 필요 콘텐츠 목록. 각 항목에 refresh_reason, freshness, priority 추가.
        priority 내림차순 정렬 (높을수록 리프레시 시급).
    """
    if not content_list:
        return []

    if not (0.0 <= decay_threshold <= 1.0):
        raise ValueError(f"decay_threshold는 0~1 범위여야 합니다. 받은 값: {decay_threshold}")

    queue: list[dict] = []

    for content in content_list:
        freshness = _compute_freshness(content)
        perf_score = _compute_performance_score(content)
        reasons: list[str] = []

        # 신선도 기준 체크
        if freshness < decay_threshold:
            reasons.append(f"신선도 부족 ({freshness:.2f} < {decay_threshold})")

        # 성과 기준 체크 (하위 30%)
        if perf_score < 0.3:
            reasons.append(f"낮은 성과 ({perf_score:.2f})")

        if not reasons:
            continue

        # 우선순위: 신선도 낮을수록 + 성과 낮을수록 높은 우선순위
        priority = round((1.0 - freshness) * 0.6 + (1.0 - perf_score) * 0.4, 4)

        queue.append({
            **content,
            "freshness": freshness,
            "refresh_reason": reasons,
            "priority": priority,
        })

    # 우선순위 내림차순 정렬
    queue.sort(key=lambda x: x["priority"], reverse=True)

    logger.info("리프레시 큐 생성: %d / %d 콘텐츠 선별", len(queue), len(content_list))
    return queue
