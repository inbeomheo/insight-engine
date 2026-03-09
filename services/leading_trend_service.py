"""
선행 트렌드 감지 서비스

다양한 신호(검색량, 언급, 참여도 등)를 분석하여
초기 단계의 선행 트렌드를 식별하고 성장률/카테고리를 분류합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class LeadingTrend:
    """감지된 선행 트렌드"""
    trend_name: str
    signal_strength: float  # 0~100
    first_detected: str  # ISO 날짜 문자열
    growth_rate: float  # 성장률 (%)
    category: str
    recommended_content: str


# ── 카테고리 키워드 매핑 ──
_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "technology": [
        "ai", "ml", "api", "cloud", "saas", "devops", "blockchain",
        "인공지능", "머신러닝", "클라우드", "블록체인", "프로그래밍",
    ],
    "business": [
        "startup", "funding", "revenue", "market", "growth",
        "스타트업", "투자", "매출", "시장", "성장", "비즈니스",
    ],
    "lifestyle": [
        "health", "wellness", "fitness", "diet", "travel",
        "건강", "웰빙", "피트니스", "여행", "다이어트",
    ],
    "entertainment": [
        "game", "movie", "music", "streaming", "content",
        "게임", "영화", "음악", "스트리밍", "콘텐츠",
    ],
    "education": [
        "course", "tutorial", "learning", "certification", "study",
        "강의", "튜토리얼", "학습", "자격증", "교육",
    ],
    "finance": [
        "crypto", "stock", "invest", "fintech", "defi",
        "암호화폐", "주식", "투자", "핀테크",
    ],
}

# ── 콘텐츠 추천 템플릿 ──
_CONTENT_TEMPLATES: Dict[str, str] = {
    "technology": "기술 트렌드 분석 및 실전 적용 가이드",
    "business": "비즈니스 동향 리포트 및 사례 분석",
    "lifestyle": "라이프스타일 트렌드 가이드 및 실천 팁",
    "entertainment": "엔터테인먼트 트렌드 리뷰 및 큐레이션",
    "education": "교육/학습 트렌드 정리 및 추천 리소스",
    "finance": "금융/투자 트렌드 분석 및 인사이트",
}


def _classify_category(trend_name: str, metadata: dict) -> str:
    """트렌드 이름과 메타데이터로 카테고리를 분류합니다."""
    # 메타데이터에 명시적 카테고리가 있으면 사용
    if "category" in metadata and metadata["category"]:
        return str(metadata["category"])

    combined = (trend_name + " " + metadata.get("description", "")).lower()
    best_category = "general"
    best_score = 0

    for category, keywords in _CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score > best_score:
            best_score = score
            best_category = category

    return best_category


def _calculate_signal_strength(signal: dict) -> float:
    """신호 데이터에서 종합 신호 강도를 계산합니다 (0~100)."""
    # 직접 지정된 signal_strength 우선
    if "signal_strength" in signal:
        return max(0.0, min(100.0, float(signal["signal_strength"])))

    components = []

    # 검색량 증가율
    search_growth = signal.get("search_growth", 0)
    if search_growth > 0:
        components.append(min(search_growth * 2, 100))

    # 언급 빈도
    mentions = signal.get("mentions", 0)
    if mentions > 0:
        components.append(min(mentions / 10, 100))

    # 참여도
    engagement = signal.get("engagement", 0)
    if engagement > 0:
        components.append(min(float(engagement), 100))

    # 소셜 버즈
    social_buzz = signal.get("social_buzz", 0)
    if social_buzz > 0:
        components.append(min(social_buzz * 5, 100))

    # 뉴스 카버리지
    news_coverage = signal.get("news_coverage", 0)
    if news_coverage > 0:
        components.append(min(news_coverage * 10, 100))

    if not components:
        return 0.0
    return round(sum(components) / len(components), 1)


def _calculate_growth_rate(signal: dict) -> float:
    """신호 데이터에서 성장률을 계산합니다."""
    # 직접 지정된 growth_rate 우선
    if "growth_rate" in signal:
        return round(float(signal["growth_rate"]), 1)

    # 이전/현재 값이 있으면 성장률 계산
    previous = signal.get("previous_value", 0)
    current = signal.get("current_value", 0)
    if previous > 0:
        return round(((current - previous) / previous) * 100, 1)

    # search_growth 폴백
    return round(float(signal.get("search_growth", 0)), 1)


def _get_first_detected(signal: dict) -> str:
    """최초 감지 날짜를 추출합니다."""
    for key in ("first_detected", "detected_at", "date", "timestamp"):
        val = signal.get(key, "")
        if val:
            return str(val)
    return "unknown"


def _recommend_content(category: str, signal_strength: float) -> str:
    """카테고리와 신호 강도에 따른 콘텐츠를 추천합니다."""
    base = _CONTENT_TEMPLATES.get(category, "트렌드 분석 콘텐츠")
    if signal_strength >= 70:
        return f"[긴급] {base} — 즉시 발행 권장"
    if signal_strength >= 40:
        return f"{base} — 조기 진입 기회"
    return f"{base} — 모니터링 후 발행 계획"


def detect_leading_trends(signals: list) -> List[LeadingTrend]:
    """신호 데이터를 분석하여 선행 트렌드를 감지합니다.

    Args:
        signals: 신호 데이터 리스트. 각 항목은 최소 {"name": str} 포함.
            선택: search_growth, mentions, engagement, social_buzz,
                  news_coverage, signal_strength, growth_rate,
                  first_detected, category, description

    Returns:
        LeadingTrend 리스트 (신호 강도 내림차순)
    """
    if not signals:
        return []

    trends: List[LeadingTrend] = []

    for signal in signals:
        name = signal.get("name", "").strip()
        if not name:
            continue

        strength = _calculate_signal_strength(signal)

        # 신호 강도 0이면 트렌드로 간주하지 않음
        if strength <= 0:
            continue

        growth = _calculate_growth_rate(signal)
        first_detected = _get_first_detected(signal)
        category = _classify_category(name, signal)
        content_rec = _recommend_content(category, strength)

        trends.append(LeadingTrend(
            trend_name=name,
            signal_strength=strength,
            first_detected=first_detected,
            growth_rate=growth,
            category=category,
            recommended_content=content_rec,
        ))

    # 신호 강도 내림차순 정렬
    trends.sort(key=lambda t: t.signal_strength, reverse=True)
    return trends
