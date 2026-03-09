"""
포트폴리오 바인더 서비스 — 콘텐츠 포트폴리오 관리
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime

VALID_CONTENT_TYPES = ("blog", "video", "podcast", "social", "newsletter", "tutorial")


@dataclass
class PortfolioItem:
    """포트폴리오 항목"""
    item_id: str
    title: str
    content_type: str  # blog / video / podcast / social / newsletter / tutorial
    created_at: str  # ISO 8601
    metrics: dict  # {"views": int, "likes": int, "shares": int}
    tags: list
    featured: bool = False


@dataclass
class Portfolio:
    """포트폴리오"""
    portfolio_id: str
    owner: str
    items: list  # list[PortfolioItem]
    bio: str


def create_portfolio(owner: str, bio: str = "") -> Portfolio:
    """포트폴리오 생성"""
    if not owner.strip():
        raise ValueError("소유자 이름은 필수입니다")

    return Portfolio(
        portfolio_id=str(uuid.uuid4()),
        owner=owner.strip(),
        items=[],
        bio=bio,
    )


def add_item(portfolio: Portfolio, item_config: dict) -> Portfolio:
    """항목 추가

    item_config: {"title": str, "content_type": str, "metrics": dict, "tags": list, "featured": bool}
    """
    content_type = item_config.get("content_type", "blog")
    if content_type not in VALID_CONTENT_TYPES:
        raise ValueError(f"유효하지 않은 콘텐츠 타입: {content_type}. 허용: {VALID_CONTENT_TYPES}")

    item = PortfolioItem(
        item_id=str(uuid.uuid4()),
        title=item_config.get("title", ""),
        content_type=content_type,
        created_at=item_config.get("created_at", datetime.now().isoformat()),
        metrics=item_config.get("metrics", {}),
        tags=item_config.get("tags", []),
        featured=item_config.get("featured", False),
    )

    portfolio.items.append(item)
    return portfolio


def curate_highlights(portfolio: Portfolio, count: int = 5) -> list:
    """하이라이트 선정 (featured 우선, 메트릭 기반 정렬)"""

    def _score(item: PortfolioItem) -> float:
        # featured 항목 우선
        featured_bonus = 10000 if item.featured else 0
        # 메트릭 가중 합산
        views = item.metrics.get("views", 0)
        likes = item.metrics.get("likes", 0)
        shares = item.metrics.get("shares", 0)
        metric_score = views * 1 + likes * 5 + shares * 10
        return featured_bonus + metric_score

    sorted_items = sorted(portfolio.items, key=_score, reverse=True)
    return sorted_items[:count]


def generate_summary(portfolio: Portfolio) -> dict:
    """포트폴리오 요약"""
    type_dist = {}
    for item in portfolio.items:
        type_dist[item.content_type] = type_dist.get(item.content_type, 0) + 1

    total_views = sum(item.metrics.get("views", 0) for item in portfolio.items)
    total_likes = sum(item.metrics.get("likes", 0) for item in portfolio.items)

    return {
        "owner": portfolio.owner,
        "total_items": len(portfolio.items),
        "type_distribution": type_dist,
        "featured_count": sum(1 for item in portfolio.items if item.featured),
        "total_views": total_views,
        "total_likes": total_likes,
    }


def export_portfolio(portfolio: Portfolio) -> dict:
    """포트폴리오 내보내기"""
    items_data = []
    for item in portfolio.items:
        items_data.append({
            "item_id": item.item_id,
            "title": item.title,
            "content_type": item.content_type,
            "created_at": item.created_at,
            "metrics": item.metrics,
            "tags": item.tags,
            "featured": item.featured,
        })

    return {
        "portfolio_id": portfolio.portfolio_id,
        "owner": portfolio.owner,
        "bio": portfolio.bio,
        "items": items_data,
        "total_items": len(items_data),
    }
