"""적응형 RAG 서비스

질의 복잡도에 따라 검색 전략을 자동 조정합니다.
단순 검색, 반복 검색, 다중 홉 검색 전략을 지원합니다.
"""
import re
import uuid
from dataclasses import dataclass, field


@dataclass
class RAGChunk:
    """RAG 청크 (이 서비스 자체 정의)"""
    chunk_id: str                       # 청크 고유 ID
    content: str                        # 청크 텍스트
    metadata: dict = field(default_factory=dict)  # 메타데이터
    embedding_hint: str = ''            # 키워드 기반 의사 임베딩


@dataclass
class RAGStrategy:
    """RAG 검색 전략"""
    strategy_type: str                  # simple / iterative / multi_hop
    num_iterations: int = 1             # 반복 횟수
    chunk_size: int = 200               # 청크 크기 (글자 수)
    top_k: int = 5                      # 상위 결과 수


def _extract_keywords(text: str) -> set[str]:
    """텍스트에서 키워드 추출 (2자 이상)"""
    tokens = re.findall(r'[\w가-힣]+', text.lower())
    return {t for t in tokens if len(t) >= 2}


def _count_concepts(query: str) -> int:
    """질의에서 핵심 개념 수 추정"""
    keywords = _extract_keywords(query)
    # 불용어 제거 (간단한 한국어/영어 불용어)
    stopwords = {
        '그리고', '또는', '하지만', '그런데', '어떻게', '무엇',
        'the', 'and', 'or', 'but', 'how', 'what', 'is', 'are',
        '이것', '그것', '저것', '대해', '대한', '에서',
    }
    meaningful = keywords - stopwords
    return len(meaningful)


def assess_complexity(query: str) -> str:
    """질의 복잡도 평가

    Args:
        query: 검색 질의

    Returns:
        'simple' | 'moderate' | 'complex'
    """
    if not query or not query.strip():
        return 'simple'

    concept_count = _count_concepts(query)

    # 관계 키워드 존재 여부 (다중 관계 표현)
    relation_keywords = [
        '관계', '영향', '비교', '차이', '원인', '결과',
        '과정', '발전', '변화', '연결', '상호작용',
        'relationship', 'impact', 'compare', 'difference',
    ]
    has_relations = any(kw in query.lower() for kw in relation_keywords)

    # 접속사 수 (다중 개념 표현)
    conjunction_count = len(re.findall(
        r'\b(?:그리고|및|또는|and|or|와|과)\b', query, re.IGNORECASE
    ))

    if concept_count >= 4 or (has_relations and concept_count >= 3) or conjunction_count >= 2:
        return 'complex'
    elif concept_count >= 2 or has_relations or conjunction_count >= 1:
        return 'moderate'
    else:
        return 'simple'


def select_strategy(complexity: str) -> RAGStrategy:
    """복잡도에 따른 검색 전략 선택

    Args:
        complexity: 'simple' | 'moderate' | 'complex'

    Returns:
        선택된 RAGStrategy
    """
    if complexity == 'complex':
        return RAGStrategy(
            strategy_type='multi_hop',
            num_iterations=3,
            chunk_size=150,
            top_k=10,
        )
    elif complexity == 'moderate':
        return RAGStrategy(
            strategy_type='iterative',
            num_iterations=2,
            chunk_size=200,
            top_k=7,
        )
    else:
        return RAGStrategy(
            strategy_type='simple',
            num_iterations=1,
            chunk_size=300,
            top_k=5,
        )


def _keyword_search(chunks: list[RAGChunk], keywords: set[str], top_k: int) -> list[RAGChunk]:
    """키워드 기반 청크 검색 (내부 유틸)"""
    if not chunks or not keywords:
        return []

    scored: list[tuple[float, RAGChunk]] = []
    for chunk in chunks:
        chunk_keywords = _extract_keywords(chunk.content)
        if not chunk_keywords:
            scored.append((0.0, chunk))
            continue
        intersection = keywords & chunk_keywords
        score = len(intersection) / len(keywords) if keywords else 0.0
        scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]


def iterative_search(
    chunks: list[RAGChunk],
    query: str,
    iterations: int = 2,
) -> list[RAGChunk]:
    """반복 검색

    이전 검색 결과의 키워드로 쿼리를 확장하며 반복합니다.

    Args:
        chunks: 검색 대상 청크 목록
        query: 초기 질의
        iterations: 반복 횟수

    Returns:
        최종 검색 결과 청크 목록
    """
    if not chunks or not query:
        return []

    current_keywords = _extract_keywords(query)
    seen_ids: set[str] = set()
    all_results: list[RAGChunk] = []

    for _ in range(max(1, iterations)):
        results = _keyword_search(chunks, current_keywords, top_k=5)

        for chunk in results:
            if chunk.chunk_id not in seen_ids:
                seen_ids.add(chunk.chunk_id)
                all_results.append(chunk)

        # 결과에서 새 키워드 추출하여 확장
        for chunk in results:
            new_keywords = _extract_keywords(chunk.content)
            current_keywords = current_keywords | new_keywords

    return all_results


def multi_hop_search(
    chunks: list[RAGChunk],
    query: str,
    hops: int = 3,
) -> list[RAGChunk]:
    """다중 홉 검색

    이전 홉의 결과에서 연관 청크를 체이닝하며 탐색합니다.

    Args:
        chunks: 검색 대상 청크 목록
        query: 초기 질의
        hops: 홉 수

    Returns:
        체이닝된 검색 결과 청크 목록
    """
    if not chunks or not query:
        return []

    seen_ids: set[str] = set()
    chain: list[RAGChunk] = []

    # 첫 홉: 원본 질의로 검색
    current_keywords = _extract_keywords(query)
    hop_results = _keyword_search(chunks, current_keywords, top_k=3)

    for chunk in hop_results:
        if chunk.chunk_id not in seen_ids:
            seen_ids.add(chunk.chunk_id)
            chain.append(chunk)

    # 후속 홉: 이전 결과의 키워드로 연관 청크 탐색
    for _ in range(1, max(1, hops)):
        if not chain:
            break

        # 마지막 결과들의 키워드를 다음 쿼리로 사용
        hop_keywords: set[str] = set()
        for chunk in chain[-3:]:
            hop_keywords |= _extract_keywords(chunk.content)

        # 이미 본 청크 제외
        remaining = [c for c in chunks if c.chunk_id not in seen_ids]
        hop_results = _keyword_search(remaining, hop_keywords, top_k=2)

        for chunk in hop_results:
            if chunk.chunk_id not in seen_ids:
                seen_ids.add(chunk.chunk_id)
                chain.append(chunk)

    return chain
