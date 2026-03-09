"""캠페인 태그 분석 서비스

태그별 캠페인 성과를 집계하여 참여율, 도달 추정치, 감성 분석,
상위 게시물, 개선 추천 사항을 포함한 종합 리포트를 생성한다.
"""
import re
import math
from dataclasses import dataclass, field


@dataclass
class CampaignReport:
    """캠페인 태그 분석 리포트"""
    tag: str                             # 분석 대상 태그
    total_posts: int                     # 총 게시물 수
    engagement_rate: float               # 참여율 0~100 (%)
    reach_estimate: int                  # 도달 추정치
    top_posts: list[dict] = field(default_factory=list)      # 상위 게시물
    sentiment: str = "neutral"           # "positive" | "neutral" | "negative"
    recommendations: list[str] = field(default_factory=list)  # 개선 추천


# ── 감성 분석용 키워드 사전 ────────────────────────────────────
_POSITIVE_WORDS = {
    # 한국어
    "좋아요", "최고", "감사", "추천", "대박", "훌륭", "유익",
    "재밌", "신선", "만족", "행복", "기대", "성공", "효과적",
    # 영어
    "great", "love", "awesome", "excellent", "amazing",
    "good", "best", "recommend", "helpful", "useful",
    "fantastic", "wonderful", "perfect", "impressive",
}

_NEGATIVE_WORDS = {
    # 한국어
    "별로", "실망", "최악", "싫어", "불만", "짜증", "후회",
    "부족", "아쉽", "문제", "불편", "걱정", "위험", "실패",
    # 영어
    "bad", "terrible", "worst", "hate", "disappointing",
    "poor", "waste", "boring", "awful", "useless",
    "horrible", "annoying", "problem", "fail",
}

# 텍스트에서 단어 추출용 패턴
_WORD_PATTERN = re.compile(r'[가-힣a-zA-Z]+')


def _normalize_tag(tag: str) -> str:
    """태그 문자열을 정규화한다.

    앞뒤 공백 제거, 소문자 변환, 선행 '#' 제거.

    Args:
        tag: 원본 태그 문자열

    Returns:
        정규화된 태그
    """
    tag = tag.strip().lower()
    if tag.startswith("#"):
        tag = tag[1:]
    return tag


def _compute_engagement(posts: list[dict]) -> float:
    """게시물 목록의 평균 참여율을 계산한다.

    참여율 = (likes + comments + shares) / total_posts
    결과를 0~100 범위로 클리핑한다.

    Args:
        posts: 게시물 딕셔너리 리스트

    Returns:
        참여율 (0~100)
    """
    if not posts:
        return 0.0

    total_engagement = 0
    for post in posts:
        likes = max(0, post.get("likes", 0))
        comments = max(0, post.get("comments", 0))
        shares = max(0, post.get("shares", 0))
        total_engagement += likes + comments + shares

    # 게시물당 평균 참여도를 100 기준으로 정규화
    avg_engagement = total_engagement / len(posts)
    # 참여도를 0~100 스케일로 변환 (1000 상호작용 = 100%)
    rate = min(100.0, (avg_engagement / 1000) * 100)
    return round(rate, 2)


def _estimate_reach(posts: list[dict]) -> int:
    """도달 추정치를 계산한다.

    (총 상호작용 합계) × 3 을 기반 추정치로 사용한다.
    소셜 미디어에서 상호작용의 약 3배가 도달(노출) 수로 추정됨.

    Args:
        posts: 게시물 딕셔너리 리스트

    Returns:
        도달 추정치 (0 이상 정수)
    """
    if not posts:
        return 0

    total_interactions = 0
    for post in posts:
        likes = max(0, post.get("likes", 0))
        comments = max(0, post.get("comments", 0))
        shares = max(0, post.get("shares", 0))
        total_interactions += likes + comments + shares

    # 상호작용의 3배를 도달로 추정
    return max(0, math.ceil(total_interactions * 3))


def _analyze_sentiment(posts: list[dict]) -> str:
    """게시물 텍스트의 전체 감성을 분석한다.

    긍정/부정 키워드 빈도 비교로 판정한다.

    Args:
        posts: 게시물 딕셔너리 리스트

    Returns:
        "positive" | "neutral" | "negative"
    """
    positive_count = 0
    negative_count = 0

    for post in posts:
        text = post.get("text", "")
        if not text:
            continue

        words = set(_WORD_PATTERN.findall(text.lower()))

        positive_count += len(words & _POSITIVE_WORDS)
        negative_count += len(words & _NEGATIVE_WORDS)

    if positive_count == 0 and negative_count == 0:
        return "neutral"
    if positive_count > negative_count:
        return "positive"
    if negative_count > positive_count:
        return "negative"
    return "neutral"


