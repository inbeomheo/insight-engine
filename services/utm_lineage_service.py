"""
UTM 리니지 추적 서비스

UTM 파라미터 데이터를 분석하여 캠페인별 터치포인트 추적,
기여도 가중치, 최고 성과 캠페인을 도출합니다.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class CampaignTrace:
    """개별 캠페인 추적 데이터"""
    utm_source: str
    utm_medium: str
    utm_campaign: str
    visits: int
    conversions: int
    attribution_weight: float


@dataclass
class UTMLineage:
    """UTM 리니지 추적 결과"""
    campaigns: List[CampaignTrace] = field(default_factory=list)
    total_touchpoints: int = 0
    top_performing: str = ""


def _build_campaign_key(entry: dict) -> str:
    """UTM 데이터에서 캠페인 고유 키를 생성합니다."""
    source = entry.get("utm_source", "direct")
    medium = entry.get("utm_medium", "none")
    campaign = entry.get("utm_campaign", "unknown")
    return f"{source}|{medium}|{campaign}"


def _aggregate_campaigns(utm_data: List[dict]) -> Dict[str, dict]:
    """동일 캠페인 키의 데이터를 집계합니다."""
    aggregated: Dict[str, dict] = {}

    for entry in utm_data:
        key = _build_campaign_key(entry)
        if key not in aggregated:
            aggregated[key] = {
                "utm_source": entry.get("utm_source", "direct"),
                "utm_medium": entry.get("utm_medium", "none"),
                "utm_campaign": entry.get("utm_campaign", "unknown"),
                "visits": 0,
                "conversions": 0,
            }
        aggregated[key]["visits"] += int(entry.get("visits", 1))
        aggregated[key]["conversions"] += int(entry.get("conversions", 0))

    return aggregated


def _calculate_attribution(aggregated: Dict[str, dict]) -> List[CampaignTrace]:
    """캠페인별 기여도 가중치를 계산합니다."""
    total_conversions = sum(c["conversions"] for c in aggregated.values())

    traces: List[CampaignTrace] = []
    for data in aggregated.values():
        weight = (
            data["conversions"] / total_conversions
            if total_conversions > 0
            else 1.0 / max(len(aggregated), 1)
        )
        traces.append(CampaignTrace(
            utm_source=data["utm_source"],
            utm_medium=data["utm_medium"],
            utm_campaign=data["utm_campaign"],
            visits=data["visits"],
            conversions=data["conversions"],
            attribution_weight=round(weight, 4),
        ))

    # 기여도 내림차순 정렬
    traces.sort(key=lambda t: t.attribution_weight, reverse=True)
    return traces


def trace_utm_lineage(utm_data: List[dict]) -> UTMLineage:
    """UTM 데이터로 캠페인 리니지를 추적합니다.

    Args:
        utm_data: UTM 파라미터 데이터 리스트.
            각 항목은 {"utm_source", "utm_medium", "utm_campaign",
                       "visits", "conversions"} 형태.

    Returns:
        UTMLineage: 캠페인 추적, 총 터치포인트, 최고 성과 캠페인 정보.
    """
    if not utm_data:
        logger.warning("빈 UTM 데이터가 전달되었습니다.")
        return UTMLineage()

    aggregated = _aggregate_campaigns(utm_data)
    campaigns = _calculate_attribution(aggregated)

    total_touchpoints = sum(c.visits for c in campaigns)

    # 최고 성과: 전환율 기준 (전환/방문)
    top_performing = ""
    if campaigns:
        best = max(
            campaigns,
            key=lambda c: c.conversions / max(c.visits, 1),
        )
        top_performing = best.utm_campaign

    logger.info(
        "UTM 리니지 추적 완료: %d개 캠페인, %d 터치포인트, 최고=%s",
        len(campaigns), total_touchpoints, top_performing,
    )

    return UTMLineage(
        campaigns=campaigns,
        total_touchpoints=total_touchpoints,
        top_performing=top_performing,
    )
