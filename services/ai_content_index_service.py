"""
AI 콘텐츠 인덱스 서비스 — AI 검색엔진용 콘텐츠 인덱스
"""

import uuid
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class IndexEntry:
    """인덱스 항목"""
    entry_id: str
    url: str
    title: str
    summary: str
    keywords: list  # 자동 추출된 키워드
    structured_data: dict  # schema.org 등
    last_indexed: str  # ISO 8601


@dataclass
class ContentIndex:
    """콘텐츠 인덱스"""
    index_id: str
    entries: list  # list[IndexEntry]


def _extract_keywords(content: str, max_keywords: int = 10) -> list:
    """콘텐츠에서 키워드 자동 추출 (단어 빈도 기반)"""
    # 한국어/영어 단어 추출
    words = re.findall(r"[가-힣]{2,}|[a-zA-Z]{3,}", content)
    # 빈도 계산
    freq = {}
    for w in words:
        w_lower = w.lower()
        freq[w_lower] = freq.get(w_lower, 0) + 1

    # 빈도순 정렬 후 상위 N개
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words[:max_keywords]]


def _generate_summary(content: str, max_length: int = 200) -> str:
    """콘텐츠 요약 (앞부분 추출)"""
    clean = content.strip()
    if len(clean) <= max_length:
        return clean
    # 문장 단위로 자르기
    truncated = clean[:max_length]
    last_period = max(truncated.rfind("."), truncated.rfind("。"), truncated.rfind("!"))
    if last_period > max_length // 2:
        return truncated[:last_period + 1]
    return truncated + "..."


def index_content(index: ContentIndex, url: str, title: str, content: str) -> ContentIndex:
    """콘텐츠 인덱싱 (기존 URL이면 업데이트)"""
    keywords = _extract_keywords(content)
    summary = _generate_summary(content)

    entry = IndexEntry(
        entry_id=str(uuid.uuid4()),
        url=url,
        title=title,
        summary=summary,
        keywords=keywords,
        structured_data={
            "@type": "Article",
            "name": title,
            "url": url,
        },
        last_indexed=datetime.now().isoformat(),
    )

    # 기존 URL 업데이트
    index.entries = [e for e in index.entries if e.url != url]
    index.entries.append(entry)
    return index


def search_index(index: ContentIndex, query: str) -> list:
    """키워드 검색 — 쿼리 단어가 키워드/제목/요약에 포함되면 매칭"""
    query_words = set(query.lower().split())
    results = []

    for entry in index.entries:
        score = 0
        entry_keywords = set(k.lower() for k in entry.keywords)
        title_lower = entry.title.lower()
        summary_lower = entry.summary.lower()

        for qw in query_words:
            if qw in entry_keywords:
                score += 3  # 키워드 매칭 고점수
            if qw in title_lower:
                score += 2
            if qw in summary_lower:
                score += 1

        if score > 0:
            results.append((score, entry))

    results.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in results]


def generate_sitemap(index: ContentIndex) -> str:
    """XML 사이트맵 문자열 생성"""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for entry in index.entries:
        lines.append("  <url>")
        lines.append(f"    <loc>{entry.url}</loc>")
        lines.append(f"    <lastmod>{entry.last_indexed[:10]}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines)


def remove_stale(index: ContentIndex, max_age_days: int, current_date: str) -> ContentIndex:
    """오래된 항목 제거"""
    cutoff = datetime.fromisoformat(current_date) - timedelta(days=max_age_days)
    index.entries = [
        e for e in index.entries
        if datetime.fromisoformat(e.last_indexed) >= cutoff
    ]
    return index
