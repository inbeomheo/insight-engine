"""
이사회 내러티브 보드 서비스 — 경영진/이사회용 보드 팩 보고서 생성
"""

from dataclasses import dataclass, field


@dataclass
class BoardPack:
    """이사회 보고용 내러티브 팩"""
    period: str
    highlights: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    narrative: str = ""
    action_items: list[str] = field(default_factory=list)


# 지원하는 보고 기간
VALID_PERIODS = {"weekly", "monthly", "quarterly"}


def _extract_highlights(channel_data: dict) -> list[str]:
    """채널 데이터에서 주요 하이라이트 추출"""
    highlights = []
    total = channel_data.get("total_content", 0)
    published = channel_data.get("published", 0)
    views = channel_data.get("total_views", 0)
    subscribers = channel_data.get("subscribers", 0)
    growth = channel_data.get("subscriber_growth", 0)

    if total > 0:
        highlights.append(f"콘텐츠 {total}건 생성 완료")
    if published > 0:
        highlights.append(f"{published}건 발행, 발행률 {published / max(total, 1) * 100:.0f}%")
    if views > 0:
        highlights.append(f"총 조회수 {views:,}회 달성")
    if subscribers > 0:
        highlights.append(f"구독자 {subscribers:,}명")
    if growth > 0:
        highlights.append(f"구독자 증가 +{growth:,}명")
    elif growth < 0:
        highlights.append(f"구독자 감소 {growth:,}명 — 원인 분석 필요")

    # 성과 데이터
    top_content = channel_data.get("top_content")
    if top_content:
        highlights.append(f"최고 성과 콘텐츠: '{top_content}'")

    if not highlights:
        highlights.append("기간 내 데이터 없음")

    return highlights


def _compute_metrics(channel_data: dict) -> dict:
    """핵심 성과 지표 계산"""
    total = channel_data.get("total_content", 0)
    published = channel_data.get("published", 0)
    views = channel_data.get("total_views", 0)
    engagement = channel_data.get("total_engagement", 0)

    metrics = {
        "total_content": total,
        "published": published,
        "publish_rate": round(published / max(total, 1) * 100, 1),
        "total_views": views,
        "avg_views_per_content": round(views / max(published, 1), 1),
        "total_engagement": engagement,
        "engagement_rate": round(engagement / max(views, 1) * 100, 2) if views > 0 else 0.0,
    }

    # 비용 데이터 (있는 경우)
    cost = channel_data.get("total_cost", 0)
    if cost > 0:
        metrics["total_cost"] = round(cost, 2)
        metrics["cost_per_content"] = round(cost / max(total, 1), 2)
        metrics["cost_per_view"] = round(cost / max(views, 1), 4) if views > 0 else 0

    return metrics


def _build_narrative(
    period: str,
    highlights: list[str],
    metrics: dict,
    channel_data: dict,
) -> str:
    """내러티브 보고서 본문 생성"""
    period_label = {
        "weekly": "금주",
        "monthly": "이번 달",
        "quarterly": "이번 분기",
    }.get(period, period)

    sections = []

    # 개요
    total = metrics.get("total_content", 0)
    published = metrics.get("published", 0)
    sections.append(
        f"{period_label} 콘텐츠 운영 요약: "
        f"총 {total}건 생성, {published}건 발행."
    )

    # 성과
    views = metrics.get("total_views", 0)
    eng_rate = metrics.get("engagement_rate", 0)
    if views > 0:
        sections.append(
            f"조회수 {views:,}회, 인게이지먼트율 {eng_rate}% 기록."
        )

    # 비용
    cost = metrics.get("total_cost")
    cpv = metrics.get("cost_per_view")
    if cost is not None and cost > 0:
        sections.append(
            f"총 비용 ${cost:.2f}, 조회당 비용 ${cpv:.4f}."
        )

    # 핵심 인사이트
    growth = channel_data.get("subscriber_growth", 0)
    if growth > 0:
        sections.append(f"구독자 {growth:,}명 순증으로 성장 추세 유지.")
    elif growth < 0:
        sections.append(f"구독자 {abs(growth):,}명 감소. 리텐션 전략 검토 필요.")

    return " ".join(sections)


def _generate_action_items(metrics: dict, channel_data: dict) -> list[str]:
    """다음 기간 액션 아이템 생성"""
    items = []

    publish_rate = metrics.get("publish_rate", 0)
    if publish_rate < 80:
        items.append(f"발행률 {publish_rate}% → 80% 이상 목표 설정")

    eng_rate = metrics.get("engagement_rate", 0)
    if eng_rate < 3:
        items.append("인게이지먼트율 3% 미만 — CTA/댓글 유도 전략 강화")

    avg_views = metrics.get("avg_views_per_content", 0)
    if avg_views < 100:
        items.append("콘텐츠당 평균 조회수 저조 — 배포 채널 확대 검토")

    growth = channel_data.get("subscriber_growth", 0)
    if growth <= 0:
        items.append("구독자 정체/감소 — 시리즈 콘텐츠 또는 콜라보 기획")

    cost = metrics.get("cost_per_content", 0)
    if cost > 1.0:
        items.append(f"콘텐츠당 비용 ${cost:.2f} — 모델/프롬프트 최적화로 비용 절감")

    if not items:
        items.append("현재 지표 양호 — 기존 전략 유지 및 신규 포맷 실험 권장")

    return items


def generate_board_pack(
    channel_data: dict,
    period: str = "monthly",
) -> BoardPack:
    """
    이사회용 내러티브 보드 팩 생성.

    Args:
        channel_data: {
            "total_content": N, "published": N, "total_views": N,
            "total_engagement": N, "subscribers": N, "subscriber_growth": N,
            "total_cost": N, "top_content": "제목"
        }
        period: "weekly" | "monthly" | "quarterly"

    Returns:
        BoardPack: 보드 팩 보고서
    """
    if period not in VALID_PERIODS:
        raise ValueError(f"지원하지 않는 기간: {period}. 가능: {VALID_PERIODS}")

    if not channel_data:
        return BoardPack(
            period=period,
            highlights=["데이터 없음"],
            metrics={},
            narrative=f"{period} 기간 데이터가 제공되지 않았습니다.",
            action_items=["데이터 수집 체계 구축 필요"],
        )

    highlights = _extract_highlights(channel_data)
    metrics = _compute_metrics(channel_data)
    narrative = _build_narrative(period, highlights, metrics, channel_data)
    action_items = _generate_action_items(metrics, channel_data)

    return BoardPack(
        period=period,
        highlights=highlights,
        metrics=metrics,
        narrative=narrative,
        action_items=action_items,
    )
