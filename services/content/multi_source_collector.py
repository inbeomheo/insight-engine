"""
통합 콘텐츠 수집기

URL 타입을 자동 감지하고 각 서비스에 위임하여 콘텐츠를 수집합니다.
지원 소스: youtube, webpage, rss, arxiv, twitter, reddit, github, hackernews, podcast
"""
from __future__ import annotations

import logging

import re
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# 지원하는 소스 타입
SOURCE_YOUTUBE = "youtube"
SOURCE_WEBPAGE = "webpage"
SOURCE_RSS = "rss"
SOURCE_ARXIV = "arxiv"
SOURCE_TWITTER = "twitter"
SOURCE_REDDIT = "reddit"
SOURCE_GITHUB = "github"
SOURCE_HACKERNEWS = "hackernews"
SOURCE_PODCAST = "podcast"
SOURCE_STACKOVERFLOW = "stackoverflow"

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

# Twitter/X URL 패턴
_TWITTER_DOMAINS = {"twitter.com", "www.twitter.com", "x.com", "www.x.com"}

# Reddit URL 패턴
_REDDIT_RE = re.compile(r"reddit\.com/r/\w+/comments/", re.IGNORECASE)

# GitHub URL 패턴
_GITHUB_REPO_RE = re.compile(
    r"github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?$", re.IGNORECASE
)

# Hacker News URL 패턴
_HN_RE = re.compile(r"news\.ycombinator\.com/item\?id=\d+", re.IGNORECASE)

# 팟캐스트 URL 패턴 (Spotify 에피소드, Apple Podcasts, 일반 오디오)
_PODCAST_DOMAINS = {
    "open.spotify.com",
    "podcasts.apple.com",
    "podcasts.google.com",
    "anchor.fm",
    "podbean.com",
    "soundcloud.com",
}
_SPOTIFY_EPISODE_RE = re.compile(r"open\.spotify\.com/episode/", re.IGNORECASE)
_APPLE_PODCAST_RE = re.compile(r"podcasts\.apple\.com/.+/podcast/", re.IGNORECASE)
_AUDIO_EXT_RE = re.compile(r"\.(mp3|m4a|ogg|wav|flac|aac)(\?|$)", re.IGNORECASE)

# Stack Overflow URL 패턴
_SO_RE = re.compile(r"stackoverflow\.com/questions/\d+", re.IGNORECASE)


def detect_source_type(url: str) -> str:
    """URL을 분석하여 소스 타입을 자동으로 감지합니다.

    Args:
        url: 감지할 URL 문자열

    Returns:
        소스 타입 문자열: "youtube" | "arxiv" | "rss" | "webpage"
    """
    url_stripped = url.strip()

    # URL 파싱
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url_stripped)
        netloc_clean = parsed.netloc.lower()
    except Exception:
        netloc_clean = ""

    # 0. 팟캐스트 체크 (YouTube보다 먼저: Spotify/Apple은 명확)
    if _SPOTIFY_EPISODE_RE.search(url_stripped):
        return SOURCE_PODCAST
    if _APPLE_PODCAST_RE.search(url_stripped):
        return SOURCE_PODCAST
    if netloc_clean in _PODCAST_DOMAINS:
        return SOURCE_PODCAST
    if _AUDIO_EXT_RE.search(url_stripped):
        return SOURCE_PODCAST

    # 1. YouTube 체크
    if netloc_clean in _YOUTUBE_DOMAINS or netloc_clean.replace("www.", "") == "youtube.com":
        return SOURCE_YOUTUBE
    if "youtu.be" in netloc_clean:
        return SOURCE_YOUTUBE

    # 2. Twitter/X 체크
    if netloc_clean in _TWITTER_DOMAINS or netloc_clean.replace("www.", "") in {"twitter.com", "x.com"}:
        return SOURCE_TWITTER

    # 3. Reddit 체크
    if _REDDIT_RE.search(url_stripped):
        return SOURCE_REDDIT

    # 4. GitHub 체크 (리포지토리 루트 URL만)
    if _GITHUB_REPO_RE.search(url_stripped):
        return SOURCE_GITHUB

    # 5. Stack Overflow 체크
    if _SO_RE.search(url_stripped):
        return SOURCE_STACKOVERFLOW

    # 6. Hacker News 체크
    if _HN_RE.search(url_stripped):
        return SOURCE_HACKERNEWS

    # 6. arXiv 체크
    if _ARXIV_URL_RE.search(url_stripped):
        return SOURCE_ARXIV

    # 순수 arXiv ID 입력 (예: '2303.08774')
    bare = url_stripped.strip("/")
    if _ARXIV_ID_RE.match(bare):
        return SOURCE_ARXIV

    # 7. RSS 피드 체크 (URL 패턴 기반)
    if _RSS_RE.search(url_stripped):
        return SOURCE_RSS

    # 8. 기본: 웹페이지
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
    try:
        if not url or not url.strip():
            raise ValueError("URL이 필요합니다.")

        url = url.strip()
        stype = source_type or detect_source_type(url)

        _collectors = {
            SOURCE_YOUTUBE: _collect_youtube,
            SOURCE_ARXIV: _collect_arxiv,
            SOURCE_RSS: _collect_rss,
            SOURCE_WEBPAGE: _collect_webpage,
            SOURCE_TWITTER: _collect_twitter,
            SOURCE_REDDIT: _collect_reddit,
            SOURCE_GITHUB: _collect_github,
            SOURCE_HACKERNEWS: _collect_hackernews,
            SOURCE_STACKOVERFLOW: _collect_stackoverflow,
            SOURCE_PODCAST: _collect_podcast,
        }

        collector = _collectors.get(stype)
        if not collector:
            raise ValueError(f"지원하지 않는 소스 타입: {stype}")
        return collector(url)
    except Exception as e:
        logger.error(f"콘텐츠 수집 처리 실패: {e}")
        raise
