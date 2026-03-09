"""
피드백 학습 에이전트.

사용자 피드백을 수집/분석하여 개선 패턴을 추출하고
만족도 추이를 계산한다.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from collections import Counter
import uuid


VALID_CATEGORIES = {"quality", "style", "accuracy", "relevance"}


@dataclass
class Feedback:
    """사용자 피드백."""
    feedback_id: str
    content_id: str
    rating: int  # 1~5
    comment: str
    category: str  # quality / style / accuracy / relevance
    timestamp: str


@dataclass
class LearningInsight:
    """학습된 인사이트."""
    insight_id: str
    pattern: str
    frequency: int
    avg_rating: float
    suggestion: str


def record_feedback(
    content_id: str,
    rating: int,
    comment: str,
    category: str,
) -> Feedback:
    """
    피드백 기록.

    Args:
        content_id: 대상 콘텐츠 ID.
        rating: 평점 (1~5).
        comment: 코멘트.
        category: 카테고리 (quality/style/accuracy/relevance).

    Returns:
        생성된 Feedback 객체.

    Raises:
        ValueError: rating 범위 초과 또는 잘못된 카테고리.
    """
    if not (1 <= rating <= 5):
        raise ValueError(f"Rating must be 1~5, got {rating}")
    if category not in VALID_CATEGORIES:
        raise ValueError(f"Invalid category: {category}")

    return Feedback(
        feedback_id=uuid.uuid4().hex[:12],
        content_id=content_id,
        rating=rating,
        comment=comment,
        category=category,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _extract_keywords(comment: str) -> list[str]:
    """코멘트에서 핵심 키워드 추출 (간단한 토큰화)."""
    # 2글자 이상 단어만 추출
    words = comment.replace(",", " ").replace(".", " ").split()
    return [w.strip() for w in words if len(w.strip()) >= 2]


def analyze_feedback(feedbacks: list[Feedback]) -> list[LearningInsight]:
    """
    패턴 분석. 빈도 3회 이상 반복되는 패턴 추출.

    카테고리별로 그룹화하여 반복 패턴을 찾고,
    평균 평점과 함께 인사이트를 생성한다.
    """
    if not feedbacks:
        return []

    # 카테고리별 피드백 그룹화
    category_groups: dict[str, list[Feedback]] = {}
    for fb in feedbacks:
        category_groups.setdefault(fb.category, []).append(fb)

    # 키워드 빈도 + 평균 평점 분석
    keyword_data: dict[str, dict] = {}  # keyword -> {count, ratings, category}
    for fb in feedbacks:
        keywords = _extract_keywords(fb.comment)
        for kw in keywords:
            if kw not in keyword_data:
                keyword_data[kw] = {"count": 0, "ratings": [], "category": fb.category}
            keyword_data[kw]["count"] += 1
            keyword_data[kw]["ratings"].append(fb.rating)

    insights = []

    # 빈도 3회 이상인 패턴만 추출
    for pattern, data in keyword_data.items():
        if data["count"] >= 3:
            avg_rating = sum(data["ratings"]) / len(data["ratings"])
            # 평점 기반 제안 생성
            if avg_rating < 3.0:
                suggestion = f"'{pattern}' 관련 품질 개선 필요"
            else:
                suggestion = f"'{pattern}' 관련 긍정적 패턴 유지"

            insights.append(LearningInsight(
                insight_id=uuid.uuid4().hex[:12],
                pattern=pattern,
                frequency=data["count"],
                avg_rating=round(avg_rating, 2),
                suggestion=suggestion,
            ))

    # 카테고리별 반복 패턴 (빈도 3회 이상)
    for category, fbs in category_groups.items():
        if len(fbs) >= 3:
            avg_rating = sum(f.rating for f in fbs) / len(fbs)
            if avg_rating < 3.0:
                suggestion = f"'{category}' 카테고리 전반적 개선 필요"
            else:
                suggestion = f"'{category}' 카테고리 품질 양호"

            insights.append(LearningInsight(
                insight_id=uuid.uuid4().hex[:12],
                pattern=f"category:{category}",
                frequency=len(fbs),
                avg_rating=round(avg_rating, 2),
                suggestion=suggestion,
            ))

    # 빈도 내림차순 정렬
    insights.sort(key=lambda x: x.frequency, reverse=True)
    return insights


def get_improvement_suggestions(insights: list[LearningInsight]) -> list[str]:
    """
    개선 제안 생성.

    낮은 평점(< 3.0)의 인사이트를 우선으로 제안 목록 반환.
    """
    if not insights:
        return []

    suggestions = []
    # 낮은 평점 우선
    sorted_insights = sorted(insights, key=lambda x: x.avg_rating)
    for ins in sorted_insights:
        suggestions.append(ins.suggestion)

    return suggestions


def calculate_satisfaction_trend(feedbacks: list[Feedback]) -> dict:
    """
    만족도 추이 계산.

    Returns:
        {
            "average": 전체 평균 평점,
            "trend": "improving" / "declining" / "stable",
            "count": 피드백 수,
            "rating_distribution": {1: n, 2: n, ...}
        }
    """
    if not feedbacks:
        return {
            "average": 0.0,
            "trend": "stable",
            "count": 0,
            "rating_distribution": {},
        }

    ratings = [fb.rating for fb in feedbacks]
    average = sum(ratings) / len(ratings)

    # 추세: 전반부 vs 후반부 평균 비교
    mid = len(ratings) // 2
    if mid > 0 and len(ratings) >= 4:
        first_half = sum(ratings[:mid]) / mid
        second_half = sum(ratings[mid:]) / len(ratings[mid:])
        diff = second_half - first_half
        if diff > 0.3:
            trend = "improving"
        elif diff < -0.3:
            trend = "declining"
        else:
            trend = "stable"
    else:
        trend = "stable"

    distribution = dict(Counter(ratings))

    return {
        "average": round(average, 2),
        "trend": trend,
        "count": len(feedbacks),
        "rating_distribution": distribution,
    }
