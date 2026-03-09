"""
경쟁 역공학 서비스 — 경쟁 채널의 콘텐츠 전략을 분석하여 전략 템플릿 생성
"""

from dataclasses import dataclass, field
from collections import Counter
import re


@dataclass
class StrategyTemplate:
    """경쟁 채널 전략 역공학 결과"""
    competitor: str
    posting_frequency: str  # "daily" | "weekly" | "biweekly" | "monthly" | "irregular"
    content_types: list[str] = field(default_factory=list)
    top_topics: list[str] = field(default_factory=list)
    engagement_patterns: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


# 포스팅 빈도 판단 기준 (일 단위)
_FREQUENCY_THRESHOLDS = [
    (1.5, "daily"),
    (4, "weekly"),      # 주 2회 이상
    (10, "biweekly"),   # 격주 1회 이상
    (35, "monthly"),
]


def _classify_posting_frequency(avg_interval_days: float) -> str:
    """평균 포스팅 간격(일)으로 빈도 분류"""
    for threshold, label in _FREQUENCY_THRESHOLDS:
        if avg_interval_days <= threshold:
            return label
    return "irregular"


def _extract_content_types(posts: list[dict]) -> list[str]:
    """게시물 텍스트에서 콘텐츠 유형 추론"""
    type_keywords = {
        "tutorial": ["방법", "하는 법", "tutorial", "how to", "가이드"],
        "review": ["리뷰", "review", "후기", "비교"],
        "news": ["뉴스", "소식", "발표", "출시"],
        "listicle": ["추천", "top", "best", "선정"],
        "opinion": ["생각", "의견", "opinion", "칼럼"],
        "vlog": ["일상", "vlog", "브이로그", "하루"],
    }
    found = set()
    for post in posts:
        text = post.get("text", "").lower()
        for ctype, keywords in type_keywords.items():
            if any(kw in text for kw in keywords):
                found.add(ctype)
    return sorted(found) if found else ["general"]


def _extract_top_topics(posts: list[dict], top_n: int = 5) -> list[str]:
    """게시물에서 반복 등장하는 핵심 토픽 추출 (단어 빈도 기반)"""
    # 불용어
    stopwords = {"the", "a", "an", "is", "are", "was", "were", "and", "or",
                 "을", "를", "이", "가", "에", "의", "로", "은", "는", "도",
                 "한", "하는", "에서", "으로", "와", "과", "입니다", "합니다"}
    word_counter: Counter = Counter()
    for post in posts:
        text = post.get("text", "")
        # 2글자 이상 단어만 추출
        words = re.findall(r'[가-힣a-zA-Z]{2,}', text.lower())
        words = [w for w in words if w not in stopwords]
        word_counter.update(words)
    return [word for word, _ in word_counter.most_common(top_n)]


def _analyze_engagement_patterns(posts: list[dict]) -> list[str]:
    """인게이지먼트 패턴 분석"""
    if not posts:
        return ["데이터 부족"]

    engagements = [p.get("engagement", 0) for p in posts]
    avg_eng = sum(engagements) / len(engagements) if engagements else 0
    max_eng = max(engagements) if engagements else 0
    min_eng = min(engagements) if engagements else 0

    patterns = []

    # 평균 인게이지먼트 수준
    if avg_eng >= 10000:
        patterns.append("높은 평균 인게이지먼트 (10K+)")
    elif avg_eng >= 1000:
        patterns.append("중간 평균 인게이지먼트 (1K~10K)")
    else:
        patterns.append(f"낮은 평균 인게이지먼트 ({avg_eng:.0f})")

    # 변동성 분석
    if max_eng > 0 and min_eng >= 0:
        ratio = max_eng / max(min_eng, 1)
        if ratio > 10:
            patterns.append("인게이지먼트 변동성 높음 (바이럴 콘텐츠 존재)")
        elif ratio > 3:
            patterns.append("인게이지먼트 변동성 중간")
        else:
            patterns.append("인게이지먼트 안정적")

    # 고성과 콘텐츠 비율
    high_performers = sum(1 for e in engagements if e > avg_eng * 2)
    if len(posts) > 0:
        hp_ratio = high_performers / len(posts)
        if hp_ratio > 0.2:
            patterns.append(f"고성과 콘텐츠 비율 {hp_ratio:.0%}")

    return patterns


