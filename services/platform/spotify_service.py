"""Spotify 에피소드 메타데이터 추출 서비스

Spotify oEmbed API를 사용하여 에피소드 정보를 가져옵니다.
오디오 URL 직접 접근은 Spotify 정책상 불가 — 설명(description)으로 콘텐츠 생성.
"""
from __future__ import annotations

import logging
import re
from typing import Dict, Optional

import requests

logger = logging.getLogger(__name__)

# Spotify 에피소드 URL 패턴
SPOTIFY_EPISODE_RE = re.compile(
    r"open\.spotify\.com/episode/([A-Za-z0-9]+)", re.IGNORECASE
)

OEMBED_URL = "https://open.spotify.com/oembed"
TIMEOUT = (5, 10)


def is_spotify_episode_url(url: str) -> bool:
    """URL이 Spotify 에피소드 URL인지 확인합니다."""
    return bool(SPOTIFY_EPISODE_RE.search(url))


def get_episode_id(url: str) -> Optional[str]:
    """URL에서 Spotify 에피소드 ID를 추출합니다."""
    m = SPOTIFY_EPISODE_RE.search(url)
    return m.group(1) if m else None


def get_episode_info(url: str) -> Dict:
    """Spotify 에피소드 메타데이터를 추출합니다.

    oEmbed API로 제목/설명을 가져옵니다.
    Spotify는 오디오 직접 다운로드를 지원하지 않으므로
    설명 텍스트를 콘텐츠 소스로 사용합니다.

    Args:
        url: Spotify 에피소드 URL

    Returns:
        {
            "title": str,
            "description": str,
            "thumbnail_url": str | None,
            "provider": "spotify",
        }

    Raises:
        ValueError: 유효하지 않은 URL 또는 메타데이터 추출 실패
    """
    if not is_spotify_episode_url(url):
        raise ValueError(f"유효하지 않은 Spotify 에피소드 URL: {url}")

    try:
        resp = requests.get(
            OEMBED_URL,
            params={"url": url, "format": "json"},
            timeout=TIMEOUT,
            allow_redirects=False,
        )
        if 300 <= resp.status_code < 400:
            raise ValueError(f"Spotify oEmbed 리다이렉트 차단: {resp.status_code}")
        resp.raise_for_status()
        data = resp.json()

        title = data.get("title", "Spotify 에피소드")
        # oEmbed의 description은 제목에 포함된 경우가 많으므로 html에서 추출
        description = data.get("description", "")
        thumbnail = data.get("thumbnail_url")

        return {
            "title": title,
            "description": description,
            "thumbnail_url": thumbnail,
            "provider": "spotify",
        }

    except requests.exceptions.RequestException as e:
        logger.error("Spotify oEmbed 요청 실패: %s", str(e))
        raise ValueError(f"Spotify 에피소드 정보를 가져올 수 없습니다: {str(e)}")
