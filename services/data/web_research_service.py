"""웹 리서치 서비스 — 주제 키워드 검색 → 기사 크롤링 → AI 요약"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Optional

import trafilatura
from duckduckgo_search import DDGS

from services.core import ai_service
from services.usage.usage_lock import UsageLockUnavailable
from utils.url_safety import fetch_public_url

logger = logging.getLogger(__name__)

MAX_SEARCH_RESULTS = 5
MAX_ARTICLE_LENGTH = 5000
_ARTICLE_FETCH_TIMEOUT = (5, 10)
_MAX_ARTICLE_RESPONSE_BYTES = 1024 * 1024
_MAX_ARTICLE_REDIRECTS = 3
_ARTICLE_FETCH_HEADERS = {
    'User-Agent': 'InsightEngine/1.0 (web research)',
    'Accept': 'text/html,application/xhtml+xml',
}


def extract_keywords(
    transcripts: List[str],
    model: str,
    on_cost_start: Optional[Callable[[], None]] = None,
) -> List[str]:
    """자막들에서 핵심 검색 키워드 3~5개 추출

    Args:
        transcripts: 자막 텍스트 리스트
        model: LiteLLM 모델 ID

    Returns:
        list[str]: 키워드 리스트 (빈 리스트 가능)
    """
    combined = '\n---\n'.join(t[:2000] for t in transcripts)
    prompt = (
        '다음 자막들의 핵심 주제를 나타내는 검색 키워드를 3~5개 추출하세요.\n'
        '쉼표로 구분하여 키워드만 출력하세요. 다른 텍스트는 포함하지 마세요.\n\n'
        f'{combined}'
    )
    try:
        result = ai_service.create_content(
            content=prompt, model=model,
            style_prompt='키워드만 쉼표로 구분하여 출력하세요.',
            style_id='summary',
            on_cost_start=on_cost_start,
        )
        raw = result.get('content', '')
        keywords = [k.strip() for k in raw.split(',') if k.strip()]
        return keywords[:5]
    except UsageLockUnavailable:
        raise
    except Exception as e:
        logger.error('키워드 추출 실패: %s', e)
        return []


def search_web(keywords: List[str], max_results: int = MAX_SEARCH_RESULTS) -> List[Dict[str, str]]:
    """DuckDuckGo로 키워드 검색

    Args:
        keywords: 검색 키워드 리스트
        max_results: 최대 검색 결과 수

    Returns:
        list[dict]: [{'title': str, 'url': str}, ...]
    """
    query = ' '.join(keywords)
    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
        return [
            {'title': r.get('title', ''), 'url': r.get('href', '')}
            for r in raw_results if r.get('href')
        ]
    except Exception as e:
        logger.error('웹 검색 실패: %s', e)
        return []


def crawl_article(url: str) -> Optional[str]:
    """trafilatura로 기사 본문 추출

    Args:
        url: 기사 URL

    Returns:
        str 또는 None: 본문 텍스트
    """
    try:
        response = fetch_public_url(
            url,
            headers=_ARTICLE_FETCH_HEADERS,
            timeout=_ARTICLE_FETCH_TIMEOUT,
            max_bytes=_MAX_ARTICLE_RESPONSE_BYTES,
            max_redirects=_MAX_ARTICLE_REDIRECTS,
        )
        response.raise_for_status()
        if not response.content:
            return None
        text = trafilatura.extract(response.content)
        if text:
            return text[:MAX_ARTICLE_LENGTH]
        return None
    except Exception as e:
        logger.warning('기사 크롤링 실패 (%s): %s', url, e)
        return None


def _crawl_articles(search_results: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """검색 결과에서 기사 본문을 병렬 크롤링합니다."""
    articles = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_map = {
            executor.submit(crawl_article, sr['url']): sr
            for sr in search_results
        }
        for future in as_completed(future_map):
            sr = future_map[future]
            try:
                text = future.result()
            except Exception as e:
                logger.warning('Article crawl failed (%s): %s', sr['url'], e)
                continue
            if text:
                articles.append({**sr, 'text': text})
    return articles


def _summarize_articles(
    articles: List[Dict],
    model: str,
    on_cost_start: Optional[Callable[[], None]] = None,
) -> List[Dict[str, str]]:
    """크롤링된 기사들을 병렬 AI 요약합니다."""
    def summarize(prompt: str):
        return ai_service.create_content(
            content=prompt,
            model=model,
            style_prompt='200자 이내 핵심 요약만 출력하세요.',
            style_id='summary',
            on_cost_start=on_cost_start,
        )

    sources = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_map = {}
        for art in articles:
            prompt = f'다음 기사를 200자 이내로 핵심만 요약하세요:\n\n{art["text"][:3000]}'
            fut = executor.submit(summarize, prompt)
            future_map[fut] = art

        for future in as_completed(future_map):
            art = future_map[future]
            try:
                result = future.result()
                sources.append({
                    'title': art['title'], 'url': art['url'],
                    'summary': result.get('content', ''),
                })
            except UsageLockUnavailable:
                for pending in future_map:
                    pending.cancel()
                raise
            except Exception as e:
                logger.warning('기사 요약 실패 (%s): %s', art['url'], e)
    return sources


def research_topic(
    transcripts: List[str],
    model: str,
    max_sources: int = MAX_SEARCH_RESULTS,
    on_cost_start: Optional[Callable[[], None]] = None,
) -> List[Dict[str, str]]:
    """전체 웹 리서치 파이프라인: 키워드 추출 → 검색 → 크롤링 → 요약

    Args:
        transcripts: 자막 텍스트 리스트
        model: LiteLLM 모델 ID
        max_sources: 최대 외부 소스 수

    Returns:
        list[dict]: [{'title': str, 'summary': str, 'url': str}, ...]
    """
    keywords = extract_keywords(
        transcripts,
        model,
        on_cost_start=on_cost_start,
    )
    if not keywords:
        return []

    search_results = search_web(keywords, max_results=max_sources)
    if not search_results:
        return []

    articles = _crawl_articles(search_results)
    if not articles:
        return []

    return _summarize_articles(
        articles,
        model,
        on_cost_start=on_cost_start,
    )
