"""
웹페이지 스크래핑 서비스

BeautifulSoup으로 웹페이지 본문 텍스트를 추출합니다.
- robots.txt 기본 준수 (크롤링 허용 여부 체크)
- User-Agent: InsightEngine/1.0
- 타임아웃: 10초
"""
from __future__ import annotations

import re
import urllib.robotparser
from typing import Dict
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

# 요청 헤더
_HEADERS = {
    "User-Agent": "InsightEngine/1.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko,en;q=0.9",
}

# 제거할 태그 목록 (본문과 무관한 요소)
_REMOVE_TAGS = [
    "script", "style", "noscript", "nav", "header", "footer",
    "aside", "form", "button", "select", "option", "svg",
    "figure", "iframe", "embed", "object",
]

# 본문 후보 태그 (우선순위 순)
_ARTICLE_SELECTORS = [
    "article",
    "[role='main']",
    "main",
    ".content",
    ".post-content",
    ".entry-content",
    ".article-body",
    "#content",
    "#main",
]

_REQUEST_TIMEOUT = 10  # 초


def _is_crawl_allowed(url: str) -> bool:
    """robots.txt를 확인해 크롤링 허용 여부를 반환합니다.

    요청 실패 시 허용으로 간주합니다 (비파괴적 기본값).
    """
    try:
        parsed = urlparse(url)
        robots_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch("InsightEngine/1.0", url)
    except Exception:
        return True  # 파싱 실패 시 허용으로 간주


def _extract_main_content(soup: BeautifulSoup) -> str:
    """HTML에서 본문 텍스트를 추출합니다."""
    # 불필요한 태그 제거
    for tag in soup(_REMOVE_TAGS):
        tag.decompose()

    # 본문 후보 요소 탐색
    content_el = None
    for selector in _ARTICLE_SELECTORS:
        content_el = soup.select_one(selector)
        if content_el and len(content_el.get_text(strip=True)) > 100:
            break

    target = content_el if content_el else soup.find("body") or soup

    # 연속 공백/줄바꿈 정리
    text = target.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def scrape_webpage(url: str) -> Dict:
    """웹페이지를 스크래핑하여 본문 텍스트를 반환합니다.

    Args:
        url: 스크래핑할 웹페이지 URL

    Returns:
        {
            "title": str,
            "content": str,
            "url": str,
            "source_type": "webpage"
        }

    Raises:
        ValueError: robots.txt가 크롤링을 금지한 경우
        requests.RequestException: 네트워크 오류
    """
    if not _is_crawl_allowed(url):
        raise ValueError(f"robots.txt가 해당 URL의 크롤링을 금지합니다: {url}")

    resp = requests.get(url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
    resp.raise_for_status()

    # 인코딩 자동 감지
    resp.encoding = resp.apparent_encoding or "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    # 제목 추출
    title = ""
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
    elif soup.title:
        title = soup.title.get_text(strip=True)

    content = _extract_main_content(soup)

    return {
        "title": title,
        "content": content,
        "url": url,
        "source_type": "webpage",
    }
