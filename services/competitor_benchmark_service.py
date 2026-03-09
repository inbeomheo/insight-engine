"""
경쟁사 벤치마크 서비스

여러 계정(채널)의 지표를 분석·비교하여 순위, 강점, 약점,
인사이트를 담은 벤치마크 보고서를 생성합니다.
"""
import logging
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class AccountRank:
    """계정별 순위 정보"""
    account_name: str
    score: float                    # 종합 점수 (0.0~100.0)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)


@dataclass
class BenchmarkReport:
    """벤치마크 분석 보고서"""
    accounts_analyzed: int
    rankings: List[AccountRank] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)


# 지표별 가중치 (합산 1.0)
_METRIC_WEIGHTS = {
    'subscribers': 0.25,
    'avg_views': 0.30,
    'engagement_rate': 0.25,
    'upload_frequency': 0.10,
    'growth_rate': 0.10,
}


def _safe_float(value, default: float = 0.0) -> float:
    """안전하게 float 변환합니다."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_values(values: list) -> list:
    """값 리스트를 0~1 범위로 정규화합니다 (min-max)."""
    if not values:
        return []
    min_v = min(values)
    max_v = max(values)
    if max_v == min_v:
        return [0.5] * len(values)
    return [(v - min_v) / (max_v - min_v) for v in values]


def _compute_score(account: dict, all_accounts: list) -> float:
    """단일 계정의 종합 점수를 산출합니다 (0~100)."""
    score = 0.0
    for metric, weight in _METRIC_WEIGHTS.items():
        values = [_safe_float(a.get(metric, 0)) for a in all_accounts]
        account_val = _safe_float(account.get(metric, 0))
        normalized = _normalize_values(values)
        idx = next(
            (i for i, a in enumerate(all_accounts) if a is account),
            None
        )
        if idx is not None and idx < len(normalized):
            score += normalized[idx] * weight * 100
    return round(score, 2)


def _identify_strengths(account: dict, all_accounts: list) -> list:
    """계정의 강점 지표를 식별합니다."""
    strengths = []
    for metric in _METRIC_WEIGHTS:
        val = _safe_float(account.get(metric, 0))
        others = [_safe_float(a.get(metric, 0)) for a in all_accounts if a is not account]
        if not others:
            continue
        avg_others = sum(others) / len(others)
        if avg_others > 0 and val > avg_others * 1.2:
            ratio = val / avg_others
            strengths.append(f"{metric} 평균 대비 {ratio:.1f}배 우수")
    return strengths


def _identify_weaknesses(account: dict, all_accounts: list) -> list:
    """계정의 약점 지표를 식별합니다."""
    weaknesses = []
    for metric in _METRIC_WEIGHTS:
        val = _safe_float(account.get(metric, 0))
        others = [_safe_float(a.get(metric, 0)) for a in all_accounts if a is not account]
        if not others:
            continue
        avg_others = sum(others) / len(others)
        if avg_others > 0 and val < avg_others * 0.8:
            ratio = val / avg_others if avg_others > 0 else 0
            weaknesses.append(f"{metric} 평균 대비 {ratio:.1f}배 미달")
    return weaknesses


def _generate_insights(rankings: list, accounts: list) -> list:
    """전체 분석 인사이트를 생성합니다."""
    insights = []
    if not rankings:
        return insights

    # 1위 계정 인사이트
    top = rankings[0]
    insights.append(f"최고 성과 계정: {top.account_name} (종합 {top.score}점)")

    # 점수 편차 분석
    scores = [r.score for r in rankings]
    if len(scores) >= 2:
        gap = scores[0] - scores[-1]
        if gap > 30:
            insights.append(f"1위와 최하위 간 점수 차이가 {gap:.1f}점으로 격차가 큽니다")
        elif gap < 10:
            insights.append("전체적으로 경쟁이 치열하며 점수 차이가 작습니다")

    # 공통 약점 발견
    all_weaknesses = []
    for r in rankings:
        all_weaknesses.extend(r.weaknesses)
    if all_weaknesses:
        from collections import Counter
        common = Counter(all_weaknesses).most_common(1)
        if common and common[0][1] > 1:
            insights.append(f"다수 계정의 공통 약점: {common[0][0]}")

    return insights


def benchmark_competitors(accounts: list) -> BenchmarkReport:
    """경쟁 계정들을 벤치마크 분석합니다.

    Args:
        accounts: 계정 딕셔너리 리스트. 각 항목에
                  name, subscribers, avg_views, engagement_rate,
                  upload_frequency, growth_rate 등 포함.

    Returns:
        BenchmarkReport 보고서
    """
    if not accounts:
        return BenchmarkReport(accounts_analyzed=0, rankings=[], insights=["분석할 계정이 없습니다"])

    rankings = []
    for account in accounts:
        name = account.get('name', account.get('account_name', 'Unknown'))
        score = _compute_score(account, accounts)
        strengths = _identify_strengths(account, accounts)
        weaknesses = _identify_weaknesses(account, accounts)
        rankings.append(AccountRank(
            account_name=name,
            score=score,
            strengths=strengths,
            weaknesses=weaknesses,
        ))

    # 점수 내림차순 정렬
    rankings.sort(key=lambda r: r.score, reverse=True)

    insights = _generate_insights(rankings, accounts)

    return BenchmarkReport(
        accounts_analyzed=len(accounts),
        rankings=rankings,
        insights=insights,
    )
