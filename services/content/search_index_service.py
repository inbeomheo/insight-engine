"""
콘텐츠 검색 인덱스 서비스

역인덱스 기반 전문 검색을 제공합니다.
인메모리로 동작하며, 콘텐츠 컬렉션을 인덱싱 후 검색합니다.
"""
import logging
import re
from collections import defaultdict
from typing import List

logger = logging.getLogger(__name__)

_WORD_PATTERN = re.compile(r'[가-힣]{2,}|[a-zA-Z]{3,}')
_HEADING_PATTERN = re.compile(r'^#{1,6}\s+(.+)$', re.MULTILINE)

_STOPWORDS = frozenset([
    '이', '그', '저', '것', '수', '등', '및', '또는', '위한', '대한',
    '통해', '따라', '경우', '때문', '이후', '위해', '함께', '가장',
    '그리고', '하지만', '그러나', '따라서', '그래서', '또한',
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
    'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
    'and', 'but', 'or', 'not', 'this', 'that', 'it', 'its',
])


def _tokenize(text: str) -> List[str]:
    """텍스트를 토큰(단어)으로 분리합니다."""
    words = _WORD_PATTERN.findall(text.lower())
    return [w for w in words if w not in _STOPWORDS]


def build_index(contents: List[dict]) -> dict:
    """콘텐츠 컬렉션의 역인덱스를 빌드합니다.

    Args:
        contents: [{'id': str, 'title': str, 'content': str}, ...]

    Returns:
        {
            'index': {word: [{'id': str, 'frequency': int}]},
            'documents': int,
            'terms': int,
        }
    """
    if not contents:
        return {'index': {}, 'documents': 0, 'terms': 0}

    inverted_index = defaultdict(list)

    for item in contents:
        doc_id = item.get('id', '')
        title = item.get('title', '')
        content = item.get('content', '')
        full_text = f'{title} {content}'

        tokens = _tokenize(full_text)
        word_freq = defaultdict(int)
        for token in tokens:
            word_freq[token] += 1

        for word, freq in word_freq.items():
            inverted_index[word].append({
                'id': doc_id,
                'frequency': freq,
            })

    return {
        'index': dict(inverted_index),
        'documents': len(contents),
        'terms': len(inverted_index),
    }


def search(index: dict, query: str, max_results: int = 10) -> dict:
    """인덱스에서 검색합니다.

    Args:
        index: build_index()로 생성된 역인덱스
        query: 검색 쿼리
        max_results: 최대 결과 수

    Returns:
        {
            'results': [{'id': str, 'score': float, 'matched_terms': [str]}],
            'total': int,
            'query_terms': [str],
        }
    """
    if not index or not query or not query.strip():
        return {'results': [], 'total': 0, 'query_terms': []}

    inv_index = index.get('index', {})
    query_terms = _tokenize(query)

    if not query_terms:
        return {'results': [], 'total': 0, 'query_terms': []}

    # 문서별 점수 계산
    doc_scores = defaultdict(lambda: {'score': 0.0, 'matched_terms': []})

    for term in query_terms:
        if term in inv_index:
            for entry in inv_index[term]:
                doc_id = entry['id']
                doc_scores[doc_id]['score'] += entry['frequency']
                if term not in doc_scores[doc_id]['matched_terms']:
                    doc_scores[doc_id]['matched_terms'].append(term)

    # 매칭 단어 수 보너스 (여러 쿼리 단어가 매칭되면 점수 부스트)
    for doc_id, info in doc_scores.items():
        match_ratio = len(info['matched_terms']) / len(query_terms)
        info['score'] *= (1 + match_ratio)

    # 정렬 및 제한
    sorted_results = sorted(
        [{'id': doc_id, **info} for doc_id, info in doc_scores.items()],
        key=lambda x: x['score'],
        reverse=True,
    )[:max_results]

    # 점수 정규화
    if sorted_results:
        max_score = sorted_results[0]['score']
        for r in sorted_results:
            r['score'] = round(r['score'] / max_score, 4) if max_score > 0 else 0

    return {
        'results': sorted_results,
        'total': len(sorted_results),
        'query_terms': query_terms,
    }
