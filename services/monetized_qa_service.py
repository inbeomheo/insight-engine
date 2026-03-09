"""
수익형 Q&A 서비스 — 유료 Q&A 콘텐츠 관리
"""

import uuid
from dataclasses import dataclass, field

VALID_TIERS = ("free", "premium", "exclusive")


@dataclass
class QAItem:
    """Q&A 항목"""
    qa_id: str
    question: str
    answer: str
    tier: str  # free / premium / exclusive
    price: float
    views: int = 0
    purchases: int = 0


@dataclass
class QACatalog:
    """Q&A 카탈로그"""
    catalog_id: str
    items: list  # list[QAItem]
    total_revenue: float = 0.0


def create_qa(question: str, answer: str, tier: str = "free", price: float = 0.0) -> QAItem:
    """Q&A 항목 생성"""
    if tier not in VALID_TIERS:
        raise ValueError(f"유효하지 않은 티어: {tier}. 허용: {VALID_TIERS}")
    if tier == "free" and price > 0:
        price = 0.0  # 무료 티어는 가격 0
    if price < 0:
        raise ValueError("가격은 0 이상이어야 합니다")
    if not question.strip():
        raise ValueError("질문은 필수입니다")

    return QAItem(
        qa_id=str(uuid.uuid4()),
        question=question.strip(),
        answer=answer.strip(),
        tier=tier,
        price=price,
    )


def filter_by_tier(catalog: QACatalog, tier: str) -> list:
    """티어별 필터링"""
    return [item for item in catalog.items if item.tier == tier]


def calculate_revenue(catalog: QACatalog) -> float:
    """총 매출 계산 (purchases × price)"""
    revenue = sum(item.purchases * item.price for item in catalog.items)
    catalog.total_revenue = revenue
    return revenue


def get_popular(catalog: QACatalog, top_k: int = 5) -> list:
    """조회수 기반 인기 Q&A"""
    sorted_items = sorted(catalog.items, key=lambda x: x.views, reverse=True)
    return sorted_items[:top_k]


def preview_answer(item: QAItem, preview_length: int = 50) -> str:
    """무료 미리보기 (앞 N자 + '...')"""
    if item.tier == "free":
        return item.answer  # 무료는 전체 공개

    if len(item.answer) <= preview_length:
        return item.answer

    return item.answer[:preview_length] + "..."
