"""
RSS/Atom 피드 파싱 서비스

feedparser 라이브러리를 사용하여 RSS/Atom 피드를 파싱합니다.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

import feedparser
from bs4 import BeautifulSoup
import logging

from utils.url_safety import fetch_public_url

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 15
_REQUEST_HEADERS = {
    "User-Agent": "InsightEngine/1.0",
    "Accept": "application/rss+xml,application/atom+xml,application/xml,text/xml,*/*;q=0.8",
}


def _clean_html(raw: str) -> str:
    """HTML 태그를 제거하고 순수 텍스트를 반환합니다."""
    if not raw:
        return ""
    text = BeautifulSoup(raw, "html.parser").get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _entry_to_dict(entry) -> Dict:
    """feedparser 엔트리 객체를 딕셔너리로 변환합니다."""
    # 본문 우선순위: content > summary
    content_raw = ""
    if hasattr(entry, "content") and entry.content:
        content_raw = entry.content[0].get("value", "")
    if not content_raw and hasattr(entry, "summary"):
        content_raw = entry.summary or ""

    content = _clean_html(content_raw)

    # 발행일 추출
    published = ""
    if hasattr(entry, "published"):
        published = entry.published or ""
    elif hasattr(entry, "updated"):
        published = entry.updated or ""

    return {
        "title": (entry.get("title") or "").strip(),
        "content": content,
        "url": entry.get("link") or "",
        "published": published,
        "source_type": "rss",
    }


def _parse_published_dt(published_str: str) -> Optional[datetime]:
    """published 문자열을 datetime으로 변환합니다. 실패 시 None 반환."""
    if not published_str:
        return None
    try:
        # feedparser가 time.struct_time을 파싱하므로 직접 문자열 파싱
        import email.utils
        parsed_tuple = email.utils.parsedate_to_datetime(published_str)
        return parsed_tuple
    except Exception:
        pass

    # ISO 8601 형식 시도
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(published_str[:19], fmt[:len(fmt)])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def parse_feed(url: str, max_items: int = 10) -> List[Dict]:
    """RSS/Atom 피드를 파싱하여 엔트리 목록을 반환합니다.

    Args:
        url: RSS/Atom 피드 URL
        max_items: 최대 항목 수 (기본 10)

    Returns:
        엔트리 딕셔너리 목록:
        [{"title": str, "content": str, "url": str, "published": str, "source_type": "rss"}]

    Raises:
        ValueError: 유효하지 않은 피드이거나 파싱 실패
    """
    try:
        feed = _parse_feed_document(url)

        # bozo == True 이면 파싱 오류 (단, 일부 피드는 bozo여도 파싱 가능)
        if feed.bozo and not feed.entries:
            raise ValueError(f"RSS 피드 파싱 실패: {feed.bozo_exception}")

        entries = feed.entries[:max_items]
        return [_entry_to_dict(e) for e in entries]
    except ValueError:
        raise
    except Exception as e:
        logger.error("parse_feed 실패: %s", e, exc_info=True)
        return []


def _fetch_feed_content(url: str) -> bytes:
    response = fetch_public_url(
        url,
        headers=_REQUEST_HEADERS,
        timeout=_REQUEST_TIMEOUT,
        label="RSS 피드 URL",
    )
    return response.content or b""


def _parse_feed_document(url: str):
    """Fetch a feed without redirects, then parse local bytes only."""
    return feedparser.parse(_fetch_feed_content(url))


def get_feed_title(url: str) -> str:
    """Return the feed title using the same safe fetch path as parse_feed."""
    feed = _parse_feed_document(url)
    return getattr(feed.feed, "title", "") or url


def get_latest_entries(url: str, since_days: int = 7) -> List[Dict]:
    """최근 N일 이내에 발행된 RSS 엔트리만 반환합니다.

    Args:
        url: RSS/Atom 피드 URL
        since_days: 최근 며칠치를 가져올지 (기본 7일)

    Returns:
        최근 엔트리 딕셔너리 목록
    """
    try:
        all_entries = parse_feed(url, max_items=50)

        cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
        recent = []
        for entry in all_entries:
            dt = _parse_published_dt(entry.get("published", ""))
            if dt is None:
                # 날짜 파싱 불가 → 포함
                recent.append(entry)
            elif dt >= cutoff:
                recent.append(entry)

        return recent
    except Exception as e:
        logger.error("get_latest_entries 실패: %s", e, exc_info=True)
        return []
