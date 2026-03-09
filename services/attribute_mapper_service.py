"""제품 속성 추출 서비스 — 리뷰 자막에서 제품 속성을 매핑"""
import re
from dataclasses import dataclass


@dataclass
class ProductAttribute:
    """제품 속성"""
    name: str
    value: str
    sentiment: str  # positive, negative, neutral
    mention_count: int


_VALID_SENTIMENTS = {"positive", "negative", "neutral"}

# 긍정/부정 키워드 사전
_POSITIVE_KEYWORDS = {
    "좋", "훌륭", "최고", "만족", "추천", "편리", "빠르", "가벼",
    "good", "great", "excellent", "amazing", "love", "best", "fast",
    "nice", "perfect", "comfortable", "quality",
}

_NEGATIVE_KEYWORDS = {
    "나쁘", "별로", "불편", "느리", "무겁", "비싸", "아쉬",
    "bad", "poor", "slow", "heavy", "expensive", "worst", "terrible",
    "disappointing", "broken", "cheap",
}

# 일반 속성 패턴: "속성(이/가/은/는) 값" 형태
_ATTR_PATTERN = re.compile(
    r'([가-힣a-zA-Z]{2,10})[이가은는]\s+([\S]+)',
    re.UNICODE,
)

# "속성: 값" 또는 "속성 - 값" 형태
_COLON_PATTERN = re.compile(
    r'([가-힣a-zA-Z]{2,15})\s*[:\-]\s*([^\n,]{1,30})',
    re.UNICODE,
)


def _detect_sentiment(context: str) -> str:
    """문맥에서 감성을 판별한다."""
    context_lower = context.lower()
    pos_count = sum(1 for kw in _POSITIVE_KEYWORDS if kw in context_lower)
    neg_count = sum(1 for kw in _NEGATIVE_KEYWORDS if kw in context_lower)

    if pos_count > neg_count:
        return "positive"
    elif neg_count > pos_count:
        return "negative"
    return "neutral"


def _extract_attributes(transcript: str) -> dict[str, dict]:
    """자막에서 속성-값 쌍을 추출한다."""
    attributes: dict[str, dict] = {}
    sentences = re.split(r'[.!?\n。]', transcript)

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # 패턴 1: 조사 기반
        for match in _ATTR_PATTERN.finditer(sentence):
            name = match.group(1).strip()
            value = match.group(2).strip()
            sentiment = _detect_sentiment(sentence)
            key = name.lower()
            if key in attributes:
                attributes[key]["mention_count"] += 1
                # 감성이 다르면 가장 최근 것 유지
                attributes[key]["sentiment"] = sentiment
            else:
                attributes[key] = {
                    "name": name,
                    "value": value,
                    "sentiment": sentiment,
                    "mention_count": 1,
                }

        # 패턴 2: 콜론/하이픈 기반
        for match in _COLON_PATTERN.finditer(sentence):
            name = match.group(1).strip()
            value = match.group(2).strip()
            sentiment = _detect_sentiment(sentence)
            key = name.lower()
            if key in attributes:
                attributes[key]["mention_count"] += 1
                attributes[key]["sentiment"] = sentiment
            else:
                attributes[key] = {
                    "name": name,
                    "value": value,
                    "sentiment": sentiment,
                    "mention_count": 1,
                }

    return attributes


def map_product_attributes(review_transcript: str) -> list[ProductAttribute]:
    """리뷰 자막에서 제품 속성을 추출한다.

    Args:
        review_transcript: 리뷰 영상 자막 텍스트

    Returns:
        ProductAttribute 리스트 (mention_count 내림차순 정렬)
    """
    if not review_transcript or not review_transcript.strip():
        return []

    raw = _extract_attributes(review_transcript)

    result = [
        ProductAttribute(
            name=attr["name"],
            value=attr["value"],
            sentiment=attr["sentiment"],
            mention_count=attr["mention_count"],
        )
        for attr in raw.values()
    ]

    # 언급 횟수 내림차순 정렬
    result.sort(key=lambda a: a.mention_count, reverse=True)
    return result
