"""
ROI 플래너 서비스 — 콘텐츠 투자 대비 수익 시뮬레이션
"""

import math
from dataclasses import dataclass, field

VALID_CATEGORIES = ("content", "ads", "tools", "team")


@dataclass
class Investment:
    """투자 항목"""
    category: str  # content / ads / tools / team
    amount: float
    period_months: int


@dataclass
class ROIProjection:
    """ROI 예측"""
    total_investment: float
    projected_revenue: float
    roi_pct: float  # (수익 - 투자) / 투자 * 100
    breakeven_month: int  # 손익분기점 월 (0이면 달성 불가)
    monthly_projections: list  # [{"month": int, "revenue": float, "cost": float, "cumulative_profit": float}]


def calculate_roi(investments: list, revenue_estimate: float) -> ROIProjection:
    """ROI 계산"""
    total_investment = sum(inv.amount for inv in investments)

    if total_investment == 0:
        return ROIProjection(
            total_investment=0,
            projected_revenue=revenue_estimate,
            roi_pct=float("inf") if revenue_estimate > 0 else 0.0,
            breakeven_month=0,
            monthly_projections=[],
        )

    roi_pct = (revenue_estimate - total_investment) / total_investment * 100

    # 월별 예측 (최대 투자 기간)
    max_months = max((inv.period_months for inv in investments), default=1)
    monthly_cost = total_investment / max_months
    monthly_revenue = revenue_estimate / max_months
    projections = project_monthly_simple(monthly_cost, monthly_revenue, max_months)

    breakeven = find_breakeven(projections)

    return ROIProjection(
        total_investment=total_investment,
        projected_revenue=revenue_estimate,
        roi_pct=round(roi_pct, 2),
        breakeven_month=breakeven,
        monthly_projections=projections,
    )


def project_monthly(investment: float, growth_rate: float, months: int) -> list:
    """월별 수익 예측 (성장률 적용)"""
    projections = []
    monthly_cost = investment / max(months, 1)
    cumulative_profit = 0.0

    for m in range(1, months + 1):
        # 초기 월 수익 = 비용의 50%, 성장률 복리 적용
        revenue = (monthly_cost * 0.5) * ((1 + growth_rate) ** m)
        profit = revenue - monthly_cost
        cumulative_profit += profit

        projections.append({
            "month": m,
            "revenue": round(revenue, 2),
            "cost": round(monthly_cost, 2),
            "cumulative_profit": round(cumulative_profit, 2),
        })

    return projections


def project_monthly_simple(monthly_cost: float, monthly_revenue: float, months: int) -> list:
    """단순 월별 예측 (균등 배분)"""
    projections = []
    cumulative_profit = 0.0

    for m in range(1, months + 1):
        profit = monthly_revenue - monthly_cost
        cumulative_profit += profit

        projections.append({
            "month": m,
            "revenue": round(monthly_revenue, 2),
            "cost": round(monthly_cost, 2),
            "cumulative_profit": round(cumulative_profit, 2),
        })

    return projections


def find_breakeven(projections: list) -> int:
    """손익분기점 월 (누적 수익이 0 이상이 되는 첫 월, 없으면 0)"""
    for p in projections:
        if p["cumulative_profit"] >= 0:
            return p["month"]
    return 0


def compare_scenarios(scenarios: list) -> dict:
    """시나리오 비교"""
    if not scenarios:
        return {"count": 0, "scenarios": []}

    summaries = []
    for i, s in enumerate(scenarios):
        summaries.append({
            "scenario": i + 1,
            "total_investment": s.total_investment,
            "projected_revenue": s.projected_revenue,
            "roi_pct": s.roi_pct,
            "breakeven_month": s.breakeven_month,
        })

    best = max(summaries, key=lambda x: x["roi_pct"])

    return {
        "count": len(scenarios),
        "scenarios": summaries,
        "best_scenario": best["scenario"],
        "best_roi_pct": best["roi_pct"],
    }
