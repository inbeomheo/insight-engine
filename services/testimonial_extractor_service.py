"""증거 후기 추출 서비스 — 인터뷰 자막에서 사회적 증거 카드 추출

인터뷰/대담 형식의 자막에서 인용 가능한 발화(testimonial)를 추출하고,
발화자, 맥락, 감성, 신뢰도 점수를 포함한 카드로 구성합니다.
"""
import logging
import re
from dataclasses import dataclass, asdict
from typing import List, Optional

logger = logging.getLogger(__name__)

# 인용 가능한 발화 탐지 패턴
_QUOTE_PATTERNS = [
    # 직접 인용 ("..." 형태)
    r'"([^"]{10,200})"',
    r'"([^"]{10,200})"',
    r'「([^」]{10,200})」',
    # 발화자 표시 (이름: 발화 형태)
    r'([가-힣A-Za-z]+)\s*[:：]\s*(.{10,200}?)(?=[.!?。]|$)',
]

# 감성 분석 키워드
_SENTIMENT_KEYWORDS = {
    "positive": [
        "좋", "훌륭", "최고", "감사", "만족", "추천", "사랑", "행복",
        "성공", "뛰어나", "편리", "효과", "도움", "great", "love",
        "excellent", "amazing", "wonderful", "happy", "thank",
    ],
    "negative": [
        "나쁘", "별로", "불만", "실망", "힘들", "어렵", "문제", "불편",
        "걱정", "싫", "후회", "bad", "terrible", "disappointed",
        "difficult", "hate", "problem", "worst",
    ],
}

# 신뢰도 가중 키워드 (경험/데이터 기반 발언)
_CREDIBILITY_BOOSTERS = [
    "경험", "년", "데이터", "연구", "결과", "실제로", "직접",
    "사용해보", "테스트", "검증", "전문", "experience", "research",
    "data", "years", "tested", "proven", "professional",
]


@dataclass
class TestimonialCard:
    """사회적 증거 카드"""
    __test__ = False  # pytest 수집 방지 (Test로 시작하는 클래스명)

    quote: str
    speaker: str
    context: str
    sentiment: str           # "positive" | "neutral" | "negative"
    credibility_score: float  # 0.0~1.0


def extract_testimonials(transcript: str) -> List[TestimonialCard]:
    """인터뷰 자막에서 사회적 증거 카드를 추출합니다.

    Args:
        transcript: 자막 텍스트

    Returns:
        TestimonialCard 리스트

    Raises:
        ValueError: 자막이 비어있을 때
    """
    if not transcript or not transcript.strip():
        raise ValueError("자막 텍스트가 비어있습니다")

    stripped = transcript.strip()
    if len(stripped) < 20:
        raise ValueError("자막이 너무 짧아 후기를 추출할 수 없습니다 (최소 20자)")

    cards: List[TestimonialCard] = []

    # 1단계: 직접 인용 추출
    cards.extend(_extract_direct_quotes(stripped))

    # 2단계: 발화자:발화 형태 추출
    cards.extend(_extract_speaker_quotes(stripped))

    # 3단계: 의견/감상 문장 추출
    cards.extend(_extract_opinion_sentences(stripped))

    # 중복 제거 (동일 인용문)
    cards = _deduplicate_cards(cards)

    # 신뢰도 순 정렬
    cards.sort(key=lambda c: c.credibility_score, reverse=True)

    return cards


def _extract_direct_quotes(text: str) -> List[TestimonialCard]:
    """직접 인용 부호로 감싼 발언을 추출합니다."""
    cards = []
    patterns = [
        r'"([^"]{10,200})"',
        r'"([^"]{10,200})"',
        r'「([^」]{10,200})」',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text):
            quote = match.group(1).strip()
            if not quote or len(quote) < 10:
                continue

            # 인용 앞뒤 맥락에서 발화자 추출 시도
            start = max(0, match.start() - 50)
            context_before = text[start:match.start()]
            speaker = _extract_speaker_from_context(context_before)

            sentiment = _analyze_sentiment(quote)
            credibility = _calculate_credibility(quote, speaker)

            # 인용 주변 맥락
            end = min(len(text), match.end() + 50)
            context = text[start:end].strip()[:150]

            cards.append(TestimonialCard(
                quote=quote,
                speaker=speaker,
                context=context,
                sentiment=sentiment,
                credibility_score=credibility,
            ))

    return cards