def _rank_top_posts(posts: list[dict], top_n: int = 5) -> list[dict]:
    """상호작용 합계 기준 상위 게시물을 선별한다.

    Args:
        posts: 게시물 딕셔너리 리스트
        top_n: 반환할 상위 게시물 수

    Returns:
        상위 게시물 리스트 (상호작용 내림차순)
    """
    if not posts:
        return []

    def _score(post: dict) -> int:
        return (
            max(0, post.get("likes", 0))
            + max(0, post.get("comments", 0))
            + max(0, post.get("shares", 0))
        )

    sorted_posts = sorted(posts, key=_score, reverse=True)
    return sorted_posts[:top_n]


def _generate_recommendations(
    engagement_rate: float,
    sentiment: str,
    posts: list[dict],
) -> list[str]:
    """분석 결과를 기반으로 개선 추천 사항을 생성한다.

    Args:
        engagement_rate: 참여율 (0~100)
        sentiment: 감성 분석 결과
        posts: 게시물 리스트

    Returns:
        추천 사항 문자열 리스트
    """
    recommendations = []

    # 참여율 기반 추천
    if engagement_rate < 5:
        recommendations.append("참여율이 낮습니다. 해시태그 다양화와 게시 시간 최적화를 권장합니다.")
    elif engagement_rate < 20:
        recommendations.append("참여율이 보통 수준입니다. 시각 콘텐츠(이미지/영상) 비중을 늘려보세요.")
    else:
        recommendations.append("참여율이 높습니다. 현재 콘텐츠 전략을 유지하세요.")

    # 감성 기반 추천
    if sentiment == "negative":
        recommendations.append("부정적 반응이 우세합니다. 댓글 분석 후 불만 요인을 파악하세요.")
    elif sentiment == "neutral":
        recommendations.append("감성이 중립적입니다. 더 강한 CTA(행동 유도)를 시도해보세요.")

    # 게시물 수 기반 추천
    if len(posts) < 5:
        recommendations.append("데이터가 부족합니다. 최소 10개 이상의 게시물로 재분석을 권장합니다.")
    elif len(posts) >= 50:
        recommendations.append("충분한 데이터가 있습니다. 주간/월간 추세 분석을 추가로 고려하세요.")

    # 공유 비중 분석
    total_shares = sum(max(0, p.get("shares", 0)) for p in posts)
    total_likes = sum(max(0, p.get("likes", 0)) for p in posts)
    if total_likes > 0 and total_shares / total_likes < 0.1:
        recommendations.append("공유율이 낮습니다. 공유를 유도하는 콘텐츠 형식을 실험해보세요.")

    return recommendations


def analyze_campaign(tag: str, posts: list[dict]) -> CampaignReport:
    """태그별 캠페인 성과를 집계한다.

    Args:
        tag: 캠페인 태그 (예: "#마케팅", "AI")
        posts: 게시물 리스트. 각 항목은 아래 형식:
            {"text": "...", "likes": N, "shares": N, "comments": N}

    Returns:
        CampaignReport 데이터클래스

    Raises:
        ValueError: tag가 빈 문자열이거나 posts가 None인 경우
    """
    if not tag or not tag.strip():
        raise ValueError("tag는 빈 문자열일 수 없습니다")
    if posts is None:
        raise ValueError("posts는 None일 수 없습니다")

    normalized_tag = _normalize_tag(tag)
    engagement_rate = _compute_engagement(posts)
    reach_estimate = _estimate_reach(posts)
    sentiment = _analyze_sentiment(posts)
    top_posts = _rank_top_posts(posts)
    recommendations = _generate_recommendations(engagement_rate, sentiment, posts)

    return CampaignReport(
        tag=normalized_tag,
        total_posts=len(posts),
        engagement_rate=engagement_rate,
        reach_estimate=reach_estimate,
        top_posts=top_posts,
        sentiment=sentiment,
        recommendations=recommendations,
    )


def compare_campaigns(reports: list[CampaignReport]) -> dict:
    """여러 캠페인 리포트를 비교 요약한다.

    Args:
        reports: CampaignReport 리스트

    Returns:
        비교 요약 딕셔너리:
        {
            "best_engagement": {"tag": str, "rate": float},
            "best_reach": {"tag": str, "reach": int},
            "total_posts": int,
            "avg_engagement": float,
        }

    Raises:
        ValueError: reports가 비어있는 경우
    """
    if not reports:
        raise ValueError("비교할 리포트가 없습니다")

    best_engagement = max(reports, key=lambda r: r.engagement_rate)
    best_reach = max(reports, key=lambda r: r.reach_estimate)
    total_posts = sum(r.total_posts for r in reports)
    avg_engagement = round(
        sum(r.engagement_rate for r in reports) / len(reports), 2
    )

    return {
        "best_engagement": {
            "tag": best_engagement.tag,
            "rate": best_engagement.engagement_rate,
        },
        "best_reach": {
            "tag": best_reach.tag,
            "reach": best_reach.reach_estimate,
        },
        "total_posts": total_posts,
        "avg_engagement": avg_engagement,
    }
