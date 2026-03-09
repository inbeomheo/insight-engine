"""
공공서비스 카드 서비스 — 공공 정보를 카드 형태로 구조화
"""

import uuid
from dataclasses import dataclass, field
from typing import Optional


VALID_CATEGORIES = ('health', 'education', 'welfare', 'housing', 'employment')


@dataclass
class ServiceCard:
    """공공서비스 카드"""
    card_id: str
    title: str
    category: str  # health / education / welfare / housing / employment
    eligibility: list[str]
    how_to_apply: str
    deadline: Optional[str]
    contact: str


def create_card(title: str, category: str, eligibility: list[str],
                how_to: str, deadline: Optional[str] = None, contact: str = '') -> ServiceCard:
    """서비스 카드 생성"""
    if category not in VALID_CATEGORIES:
        raise ValueError(f"유효하지 않은 카테고리: {category}. 사용 가능: {VALID_CATEGORIES}")

    return ServiceCard(
        card_id=str(uuid.uuid4())[:8],
        title=title,
        category=category,
        eligibility=eligibility,
        how_to_apply=how_to,
        deadline=deadline,
        contact=contact
    )


def filter_by_category(cards: list[ServiceCard], category: str) -> list[ServiceCard]:
    """카테고리별 필터링"""
    return [c for c in cards if c.category == category]


def check_eligibility(card: ServiceCard, user_profile: dict) -> bool:
    """자격 요건 매칭 — user_profile의 tags 리스트와 eligibility 교집합 확인"""
    user_tags = {t.lower() for t in user_profile.get('tags', [])}
    card_eligibility = {e.lower() for e in card.eligibility}

    # 모든 자격 요건을 충족해야 함
    return card_eligibility.issubset(user_tags) if card_eligibility else True


def format_card(card: ServiceCard) -> str:
    """카드를 텍스트 포맷으로 변환"""
    lines = [
        f"[{card.category.upper()}] {card.title}",
        f"자격 요건: {', '.join(card.eligibility) if card.eligibility else '제한 없음'}",
        f"신청 방법: {card.how_to_apply}",
    ]
    if card.deadline:
        lines.append(f"마감일: {card.deadline}")
    if card.contact:
        lines.append(f"문의처: {card.contact}")
    return '\n'.join(lines)