def _extract_speaker_quotes(text: str) -> List[TestimonialCard]:
    """'발화자: 발화' 형태의 텍스트를 추출합니다."""
    cards = []
    pattern = r'([가-힣A-Za-z]{2,20})\s*[:：]\s*(.{10,200}?)(?=[.!?。\n]|$)'

    for match in re.finditer(pattern, text):
        speaker = match.group(1).strip()
        quote = match.group(2).strip()

        if not quote or len(quote) < 10:
            continue

        # 일반적인 레이블 제외 (시간, 숫자 등)
        if re.match(r'^\d', speaker) or speaker in ("참고", "주의", "예시", "출처"):
            continue

        sentiment = _analyze_sentiment(quote)
        credibility = _calculate_credibility(quote, speaker)

        cards.append(TestimonialCard(
            quote=quote,
            speaker=speaker,
            context=f"{speaker}의 발언",
            sentiment=sentiment,
            credibility_score=credibility,
        ))

    return cards


def _extract_opinion_sentences(text: str) -> List[TestimonialCard]:
    """의견/감상 표현이 담긴 문장을 추출합니다."""
    cards = []
    # 의견 표현 패턴
    opinion_patterns = [
        r'([^.!?\n]{10,200}(?:라고 생각|라고 느꼈|인 것 같|할 수 있|해야 한다|추천합니다|강추)[^.!?\n]{0,50})',
        r'([^.!?\n]{10,200}(?:정말|진짜|확실히|분명히)\s+[^.!?\n]{5,100})',
    ]

    for pattern in opinion_patterns:
        for match in re.finditer(pattern, text):
            quote = match.group(1).strip()
            if not quote or len(quote) < 15:
                continue

            sentiment = _analyze_sentiment(quote)
            credibility = _calculate_credibility(quote, "")

            cards.append(TestimonialCard(
                quote=quote[:200],
                speaker="화자",
                context="의견/감상 발언",
                sentiment=sentiment,
                credibility_score=credibility,
            ))

    return cards


def _extract_speaker_from_context(context: str) -> str:
    """인용 앞 맥락에서 발화자 이름을 추출합니다."""
    if not context:
        return "화자"

    # 'OOO가', 'OOO은', 'OOO는', 'OOO이' 패턴
    match = re.search(r'([가-힣A-Za-z]{2,10})(?:가|은|는|이|씨|님|대표|교수|선생)', context)
    if match:
        return match.group(1)

    return "화자"


def _analyze_sentiment(text: str) -> str:
    """텍스트의 감성을 분석합니다."""
    lower = text.lower()

    pos_count = sum(1 for w in _SENTIMENT_KEYWORDS["positive"] if w in lower)
    neg_count = sum(1 for w in _SENTIMENT_KEYWORDS["negative"] if w in lower)

    if pos_count > neg_count:
        return "positive"
    elif neg_count > pos_count:
        return "negative"
    return "neutral"


def _calculate_credibility(quote: str, speaker: str) -> float:
    """인용의 신뢰도 점수를 계산합니다 (0.0~1.0)."""
    score = 0.3  # 기본 점수

    lower = quote.lower()

    # 신뢰도 부스터 키워드
    booster_hits = sum(1 for w in _CREDIBILITY_BOOSTERS if w in lower)
    score += min(booster_hits * 0.1, 0.3)

    # 구체적 숫자/데이터 포함
    if re.search(r'\d+[%년개월일회]', quote):
        score += 0.15

    # 발화자가 있으면 가산
    if speaker and speaker != "화자":
        score += 0.1

    # 인용 길이 적정성 (30~150자가 최적)
    length = len(quote)
    if 30 <= length <= 150:
        score += 0.1
    elif length < 30 or length > 200:
        score -= 0.05

    return max(0.0, min(1.0, round(score, 2)))


def _deduplicate_cards(cards: List[TestimonialCard]) -> List[TestimonialCard]:
    """동일하거나 매우 유사한 인용을 중복 제거합니다."""
    if not cards:
        return []

    seen_quotes = set()
    unique = []

    for card in cards:
        # 정규화된 인용문으로 중복 체크
        normalized = re.sub(r'\s+', ' ', card.quote.strip().lower())
        if normalized not in seen_quotes:
            seen_quotes.add(normalized)
            unique.append(card)

    return unique


def testimonial_cards_to_dicts(cards: List[TestimonialCard]) -> List[dict]:
    """TestimonialCard 리스트를 직렬화 가능한 dict 리스트로 변환합니다."""
    return [asdict(c) for c in cards]
