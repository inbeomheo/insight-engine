"""
소스 추천 서비스

주제 키워드를 기반으로 관련 YouTube 영상과 웹 자료를 검색하여
콘텐츠 생성에 적합한 소스를 추천합니다.
"""
import logging
import os
from typing import Dict, List

logger = logging.getLogger(__name__)

_MAX_RESULTS = 5


def recommend_sources(topic: str) -> List[Dict]:
    """주제에 맞는 소스를 추천합니다.

    YouTube 검색 + 웹 검색으로 관련 소스를 수집합니다.

    Args:
        topic: 주제 키워드 (예: "파이썬 웹 개발")

    Returns:
        [{"url": str, "title": str, "source_type": str, "relevance_score": float}]
        relevance_score는 0.0~1.0 (검색 순위 기반)

    Raises:
        ValueError: topic이 비어있는 경우
    """
    if not topic or not topic.strip():
        raise ValueError("검색 주제를 입력해주세요.")

    topic = topic.strip()
    results = []

    # 1. YouTube 검색
    youtube_results = _search_youtube(topic)
    results.extend(youtube_results)

    # 2. 웹 검색 (DuckDuckGo)
    web_results = _search_web(topic)
    results.extend(web_results)

    # 관련도 순 정렬
    results.sort(key=lambda x: x["relevance_score"], reverse=True)

    return results[:_MAX_RESULTS * 2]  # YouTube + 웹 합산


def _search_youtube(topic: str) -> List[Dict]:
    """YouTube Data API로 관련 영상을 검색합니다."""
    api_key = os.getenv("YOUTUBE_API_KEY", "")
    if not api_key:
        logger.info("YOUTUBE_API_KEY 미설정 — YouTube 검색 건너뜀")
        return []

    try:
        from googleapiclient.discovery import build

        youtube = build("youtube", "v3", developerKey=api_key)
        request = youtube.search().list(
            q=topic,
            part="snippet",
            type="video",
            maxResults=_MAX_RESULTS,
            order="relevance",
        )
        response = request.execute()

        results = []
        items = response.get("items", [])
        for i, item in enumerate(items):
            video_id = item["id"]["videoId"]
            snippet = item["snippet"]
            score = 1.0 - (i * 0.15)  # 순위 기반 점수 (1.0 → 0.4)

            results.append({
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "title": snippet.get("title", ""),
                "source_type": "youtube",
                "relevance_score": round(max(score, 0.1), 2),
            })

        return results
    except Exception as e:
        logger.warning("YouTube 검색 실패: %s", e)
        return []


def _search_web(topic: str) -> List[Dict]:
    """DuckDuckGo로 관련 웹 자료를 검색합니다."""
    try:
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            search_results = list(ddgs.text(topic, max_results=_MAX_RESULTS))

        for i, item in enumerate(search_results):
            score = 0.9 - (i * 0.15)  # 웹은 YouTube보다 약간 낮은 기본 점수

            results.append({
                "url": item.get("href", ""),
                "title": item.get("title", ""),
                "source_type": "webpage",
                "relevance_score": round(max(score, 0.1), 2),
            })

        return results
    except Exception as e:
        logger.warning("웹 검색 실패: %s", e)
        return []
