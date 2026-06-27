"""
웹 검색 서비스 (Tavily API 기반 Grounded Generation)
YouTube 자막 내용을 웹 검색으로 보강하여 더 정확하고 풍부한 콘텐츠 생성 지원
"""
import os
import logging
from typing import List, Dict, Any

import requests

logger = logging.getLogger(__name__)

TAVILY_API_URL = 'https://api.tavily.com/search'


def search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Tavily 웹 검색을 수행합니다.

    Args:
        query: 검색할 쿼리 문자열
        max_results: 최대 검색 결과 수 (기본값 5)

    Returns:
        검색 결과 리스트. 각 항목은 title, url, content, score를 포함.
        API 오류 또는 키 미설정 시 빈 리스트 반환.
    """
    api_key = os.getenv('TAVILY_API_KEY', '')
    if not api_key:
        logger.debug("TAVILY_API_KEY 미설정 — 웹 검색 건너뜀")
        return []

    try:
        resp = requests.post(
            TAVILY_API_URL,
            json={'api_key': api_key, 'query': query, 'max_results': max_results, 'search_depth': 'basic'},
            timeout=10,
            allow_redirects=False,
        )
        status_code = getattr(resp, 'status_code', 0)
        if isinstance(status_code, int) and 300 <= status_code < 400:
            logger.warning("Tavily 웹 검색 리다이렉트 차단: %s", resp.status_code)
            return []
        resp.raise_for_status()
        return _parse_search_results(resp.json())
    except requests.exceptions.RequestException as e:
        logger.warning(f"Tavily 웹 검색 실패 (무시): {e}")
        return []
    except Exception as e:
        logger.warning(f"Tavily 응답 파싱 실패 (무시): {e}")
        return []


def _parse_search_results(data: dict) -> List[Dict[str, Any]]:
    """Tavily API 응답에서 필요한 필드만 추출합니다."""
    return [
        {
            'title': r.get('title', ''),
            'url': r.get('url', ''),
            'content': r.get('content', ''),
            'score': r.get('score', 0.0),
        }
        for r in data.get('results', [])
        if r.get('url')
    ]


def extract_grounding_context(transcript_summary: str) -> Dict[str, Any]:
    """자막 요약에서 검색 쿼리를 추출하고 웹 검색으로 보강 컨텍스트를 반환합니다.

    Args:
        transcript_summary: 자막의 앞 부분 요약 (검색 쿼리 생성에 사용)

    Returns:
        {
            'results': List[Dict] — 검색 결과 목록,
            'context_text': str — 프롬프트에 삽입할 텍스트 형식 컨텍스트,
            'enabled': bool — 실제 검색이 수행되었는지 여부
        }
    """
    from config import WEB_SEARCH_MAX_RESULTS

    results = search(transcript_summary[:300], max_results=WEB_SEARCH_MAX_RESULTS)

    if not results:
        return {'results': [], 'context_text': '', 'enabled': False}

    # 프롬프트용 텍스트 컨텍스트 생성
    lines = []
    for i, r in enumerate(results, 1):
        title = r['title'] or '제목 없음'
        url = r['url']
        # 본문이 너무 길면 잘라내기
        snippet = r['content'][:300] if r['content'] else ''
        lines.append(f"{i}. [{title}]({url})\n   {snippet}")

    context_text = '\n'.join(lines)

    return {
        'results': results,
        'context_text': context_text,
        'enabled': True,
    }
