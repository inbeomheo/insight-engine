"""
의미 캐시 서비스.

의미적으로 유사한 쿼리에 캐시 히트를 제공한다.
키워드 기반 Jaccard 유사도를 사용한다.
"""

from dataclasses import dataclass, field
from typing import Optional
import re
import uuid
from datetime import datetime


@dataclass
class CacheEntry:
    """캐시 항목"""
    entry_id: str = ""
    query: str = ""
    response: str = ""
    query_keywords: set = field(default_factory=set)
    created_at: str = ""
    hit_count: int = 0
    ttl_seconds: int = 3600


@dataclass
class SemanticCache:
    """의미 캐시"""
    cache_id: str = ""
    entries: list = field(default_factory=list)
    max_size: int = 100


def _extract_keywords(text: str) -> set:
    """텍스트에서 키워드 추출 (소문자 정규화, 불용어 제거)"""
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
        "to", "for", "of", "and", "or", "but", "not", "이", "가", "은",
        "는", "을", "를", "에", "의", "와", "과", "도", "로", "으로",
        "에서", "부터", "까지", "한", "할", "하는", "된", "되는",
    }
    # 알파벳/한글 단어 추출
    words = re.findall(r'[a-zA-Z가-힣]+', text.lower())
    return {w for w in words if w not in stopwords and len(w) > 1}


def _jaccard_similarity(set_a: set, set_b: set) -> float:
    """Jaccard 유사도 계산"""
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def put(
    cache: SemanticCache,
    query: str,
    response: str,
    ttl: int = 3600
) -> SemanticCache:
    """
    캐시에 항목 저장.

    max_size 초과 시 자동으로 LRU 삭제.
    """
    keywords = _extract_keywords(query)

    entry = CacheEntry(
        entry_id=str(uuid.uuid4()),
        query=query,
        response=response,
        query_keywords=keywords,
        created_at=datetime.utcnow().isoformat(),
        hit_count=0,
        ttl_seconds=ttl,
    )

    new_entries = list(cache.entries) + [entry]

    # max_size 초과 시 LRU 삭제
    while len(new_entries) > cache.max_size:
        new_entries = evict_lru_entries(new_entries)

    return SemanticCache(
        cache_id=cache.cache_id,
        entries=new_entries,
        max_size=cache.max_size,
    )


def get(
    cache: SemanticCache,
    query: str,
    similarity_threshold: float = 0.5
) -> Optional[CacheEntry]:
    """
    의미 매칭 조회.

    Jaccard 유사도가 threshold 이상인 항목 중 가장 유사한 것을 반환.
    """
    query_keywords = _extract_keywords(query)
    if not query_keywords:
        return None

    best_entry = None
    best_similarity = 0.0

    for entry in cache.entries:
        sim = _jaccard_similarity(query_keywords, entry.query_keywords)
        if sim >= similarity_threshold and sim > best_similarity:
            best_similarity = sim
            best_entry = entry

    if best_entry:
        best_entry.hit_count += 1

    return best_entry


def evict_lru_entries(entries: list) -> list:
    """가장 오래되고 히트 수가 적은 항목 1개 삭제"""
    if not entries:
        return entries

    # hit_count 오름차순 → created_at 오름차순으로 정렬해 첫 번째 제거
    target = min(entries, key=lambda e: (e.hit_count, e.created_at))
    return [e for e in entries if e.entry_id != target.entry_id]


def evict_lru(cache: SemanticCache) -> SemanticCache:
    """LRU 삭제 (max_size 초과 시)"""
    new_entries = list(cache.entries)
    while len(new_entries) > cache.max_size:
        new_entries = evict_lru_entries(new_entries)

    return SemanticCache(
        cache_id=cache.cache_id,
        entries=new_entries,
        max_size=cache.max_size,
    )


def get_stats(cache: SemanticCache) -> dict:
    """캐시 통계"""
    total_hits = sum(e.hit_count for e in cache.entries)
    return {
        "entry_count": len(cache.entries),
        "max_size": cache.max_size,
        "utilization": round(len(cache.entries) / cache.max_size, 4) if cache.max_size > 0 else 0.0,
        "total_hits": total_hits,
        "avg_hits_per_entry": round(total_hits / len(cache.entries), 2) if cache.entries else 0.0,
    }