def _collect_youtube(url: str) -> Dict:
    """YouTube 콘텐츠 수집 — 기존 content_service에 위임."""
    from services.core import content_service

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
    from services.data.arxiv_service import fetch_paper

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
    from services.platform.rss_service import parse_feed

    entries = parse_feed(url, max_items=1)
    if not entries:
        raise ValueError(f"RSS 피드에서 엔트리를 찾을 수 없습니다: {url}")

    entry = entries[0]
    # 단일 생성 흐름에서는 가장 최신 항목 1개를 사용
    return entry


def _collect_webpage(url: str) -> Dict:
    """웹페이지 본문 수집."""
    from services.data.web_scraper_service import scrape_webpage

    return scrape_webpage(url)


def _collect_twitter(url: str) -> Dict:
    """Twitter/X 스레드 수집."""
    from services.platform.social_scraper_service import scrape_twitter_thread

    return scrape_twitter_thread(url)


def _collect_reddit(url: str) -> Dict:
    """Reddit 포스트 수집."""
    from services.platform.social_scraper_service import scrape_reddit_post

    return scrape_reddit_post(url)


def _collect_github(url: str) -> Dict:
    """GitHub README 수집."""
    from services.platform.github_service import extract_github_readme

    return extract_github_readme(url)


def _collect_hackernews(url: str) -> Dict:
    """Hacker News 아이템 수집."""
    from services.platform.social_scraper_service import scrape_hackernews

    return scrape_hackernews(url)


def _collect_stackoverflow(url: str) -> Dict:
    """Stack Overflow 질문 수집."""
    from services.platform.social_scraper_service import scrape_stackoverflow

    return scrape_stackoverflow(url)


def _collect_podcast(url: str) -> Dict:
    """팟캐스트 콘텐츠 수집.

    Spotify 에피소드: oEmbed로 메타데이터 추출 → 설명 텍스트 사용.
    일반 오디오 URL: yt-dlp로 오디오 다운로드 → Whisper 전사.
    """
    import os

    # Spotify 에피소드
    from services.platform.spotify_service import is_spotify_episode_url
    if is_spotify_episode_url(url):
        from services.platform.spotify_service import get_episode_info
        info = get_episode_info(url)

        content = info.get("description", "")
        if not content or len(content.strip()) < 50:
            # 설명이 부족하면 Whisper 시도 (Spotify는 직접 다운로드 불가하므로 실패 가능)
            content = info.get("description", "")
            if not content.strip():
                raise ValueError(
                    "Spotify 에피소드 설명이 비어 있습니다. "
                    "오디오 직접 다운로드는 Spotify 정책상 지원되지 않습니다."
                )

        return {
            "title": info["title"],
            "content": content,
            "url": url,
            "source_type": SOURCE_PODCAST,
            "provider": "spotify",
        }

    # 일반 오디오 URL / Apple Podcasts 등: yt-dlp → Whisper
    whisper_enabled = os.getenv("WHISPER_ENABLED", "false").lower() == "true"
    if not whisper_enabled:
        raise ValueError(
            "팟캐스트 오디오 전사를 위해 WHISPER_ENABLED=true 설정이 필요합니다."
        )

    import shutil
    from services.transcript.whisper_service import download_audio, transcribe_audio

    audio_path = None
    try:
        audio_path = download_audio(url)
        if not audio_path:
            raise ValueError(f"팟캐스트 오디오 다운로드 실패: {url}")

        whisper_model = os.getenv("WHISPER_MODEL_SIZE", "base")
        text = transcribe_audio(audio_path, whisper_model)
        if not text or not text.strip():
            raise ValueError("팟캐스트 오디오 전사 결과가 비어 있습니다.")

        return {
            "title": f"팟캐스트: {url.split('/')[-1][:50]}",
            "content": text,
            "url": url,
            "source_type": SOURCE_PODCAST,
            "provider": "whisper",
        }
    finally:
        if audio_path:
            audio_dir = os.path.dirname(audio_path)
            if audio_dir and os.path.basename(audio_dir).startswith('ytdlp_audio_'):
                shutil.rmtree(audio_dir, ignore_errors=True)
            else:
                os.remove(audio_path) if os.path.exists(audio_path) else None
