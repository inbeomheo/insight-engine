"""
감성 타임라인 서비스 — 콘텐츠 관련 텍스트의 시간별 감성 변화 추적
"""

from dataclasses import dataclass, field
import re


@dataclass
class SentimentPoint:
    """단일 감성 분석 포인트"""
    timestamp: str
    sentiment: float  # -1 ~ 1
    label: str  # "positive" | "negative" | "neutral"
    text_excerpt: str


@dataclass
class SentimentTimeline:
    """감성 타임라인 전체 결과"""
    content_id: str
    points: list[SentimentPoint] = field(default_factory=list)
    trend: str = "stable"  # "improving" | "declining" | "stable"
    average_sentiment: float = 0.0


# 한국어 + 영어 감성 사전
_POSITIVE_WORDS = {
    "좋", "훌륭", "최고", "감사", "대박", "추천", "유익", "재밌",
    "멋지", "완벽", "사랑", "행복", "만족", "기대", "응원",
    "good", "great", "excellent", "love", "best", "amazing",
    "awesome", "fantastic", "helpful", "thank", "wonderful",
}

_NEGATIVE_WORDS = {
    "나쁘", "별로", "실망", "짜증", "최악", "싫", "불만", "문제",
    "안됨", "에러", "버그", "느리", "어렵", "복잡", "부족",
    "bad", "terrible", "hate", "worst", "poor", "awful",
    "horrible", "disappointing", "broken", "slow", "useless",
}


def _compute_sentiment(text: str) -> tuple[float, str]:
    """
    단순 사전 기반 감성 점수 계산.

    Returns:
        (score, label): score는 -1~1, label은 positive/negative/neutral
    """
    text_lower = text.lower()
    pos_count = sum(1 for w in _POSITIVE_WORDS if w in text_lower)
    neg_count = sum(1 for w in _NEGATIVE_WORDS if w in text_lower)
    total = pos_count + neg_count

    if total == 0:
        return 0.0, "neutral"

    # -1 ~ 1 범위로 정규화
    score = (pos_count - neg_count) / total
    score = max(-1.0, min(1.0, score))

    if score > 0.1:
        label = "positive"
    elif score < -0.1:
        label = "negative"
    else:
        label = "neutral"

    return round(score, 3), label


def _determine_trend(points: list[SentimentPoint]) -> str:
    """감성 포인트 리스트에서 전체 추세 판단"""
    if len(points) < 2:
        return "stable"

    # 전반부 / 후반부 평균 비교
    mid = len(points) // 2
    first_half = [p.sentiment for p in points[:mid]]
    second_half = [p.sentiment for p in points[mid:]]

    avg_first = sum(first_half) / len(first_half) if first_half else 0
    avg_second = sum(second_half) / len(second_half) if second_half else 0

    diff = avg_second - avg_first
    if diff > 0.15:
        return "improving"
    elif diff < -0.15:
        return "declining"
    return "stable"


def _make_excerpt(text: str, max_len: int = 80) -> str:
    """텍스트 발췌 생성"""
    text = re.sub(r'\s+', ' ', text.strip())
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def build_sentiment_timeline(
    content_id: str,
    texts: list[dict],
) -> SentimentTimeline:
    """
    콘텐츠 관련 텍스트의 시간별 감성 변화 분석.

    Args:
        content_id: 콘텐츠 식별자
        texts: [{"text": "...", "timestamp": "2026-01-01T00:00:00"}]

    Returns:
        SentimentTimeline: 감성 타임라인 결과
    """
    if not texts:
        return SentimentTimeline(content_id=content_id)

    # 타임스탬프 순 정렬
    sorted_texts = sorted(texts, key=lambda t: t.get("timestamp", ""))

    points = []
    for item in sorted_texts:
        text = item.get("text", "")
        timestamp = item.get("timestamp", "")
        if not text.strip():
            continue

        score, label = _compute_sentiment(text)
        point = SentimentPoint(
            timestamp=timestamp,
            sentiment=score,
            label=label,
            text_excerpt=_make_excerpt(text),
        )
        points.append(point)

    if not points:
        return SentimentTimeline(content_id=content_id)

    avg_sentiment = sum(p.sentiment for p in points) / len(points)
    trend = _determine_trend(points)

    return SentimentTimeline(
        content_id=content_id,
        points=points,
        trend=trend,
        average_sentiment=round(avg_sentiment, 3),
    )
