"""프롬프트 캐싱 서비스 - 반복 프롬프트 prefix 캐시로 비용/지연 감소"""
import hashlib
import time
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class CacheEntry:
    key: str
    prompt_prefix: str
    created_at: float
    ttl: int
    hit_count: int = 0
    tokens_saved: int = 0


@dataclass
class CacheSegment:
    start: int
    end: int
    cache_key: str


@dataclass
class CacheStats:
    total_entries: int
    total_hits: int
    total_tokens_saved: int
    hit_rate: float
    estimated_cost_saved: float


# 인메모리 캐시 저장소
_cache_store: dict[str, CacheEntry] = {}

# 토큰당 추정 비용 (USD) — 통계 계산용
_COST_PER_TOKEN = 0.000001


def compute_cache_key(prompt_parts: list[str]) -> str:
    """SHA256 해시로 프롬프트 prefix 키 생성.

    여러 프롬프트 파트를 결합하여 결정적 캐시 키를 만든다.
    """
    combined = "\n".join(prompt_parts)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def get_or_create_cache(
    key: str, prompt_prefix: str, ttl: int = 3600
) -> CacheEntry:
    """인메모리 캐시 조회/생성.

    - 키가 존재하고 만료되지 않았으면 히트 카운트 증가 후 반환
    - 키가 없거나 만료되었으면 새 엔트리 생성
    """
    now = time.time()

    if key in _cache_store:
        entry = _cache_store[key]
        # 만료 체크
        if now - entry.created_at < entry.ttl:
            entry.hit_count += 1
            # 토큰 절감 추정: 프롬프트 길이 기반 (한국어 ~2토큰/자)
            entry.tokens_saved += _estimate_tokens(entry.prompt_prefix)
            return entry
        # 만료된 엔트리 삭제
        del _cache_store[key]

    # 새 엔트리 생성
    entry = CacheEntry(
        key=key,
        prompt_prefix=prompt_prefix,
        created_at=now,
        ttl=ttl,
        hit_count=0,
        tokens_saved=0,
    )
    _cache_store[key] = entry
    return entry


def set_breakpoints(
    prompt: str, breakpoint_indices: list[int]
) -> list[CacheSegment]:
    """프롬프트를 브레이크포인트 인덱스로 재사용 구간 분할.

    breakpoint_indices: 프롬프트 문자열 내 분할 위치 (인덱스 목록)
    반환: CacheSegment 리스트
    """
    if not breakpoint_indices:
        # 인덱스가 없으면 전체를 하나의 세그먼트로
        cache_key = compute_cache_key([prompt])
        return [CacheSegment(start=0, end=len(prompt), cache_key=cache_key)]

    # 유효한 인덱스만 필터링 후 정렬
    valid_indices = sorted(
        idx for idx in breakpoint_indices if 0 < idx < len(prompt)
    )

    segments = []
    prev = 0
    for idx in valid_indices:
        segment_text = prompt[prev:idx]
        cache_key = compute_cache_key([segment_text])
        segments.append(CacheSegment(start=prev, end=idx, cache_key=cache_key))
        prev = idx

    # 마지막 세그먼트
    if prev < len(prompt):
        segment_text = prompt[prev:]
        cache_key = compute_cache_key([segment_text])
        segments.append(
            CacheSegment(start=prev, end=len(prompt), cache_key=cache_key)
        )

    return segments


def get_cache_stats() -> CacheStats:
    """캐시 히트율, 절감 비용 통계 반환."""
    total_entries = len(_cache_store)
    total_hits = sum(e.hit_count for e in _cache_store.values())
    total_tokens_saved = sum(e.tokens_saved for e in _cache_store.values())

    # 히트율: 히트 / (히트 + 엔트리 수). 엔트리 수 = 미스 횟수 근사치
    total_requests = total_hits + total_entries
    hit_rate = total_hits / total_requests if total_requests > 0 else 0.0

    estimated_cost_saved = total_tokens_saved * _COST_PER_TOKEN

    return CacheStats(
        total_entries=total_entries,
        total_hits=total_hits,
        total_tokens_saved=total_tokens_saved,
        hit_rate=hit_rate,
        estimated_cost_saved=estimated_cost_saved,
    )


def invalidate_cache(key: str = None) -> None:
    """특정 키 또는 전체 캐시 무효화.

    key가 None이면 전체 캐시 클리어.
    """
    if key is None:
        _cache_store.clear()
    else:
        _cache_store.pop(key, None)


def cleanup_expired() -> int:
    """만료된 캐시 엔트리 정리.

    반환: 제거된 엔트리 수
    """
    now = time.time()
    expired_keys = [
        k
        for k, entry in _cache_store.items()
        if now - entry.created_at >= entry.ttl
    ]
    for k in expired_keys:
        del _cache_store[k]
    return len(expired_keys)


def _estimate_tokens(text: str) -> int:
    """텍스트 토큰 수 추정 (한국어 ~2토큰/자, 영문 ~0.75토큰/단어)."""
    # 단순 추정: 문자 수 기반
    return max(1, len(text) // 2)