def _generate_recommendations(
    frequency: str,
    content_types: list[str],
    top_topics: list[str],
    engagement_patterns: list[str],
) -> list[str]:
    """분석 결과 기반 전략 추천"""
    recs = []

    # 빈도 기반 추천
    freq_recs = {
        "daily": "경쟁사가 일일 발행 중 — 주 3회 이상 발행으로 가시성 확보 권장",
        "weekly": "경쟁사가 주간 발행 중 — 동일 빈도 유지하며 품질 차별화 권장",
        "biweekly": "경쟁사 발행 빈도 낮음 — 주 1회 이상 발행으로 시장 점유 기회",
        "monthly": "경쟁사 발행 매우 드묾 — 일관된 발행으로 쉽게 추월 가능",
        "irregular": "경쟁사 발행 불규칙 — 일관된 스케줄이 핵심 경쟁력",
    }
    recs.append(freq_recs.get(frequency, "발행 빈도 모니터링 필요"))

    # 콘텐츠 유형 기반 추천
    if "tutorial" in content_types:
        recs.append("튜토리얼 콘텐츠 경쟁 — 더 심화된 가이드로 차별화")
    if "review" in content_types:
        recs.append("리뷰 콘텐츠 경쟁 — 독자적 벤치마크/비교 분석 추가")
    if len(content_types) <= 2:
        recs.append("경쟁사 콘텐츠 유형 제한적 — 다양한 포맷으로 틈새 공략")

    # 토픽 기반 추천
    if top_topics:
        recs.append(f"핵심 경쟁 토픽: {', '.join(top_topics[:3])} — 관련 키워드 선점 권장")

    return recs


def reverse_engineer(competitor_channel: dict) -> StrategyTemplate:
    """
    경쟁 채널 전략 역공학.

    Args:
        competitor_channel: {"name": "채널명", "posts": [{"text": "...", "engagement": N}]}

    Returns:
        StrategyTemplate: 경쟁 전략 분석 결과
    """
    name = competitor_channel.get("name", "Unknown")
    posts = competitor_channel.get("posts", [])

    if not posts:
        return StrategyTemplate(
            competitor=name,
            posting_frequency="unknown",
            content_types=[],
            top_topics=[],
            engagement_patterns=["데이터 부족"],
            recommendations=["포스트 데이터 수집 필요"],
        )

    # 포스팅 간격 계산 (타임스탬프가 있는 경우)
    timestamps = sorted(
        [p["timestamp"] for p in posts if "timestamp" in p]
    )
    if len(timestamps) >= 2:
        # 초 단위 → 일 단위
        intervals = [
            (timestamps[i + 1] - timestamps[i]) / 86400
            for i in range(len(timestamps) - 1)
            if isinstance(timestamps[i], (int, float))
        ]
        avg_interval = sum(intervals) / len(intervals) if intervals else 30
    else:
        # 타임스탬프 없으면 포스트 수로 추정 (30일 기준)
        avg_interval = 30 / max(len(posts), 1)

    frequency = _classify_posting_frequency(avg_interval)
    content_types = _extract_content_types(posts)
    top_topics = _extract_top_topics(posts)
    engagement_patterns = _analyze_engagement_patterns(posts)
    recommendations = _generate_recommendations(
        frequency, content_types, top_topics, engagement_patterns
    )

    return StrategyTemplate(
        competitor=name,
        posting_frequency=frequency,
        content_types=content_types,
        top_topics=top_topics,
        engagement_patterns=engagement_patterns,
        recommendations=recommendations,
    )
