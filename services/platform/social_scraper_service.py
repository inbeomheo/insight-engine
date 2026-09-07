"""
소셜 미디어 스크래퍼 서비스

Twitter(X), Reddit, Hacker News에서 콘텐츠를 추출합니다.
- Twitter: nitter 대안 프론트엔드 또는 trafilatura 폴백
- Reddit: JSON API (.json 접미사)
- Hacker News: Firebase API
"""
from __future__ import annotations

import logging
import re
from typing import Dict
from urllib.parse import urlencode, urlparse

import requests
import trafilatura

from utils.url_safety import fetch_public_url, is_safe_public_url

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 15  # 초
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_USER_AGENT = "InsightEngine/1.0 (social ingestion)"

# Nitter 인스턴스 목록 (가용성 순)
_NITTER_INSTANCES = [
    "nitter.net",
    "nitter.privacydev.net",
]

# Reddit URL → .json 변환용 패턴
_REDDIT_COMMENT_RE = re.compile(
    r"reddit\.com/r/(\w+)/comments/(\w+)", re.IGNORECASE
)

# HN 아이템 ID 추출 패턴
_HN_ITEM_RE = re.compile(r"news\.ycombinator\.com/item\?id=(\d+)", re.IGNORECASE)

_HN_API_BASE = "https://hacker-news.firebaseio.com/v0"

# Stack Overflow URL 패턴
_SO_QUESTION_RE = re.compile(
    r"stackoverflow\.com/questions/(\d+)", re.IGNORECASE
)

_SE_API_BASE = "https://api.stackexchange.com/2.3"


def scrape_twitter_thread(url: str) -> Dict:
    """Twitter/X 스레드에서 본문을 추출합니다.

    1차: nitter 대안 프론트엔드를 통해 trafilatura로 추출
    2차: 원본 URL에 대해 trafilatura 직접 시도

    Returns:
        {"title": str, "content": str, "url": str, "source_type": "twitter"}

    Raises:
        ValueError: 본문을 추출할 수 없는 경우
    """
    if not is_safe_public_url(url):
        raise ValueError("안전하지 않은 URL입니다.")

    # 원본 URL에서 경로 추출 (예: /user/status/123)
    parsed = urlparse(url)
    path = parsed.path

    # 1차: nitter 인스턴스를 통해 추출 시도
    for instance in _NITTER_INSTANCES:
        nitter_url = f"https://{instance}{path}"
        title, content = _extract_with_trafilatura(nitter_url)
        if content and len(content.strip()) > 30:
            return {
                "title": title or _make_twitter_title(url),
                "content": content,
                "url": url,
                "source_type": "twitter",
            }

    # 2차: 원본 URL 직접 시도
    title, content = _extract_with_trafilatura(url)
    if content and len(content.strip()) > 30:
        return {
            "title": title or _make_twitter_title(url),
            "content": content,
            "url": url,
            "source_type": "twitter",
        }

    raise ValueError("Twitter 게시물에서 본문을 추출할 수 없습니다.")


