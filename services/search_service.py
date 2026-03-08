"""전문 검색 서비스 (F5-09)

인메모리 콘텐츠 검색 — 제목, 본문, 스타일에서 키워드 검색.
Supabase FTS 연동 시 교체 가능.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 인메모리 검색 인덱스: {content_id: {title, content, style, created_at}}
_index: dict[str, dict] = {}


def index_content(content_id: str, title: str, content: str,
                  style: str = '', created_at: str = '') -> None:
    """콘텐츠를 검색 인덱스에 추가합니다."""
    _index[content_id] = {
        'id': content_id,
        'title': title,
        'content': content,
        'style': style,
        'created_at': created_at,
    }


def remove_from_index(content_id: str) -> None:
    """검색 인덱스에서 콘텐츠를 제거합니다."""
    _index.pop(content_id, None)


def search(query: str, style_filter: Optional[str] = None,
           limit: int = 20, offset: int = 0) -> dict:
    """키워드로 콘텐츠를 검색합니다.

    Returns:
        {results: [...], total: int, query: str}
    """
    if not query.strip():
        return {'results': [], 'total': 0, 'query': query}

    # 검색어를 공백으로 분리하여 AND 매칭
    terms = [t.lower() for t in query.strip().split() if t]
    results = []

    for item in _index.values():
        # 스타일 필터
        if style_filter and item.get('style') != style_filter:
            continue

        # 제목 + 본문 통합 텍스트
        text = f"{item['title']} {item['content']}".lower()

        # 모든 검색어가 포함되어야 함 (AND)
        if all(term in text for term in terms):
            # 관련도: 제목 매칭 가중치 높음
            title_lower = item['title'].lower()
            score = sum(2 if term in title_lower else 1 for term in terms)

            # 미리보기 텍스트: 첫 번째 매칭 주변 100자
            snippet = _extract_snippet(item['content'], terms[0])

            results.append({
                'id': item['id'],
                'title': item['title'],
                'snippet': snippet,
                'style': item.get('style', ''),
                'created_at': item.get('created_at', ''),
                'score': score,
            })

    # 관련도 내림차순 정렬
    results.sort(key=lambda x: x['score'], reverse=True)
    total = len(results)

    return {
        'results': results[offset:offset + limit],
        'total': total,
        'query': query,
    }


def _extract_snippet(content: str, term: str, context_chars: int = 100) -> str:
    """검색어 주변의 미리보기 텍스트를 추출합니다."""
    idx = content.lower().find(term.lower())
    if idx == -1:
        return content[:200] + ('...' if len(content) > 200 else '')

    start = max(0, idx - context_chars)
    end = min(len(content), idx + len(term) + context_chars)
    snippet = content[start:end].strip()

    if start > 0:
        snippet = '...' + snippet
    if end < len(content):
        snippet = snippet + '...'

    return snippet
