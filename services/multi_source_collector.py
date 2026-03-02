"""
통합 콘텐츠 수집기

URL 타입을 자동 감지하고 각 서비스에 위임하여 콘텐츠를 수집합니다.
지원 소스: youtube, webpage, rss, arxiv
"""
from __future__ import annotations

import re
from typing import Dict, Optional

# 지원하는 소스 타입
SOURCE_YOUTUBE = "youtube"
SOURCE_WEBPAGE = "webpage"
SOURCE_RSS = "rss"
SOURCE_ARXIV = "arxiv"

# arXiv URL 패턴
_ARXIV_URL_RE = re.compile(
    r"(arxiv\.org/(abs|pdf|html)/|ar5iv\.org/abs/)",
    re.IGNORECASE,
)
_ARXIV_ID_RE = re.compile(
    r"^\d{4}\.\d{4,5}(v\d+)?$|^[a-z\-]+(\.[A-Z]{2})?/\d{7}$",
    re.IGNORECASE,
)

# RSS 피드 URL 패턴
_RSS_INDICATORS = [
    r"/feed/?$",
    r"/rss/?$",
    r"/atom/?$",
    r"\.rss$",
    r"\.atom$",
    r"\.xml$",
    r"/feed\.xml$",
    r"type=rss",
    r"format=rss",
    r"feed=rss",
]
_RSS_RE = re.compile("|".join(_RSS_INDICATORS), re.IGNORECASE)

# YouTube URL 패턴
_YOUTUBE_DOMAINS = {"youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"}


def detect_source_type(url: str) -> str:
    """URL을 분석하여 소스 타입을 자동으로 감지합니다.

    Args:
        url: 감지할 URL 문자열

    Returns:
        소스 타입 문자열: "youtube" | "arxiv" | "rss" | "webpage"
    """
    url_stripped = url.strip()

    # 1. YouTube 체크
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url_stripped)
        domain = parsed.netloc.lower().lstrip("www.")
        # www. 제거 후 비교
        netloc_clean = parsed.netloc.lower()
        if netloc_clean in _YOUTUBE_DOMAINS or netloc_clean.replace("www.", "") == "youtube.com":
            return SOURCE_YOUTUBE
        if "youtu.be" in netloc_clean:
            return SOURCE_YOUTUBE
    except Exception:
        pass

    # 2. arXiv 체크
    if _ARXIV_URL_RE.search(url_stripped):
        return SOURCE_ARXIV

    # 순수 arXiv ID 입력 (예: '2303.08774')
    bare = url_stripped.strip("/")
    if _ARXIV_ID_RE.match(bare):
        return SOURCE_ARXIV

    # 3. RSS 피드 체크 (URL 패턴 기반)
    if _RSS_RE.search(url_stripped):
        return SOURCE_RSS

    # 4. 기본: 웹페이지
    return SOURCE_WEBPAGE


def collect_content(url: str, source_type: Optional[str] = None) -> Dict:
    """URL에서 콘텐츠를 수집합니다.

    Args:
        url: 콘텐츠 소스 URL
        source_type: 명시적 소스 타입 (None이면 자동 감지)
            "youtube" | "webpage" | "rss" | "arxiv"

    Returns:
        수집된 콘텐츠 딕셔너리:
        {
            "title": str,
            "content": str,
            "url": str,
            "source_type": str,
            ... (소스별 추가 필드)
        }

    Raises:
        ValueError: 지원하지 않는 소스 타입이거나 수집 실패
        requests.RequestException: 네트워크 오류
    """
    if not url or not url.strip():
        raise ValueError("URL이 필요합니다.")

    url = url.strip()
    stype = source_type or detect_source_type(url)

    if stype == SOURCE_YOUTUBE:
        return _collect_youtube(url)
    elif stype == SOURCE_ARXIV:
        return _collect_arxiv(url)
    elif stype == SOURCE_RSS:
        return _collect_rss(url)
    elif stype == SOURCE_WEBPAGE:
        return _collect_webpage(url)
    else:
        raise ValueError(f"지원하지 않는 소스 타입: {stype}")


def _collect_youtube(url: str) -> Dict:
    """YouTube 콘텐츠 수집 — 기존 content_service에 위임."""
    from services import content_service

    video_id = content_service.get_video_id(url)
    if not video_id:
        raise ValueError(f"유효하지 않은 YouTube URL: {url}")

    transcript_result = content_service.get_transcript(video_id)
    if isinstance(transcript_result, dict) and transcript_result.get("error"):
        raise ValueError(transcript_result["error"])

    transcript_text = transcript_result.get("text", "") if isinstance(transcript_result, dict) else str(transcript_result)
    transcript_source = transcript_result.get("source", "unknown") if isinstance(transcript_result, dict) else "unknown"
    title = content_service.get_content_title(url) or "YouTube 영상"

    return {
        "title": title,
        "content": transcript_text,
        "url": url,
        "source_type": SOURCE_YOUTUBE,
        "video_id": video_id,
        "transcript_source": transcript_source,
    }


def _collect_arxiv(url: str) -> Dict:
    """arXiv 논문 수집."""
    from services.arxiv_service import fetch_paper

    # 순수 arXiv ID인 경우 URL 형식으로 변환
    bare = url.strip("/")
    if _ARXIV_ID_RE.match(bare):
        arxiv_id = bare
    else:
        # URL에서 ID 추출
        arxiv_id = re.sub(r".*arxiv\.org/(abs|pdf|html)/", "", url).strip().rstrip("/")

    return fetch_paper(arxiv_id)


def _collect_rss(url: str) -> Dict:
    """RSS 피드 첫 번째 엔트리 수집 (단일 URL 처리용)."""
    from services.rss_service import parse_feed

    entries = parse_feed(url, max_items=1)
    if not entries:
        raise ValueError(f"RSS 피드에서 엔트리를 찾을 수 없습니다: {url}")

    entry = entries[0]
    # 단일 생성 흐름에서는 가장 최신 항목 1개를 사용
    return entry


def _collect_webpage(url: str) -> Dict:
    """웹페이지 본문 수집."""
    from services.web_scraper_service import scrape_webpage

    return scrape_webpage(url)