def scrape_reddit_post(url: str) -> Dict:
    """Reddit 포스트에서 본문과 상위 댓글을 추출합니다.

    Reddit JSON API를 사용합니다 (URL 뒤에 .json 추가).

    Returns:
        {"title": str, "content": str, "url": str, "source_type": "reddit"}

    Raises:
        ValueError: 포스트를 추출할 수 없는 경우
    """
    if not is_safe_public_url(url):
        raise ValueError("안전하지 않은 URL입니다.")

    json_url = url.rstrip("/") + ".json"

    try:
        resp = fetch_public_url(
            json_url,
            headers={"User-Agent": "InsightEngine/1.0"},
            timeout=_REQUEST_TIMEOUT,
            max_bytes=_MAX_RESPONSE_BYTES,
            max_redirects=3,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        raise ValueError(f"Reddit 포스트를 가져올 수 없습니다: {e}")

    # Reddit JSON 응답: [포스트 리스팅, 댓글 리스팅]
    if not isinstance(data, list) or len(data) < 1:
        raise ValueError("Reddit 응답 형식이 올바르지 않습니다.")

    # 포스트 추출
    post_data = data[0]["data"]["children"][0]["data"]
    title = post_data.get("title", "Reddit 포스트")
    selftext = post_data.get("selftext", "")

    # 상위 댓글 추출 (최대 10개)
    comments = []
    if len(data) > 1:
        comment_children = data[1].get("data", {}).get("children", [])
        for child in comment_children[:10]:
            if child.get("kind") != "t1":
                continue
            body = child.get("data", {}).get("body", "")
            if body:
                comments.append(body)

    # 콘텐츠 조합
    content_parts = []
    if selftext:
        content_parts.append(selftext)
    if comments:
        content_parts.append("\n\n---\n[상위 댓글]\n")
        for i, c in enumerate(comments, 1):
            content_parts.append(f"{i}. {c}")

    content = "\n\n".join(content_parts)
    if not content.strip():
        raise ValueError("Reddit 포스트에서 본문을 추출할 수 없습니다.")

    return {
        "title": title,
        "content": content,
        "url": url,
        "source_type": "reddit",
    }


def scrape_hackernews(url: str) -> Dict:
    """Hacker News 아이템에서 본문과 상위 댓글을 추출합니다.

    HN Firebase API를 사용합니다.

    Returns:
        {"title": str, "content": str, "url": str, "source_type": "hackernews"}

    Raises:
        ValueError: 아이템을 추출할 수 없는 경우
    """
    if not is_safe_public_url(url):
        raise ValueError("안전하지 않은 URL입니다.")

    # URL에서 아이템 ID 추출
    match = _HN_ITEM_RE.search(url)
    if not match:
        raise ValueError("유효하지 않은 Hacker News URL입니다.")

    item_id = match.group(1)

    try:
        resp = fetch_public_url(
            f"{_HN_API_BASE}/item/{item_id}.json",
            timeout=_REQUEST_TIMEOUT,
            max_bytes=_MAX_RESPONSE_BYTES,
            max_redirects=3,
        )
        resp.raise_for_status()
        item = resp.json()
    except (requests.RequestException, ValueError) as e:
        raise ValueError(f"Hacker News 아이템을 가져올 수 없습니다: {e}")

    if not item:
        raise ValueError(f"Hacker News 아이템을 찾을 수 없습니다: {item_id}")

    title = item.get("title", "Hacker News 포스트")
    text = item.get("text", "")
    item_url = item.get("url", "")

    # 상위 댓글 추출 (최대 10개)
    comments = []
    kid_ids = item.get("kids", [])[:10]
    for kid_id in kid_ids:
        try:
            cr = fetch_public_url(
                f"{_HN_API_BASE}/item/{kid_id}.json",
                timeout=_REQUEST_TIMEOUT,
                max_bytes=_MAX_RESPONSE_BYTES,
                max_redirects=3,
            )
            cr.raise_for_status()
            comment = cr.json()
            if comment and comment.get("text"):
                comments.append(comment["text"])
        except Exception:
            continue

    # 콘텐츠 조합
    content_parts = []
    if item_url:
        content_parts.append(f"원문 링크: {item_url}")
    if text:
        content_parts.append(text)
    if comments:
        content_parts.append("\n---\n[상위 댓글]\n")
        for i, c in enumerate(comments, 1):
            # HTML 태그 간단 제거
            clean = re.sub(r"<[^>]+>", "", c)
            content_parts.append(f"{i}. {clean}")

    content = "\n\n".join(content_parts)
    if not content.strip():
        raise ValueError(f"Hacker News 아이템에서 본문을 추출할 수 없습니다: {url}")

    return {
        "title": title,
        "content": content,
        "url": url,
        "source_type": "hackernews",
    }


def scrape_stackoverflow(url: str) -> Dict:
    """Stack Overflow 질문에서 본문과 답변을 추출합니다.

    Stack Exchange API v2.3을 사용합니다.

    Returns:
        {"title": str, "content": str, "url": str, "source_type": "stackoverflow"}

    Raises:
        ValueError: 질문을 추출할 수 없는 경우
    """
    if not is_safe_public_url(url):
        raise ValueError("안전하지 않은 URL입니다.")

    match = _SO_QUESTION_RE.search(url)
    if not match:
        raise ValueError("유효하지 않은 Stack Overflow URL입니다.")

    question_id = match.group(1)

    # 질문 + 답변 한번에 조회
    try:
        question_query = urlencode(
            {
                "site": "stackoverflow",
                "filter": "withbody",  # 본문 포함
                "sort": "votes",
            }
        )
        resp = fetch_public_url(
            f"{_SE_API_BASE}/questions/{question_id}?{question_query}",
            timeout=_REQUEST_TIMEOUT,
            max_bytes=_MAX_RESPONSE_BYTES,
            max_redirects=3,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        raise ValueError(f"Stack Overflow 질문을 가져올 수 없습니다: {e}")

    items = data.get("items", [])
    if not items:
        raise ValueError(f"Stack Overflow 질문을 찾을 수 없습니다: {question_id}")

    question = items[0]
    title = question.get("title", "Stack Overflow 질문")
    body = question.get("body", "")
    # HTML 태그 제거
    body_clean = re.sub(r"<[^>]+>", "", body)

    # 답변 조회 (votes 순)
    answers_text = []
    try:
        answer_query = urlencode(
            {
                "site": "stackoverflow",
                "filter": "withbody",
                "sort": "votes",
                "order": "desc",
            }
        )
        ans_resp = fetch_public_url(
            f"{_SE_API_BASE}/questions/{question_id}/answers?{answer_query}",
            timeout=_REQUEST_TIMEOUT,
            max_bytes=_MAX_RESPONSE_BYTES,
            max_redirects=3,
        )
        ans_resp.raise_for_status()
        ans_data = ans_resp.json()

        for ans in ans_data.get("items", [])[:5]:  # 상위 5개 답변
            ans_body = ans.get("body", "")
            ans_clean = re.sub(r"<[^>]+>", "", ans_body)
            score = ans.get("score", 0)
            accepted = " ✓" if ans.get("is_accepted") else ""
            if ans_clean.strip():
                answers_text.append(f"[답변 (votes: {score}{accepted})]\n{ans_clean}")
    except Exception:
        logger.warning("Stack Overflow 답변 조회 실패 (질문만 반환)")

    # 콘텐츠 조합
    content_parts = [f"[질문]\n{body_clean}"]
    if answers_text:
        content_parts.append("\n---\n")
        content_parts.extend(answers_text)

    content = "\n\n".join(content_parts)
    if not content.strip():
        raise ValueError(f"Stack Overflow 질문에서 본문을 추출할 수 없습니다: {url}")

    return {
        "title": title,
        "content": content,
        "url": url,
        "source_type": "stackoverflow",
    }


def _extract_with_trafilatura(url: str) -> tuple:
    """안전하게 미리 받은 HTML을 trafilatura로 추출합니다."""
    try:
        response = fetch_public_url(
            url,
            headers={
                "User-Agent": _USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
            },
            timeout=_REQUEST_TIMEOUT,
            max_bytes=_MAX_RESPONSE_BYTES,
            max_redirects=3,
        )
        response.raise_for_status()
        html = response.content
        if not html:
            return "", ""

        content = trafilatura.extract(html, include_tables=True, include_links=False) or ""
        meta = trafilatura.metadata.extract_metadata(html, default_url=url)
        title = meta.title if meta and meta.title else ""

        return title, content
    except Exception as e:
        logger.warning("trafilatura 실패: %s — %s", url, e)
        return "", ""


def _make_twitter_title(url: str) -> str:
    """Twitter URL에서 기본 제목을 생성합니다."""
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    if parts:
        return f"@{parts[0]} 트윗"
    return "Twitter 게시물"
