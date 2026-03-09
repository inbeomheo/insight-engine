"""
스폰서 워크스페이스 서비스 — 스폰서십 콘텐츠 관리 공간
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime

VALID_STATUSES = ("draft", "active", "completed", "cancelled")
STATUS_TRANSITIONS = {
    "draft": ("active", "cancelled"),
    "active": ("completed", "cancelled"),
    "completed": (),
    "cancelled": (),
}


@dataclass
class SponsorDeal:
    """스폰서 딜"""
    deal_id: str
    sponsor_name: str
    budget: float
    deliverables: list  # ["블로그 포스트", "영상 1편", ...]
    status: str  # draft / active / completed / cancelled
    start_date: str
    end_date: str


@dataclass
class SponsorWorkspace:
    """스폰서 워크스페이스"""
    workspace_id: str
    deals: list  # list[SponsorDeal]
    total_revenue: float = 0.0


def create_deal(sponsor_name: str, budget: float, deliverables: list,
                start_date: str = "", end_date: str = "") -> SponsorDeal:
    """스폰서 딜 생성 (초기 상태: draft)"""
    if budget < 0:
        raise ValueError("예산은 0 이상이어야 합니다")
    if not sponsor_name.strip():
        raise ValueError("스폰서 이름은 필수입니다")

    now = datetime.now().strftime("%Y-%m-%d")
    return SponsorDeal(
        deal_id=str(uuid.uuid4()),
        sponsor_name=sponsor_name.strip(),
        budget=budget,
        deliverables=deliverables or [],
        status="draft",
        start_date=start_date or now,
        end_date=end_date or now,
    )


def update_deal_status(deal: SponsorDeal, new_status: str) -> SponsorDeal:
    """딜 상태 변경 (유효한 전이만 허용)"""
    if new_status not in VALID_STATUSES:
        raise ValueError(f"유효하지 않은 상태: {new_status}")

    allowed = STATUS_TRANSITIONS.get(deal.status, ())
    if new_status not in allowed:
        raise ValueError(f"'{deal.status}' → '{new_status}' 전이 불가. 허용: {allowed}")

    deal.status = new_status
    return deal


def calculate_revenue(workspace: SponsorWorkspace) -> float:
    """총 수익 계산 (active + completed 딜)"""
    revenue = sum(
        d.budget for d in workspace.deals
        if d.status in ("active", "completed")
    )
    workspace.total_revenue = revenue
    return revenue


def get_active_deals(workspace: SponsorWorkspace) -> list:
    """활성 딜 목록"""
    return [d for d in workspace.deals if d.status == "active"]


def check_deliverables(deal: SponsorDeal) -> dict:
    """산출물 체크리스트 상태"""
    result = {
        "deal_id": deal.deal_id,
        "sponsor": deal.sponsor_name,
        "total": len(deal.deliverables),
        "items": [],
    }
    for item in deal.deliverables:
        result["items"].append({
            "deliverable": item,
            "completed": False,  # 순수 메타데이터 — 실제 완료 추적은 외부
        })
    return result
