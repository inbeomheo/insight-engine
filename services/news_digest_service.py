"""
뉴스 다이제스트 서비스

복수 뉴스 URL에서 본문을 추출하고, 주제별로 클러스터링하여
종합 다이제스트 마크다운을 생성합니다.
"""
import logging
from collections import defaultdict
from typing import Dict, List

logger = logging.getLogger(__name__)

# 키워드 기반 클러스터링에 사용할 최소 공통 단어 수
_MIN_COMMON_WORDS = 2
_MIN_WORD_LENGTH = 2


def create_digest(urls: List[str]) -> Dict:
    """복수 뉴스 URL에서 종합 다이제스트를 생성합니다.

    Args:
        urls: 뉴스 기사 URL 리스트 (1개 이상)

    Returns:
        {
            "title": "뉴스 다이제스트",
            "content": str,  # 마크다운 형식
            "sources": list,
            "source_type": "news_digest"
        }

    Raises:
        ValueError: 유효한 기사를 하나도 추출할 수 없는 경우
    """
    if not urls:
        raise ValueError("최소 1개의 URL이 필요합니다.")

    from services.web_scraper_service import scrape_webpage

    # 1. 각 URL에서 본문 추출
    articles = []
    failed = []
    for url in urls:
        try:
            result = scrape_webpage(url)
            articles.append({
                "title": result.get("title", url),
                "content": result.get("content", ""),
                "url": url,
            })
        except Exception as e:
            logger.warning("기사 추출 실패 (%s): %s", url, e)
            failed.append(url)

    if not articles:
        raise ValueError("모든 기사의 본문 추출에 실패했습니다.")

    # 2. 키워드 기반 클러스터링
    clusters = _cluster_by_keywords(articles)

    # 3. 다이제스트 마크다운 생성
    content = _build_digest_markdown(clusters, failed)

    sources = [{"title": a["title"], "url": a["url"]} for a in articles]

    return {
        "title": "뉴스 다이제스트",
        "content": content,
        "sources": sources,
        "source_type": "news_digest",
    }


def _extract_keywords(text: str) -> set:
    """텍스트에서 주요 키워드(명사성 단어)를 추출합니다."""
    # 간단한 방식: 공백 분할 후 길이 기반 필터링
    words = set()
    for word in text.split():
        # 특수문자 제거
        clean = ''.join(c for c in word if c.isalnum())
        if len(clean) >= _MIN_WORD_LENGTH:
            words.add(clean.lower())
    return words


def _cluster_by_keywords(articles: List[Dict]) -> List[Dict]:
    """기사들을 키워드 유사도 기반으로 클러스터링합니다.

    간단한 그리디 방식: 첫 기사부터 시작, 공통 키워드가 충분하면 같은 클러스터에 추가.
    """
    if len(articles) <= 1:
        return [{"topic": articles[0]["title"] if articles else "", "articles": articles}]

    # 각 기사의 키워드 추출
    article_keywords = []
    for article in articles:
        kw = _extract_keywords(article["title"] + " " + article["content"][:500])
        article_keywords.append(kw)

    clusters = []
    assigned = set()

    for i, article in enumerate(articles):
        if i in assigned:
            continue

        cluster_articles = [article]
        cluster_keywords = article_keywords[i].copy()
        assigned.add(i)

        for j in range(i + 1, len(articles)):
            if j in assigned:
                continue
            common = cluster_keywords & article_keywords[j]
            if len(common) >= _MIN_COMMON_WORDS:
                cluster_articles.append(articles[j])
                cluster_keywords |= article_keywords[j]
                assigned.add(j)

        # 클러스터 주제: 첫 기사 제목 사용
        clusters.append({
            "topic": cluster_articles[0]["title"],
            "articles": cluster_articles,
        })

    return clusters


def _build_digest_markdown(clusters: List[Dict], failed: List[str]) -> str:
    """클러스터를 기반으로 다이제스트 마크다운을 생성합니다."""
    parts = []

    for i, cluster in enumerate(clusters, 1):
        topic = cluster["topic"]
        articles = cluster["articles"]

        if len(clusters) > 1:
            parts.append(f"## 주제 {i}: {topic}\n")

        for article in articles:
            parts.append(f"### {article['title']}\n")
            # 본문 요약 (첫 500자)
            summary = article["content"][:500]
            if len(article["content"]) > 500:
                summary += "..."
            parts.append(f"{summary}\n")
            parts.append(f"- 출처: {article['url']}\n")

    if failed:
        parts.append("\n---\n")
        parts.append("**추출 실패 URL:**\n")
        for url in failed:
            parts.append(f"- {url}\n")

    return "\n".join(parts)
