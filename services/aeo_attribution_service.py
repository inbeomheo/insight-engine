"""AEO 귀속 분석 서비스 -- AI 유입/전환 귀속 분석"""
from dataclasses import dataclass, field
from typing import Optional


# AI 검색엔진 소스 식별용 키워드
_AI_SOURCES = {
    "chatgpt", "openai", "claude", "anthropic", "bard", "gemini",
    "copilot", "bing_chat", "perplexity", "you.com", "phind",
    "ai_search", "ai_overview",
}

_ORGANIC_SOURCES = {
    "google", "naver", "daum", "bing", "yahoo", "duckduckgo",
    "baidu", "yandex",
}


@dataclass
class AttributionReport:
    """AI 유입/전환 귀속 리포트"""
    total_visits: int = 0
    ai_attributed: int = 0
    organic: int = 0
    direct: int = 0
    channels: dict = field(default_factory=dict)
    conversion_rate: float = 0.0


def _classify_source(source: str) -> str:
    """트래픽 소스를 ai / organic / direct 로 분류한다."""
    normalized = source.strip().lower().replace(" ", "_").replace("-", "_")
    if normalized in _AI_SOURCES or any(ai in normalized for ai in _AI_SOURCES):
        return "ai"
    if normalized in _ORGANIC_SOURCES or any(org in normalized for org in _ORGANIC_SOURCES):
        return "organic"
    if normalized in ("direct", "none", "bookmark", "(direct)", ""):
        return "direct"
    # 분류 불가한 소스는 referral 로 처리하되 organic 에 합산
    return "organic"


def attribute_ai_funnel(
    traffic_data: list[dict],
) -> AttributionReport:
    """트래픽 데이터로부터 AI 유입/전환 귀속 리포트를 생성한다.

    Args:
        traffic_data: [{"source": "chatgpt", "visits": 100, "conversions": 5}, ...]

    Returns:
        AttributionReport
    """
    report = AttributionReport()
    channels: dict[str, dict] = {}
    total_conversions = 0

    for entry in traffic_data:
        source = str(entry.get("source", "direct"))
        visits = int(entry.get("visits", 0))
        conversions = int(entry.get("conversions", 0))

        if visits < 0:
            visits = 0
        if conversions < 0:
            conversions = 0

        channel = _classify_source(source)
        report.total_visits += visits
        total_conversions += conversions

        if channel == "ai":
            report.ai_attributed += visits
        elif channel == "organic":
            report.organic += visits
        else:
            report.direct += visits

        # 채널별 집계
        if channel not in channels:
            channels[channel] = {"visits": 0, "conversions": 0, "sources": []}
        channels[channel]["visits"] += visits
        channels[channel]["conversions"] += conversions
        if source not in channels[channel]["sources"]:
            channels[channel]["sources"].append(source)

    report.channels = channels

    if report.total_visits > 0:
        report.conversion_rate = round(total_conversions / report.total_visits, 4)

    return report
