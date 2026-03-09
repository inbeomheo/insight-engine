"""프롬프트 캐싱 서비스 테스트"""
import time
import pytest
from services.prompt_cache_service import (
    CacheEntry,
    CacheSegment,
    CacheStats,
    compute_cache_key,
    get_or_create_cache,
    set_breakpoints,
    get_cache_stats,
    invalidate_cache,
    cleanup_expired,
    _cache_store,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """각 테스트 전후 캐시 초기화."""
    _cache_store.clear()
    yield
    _cache_store.clear()


class TestComputeCacheKey:
    """compute_cache_key 함수 테스트"""

    def test_deterministic(self):
        """같은 입력 → 같은 키"""
        parts = ["시스템 프롬프트", "사용자 지침"]
        key1 = compute_cache_key(parts)
        key2 = compute_cache_key(parts)
        assert key1 == key2

    def test_different_input(self):
        """다른 입력 → 다른 키"""
        key1 = compute_cache_key(["프롬프트 A"])
        key2 = compute_cache_key(["프롬프트 B"])
        assert key1 != key2

    def test_sha256_format(self):
        """SHA256 해시 형식(64자 hex) 확인"""
        key = compute_cache_key(["테스트"])
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    def test_order_matters(self):
        """파트 순서가 다르면 다른 키"""
        key1 = compute_cache_key(["A", "B"])
        key2 = compute_cache_key(["B", "A"])
        assert key1 != key2


class TestGetOrCreateCache:
    """get_or_create_cache 함수 테스트"""

    def test_new_cache(self):
        """새 캐시 생성"""
        entry = get_or_create_cache("key1", "프롬프트 prefix", ttl=3600)
        assert isinstance(entry, CacheEntry)
        assert entry.key == "key1"
        assert entry.prompt_prefix == "프롬프트 prefix"
        assert entry.hit_count == 0
        assert entry.tokens_saved == 0

    def test_existing_cache_hit(self):
        """기존 캐시 히트 → hit_count 증가"""
        get_or_create_cache("key1", "prefix", ttl=3600)
        entry = get_or_create_cache("key1", "prefix", ttl=3600)
        assert entry.hit_count == 1

    def test_expired_cache_recreated(self):
        """만료 캐시 → 새로 생성"""
        # TTL 0초로 설정하여 즉시 만료
        entry1 = get_or_create_cache("key1", "old prefix", ttl=0)
        entry1_created = entry1.created_at

        # 약간의 시간 경과 보장
        time.sleep(0.01)

        entry2 = get_or_create_cache("key1", "new prefix", ttl=3600)
        # 새로 생성되었으므로 hit_count는 0
        assert entry2.hit_count == 0
        assert entry2.prompt_prefix == "new prefix"
        assert entry2.created_at > entry1_created

    def test_hit_count_increment(self):
        """연속 히트 시 카운트 누적"""
        get_or_create_cache("key1", "prefix", ttl=3600)
        for _ in range(5):
            get_or_create_cache("key1", "prefix", ttl=3600)

        entry = _cache_store["key1"]
        assert entry.hit_count == 5

    def test_tokens_saved_increment(self):
        """히트 시 tokens_saved 누적"""
        get_or_create_cache("key1", "테스트 프롬프트", ttl=3600)
        get_or_create_cache("key1", "테스트 프롬프트", ttl=3600)

        entry = _cache_store["key1"]
        assert entry.tokens_saved > 0


class TestSetBreakpoints:
    """set_breakpoints 함수 테스트"""

    def test_basic_breakpoints(self):
        """기본 브레이크포인트 분할"""
        prompt = "AAABBBCCC"
        segments = set_breakpoints(prompt, [3, 6])

        assert len(segments) == 3
        assert isinstance(segments[0], CacheSegment)
        assert segments[0].start == 0
        assert segments[0].end == 3
        assert segments[1].start == 3
        assert segments[1].end == 6
        assert segments[2].start == 6
        assert segments[2].end == 9

    def test_empty_breakpoints(self):
        """빈 인덱스 → 전체를 하나의 세그먼트로"""
        prompt = "전체 프롬프트"
        segments = set_breakpoints(prompt, [])

        assert len(segments) == 1
        assert segments[0].start == 0
        assert segments[0].end == len(prompt)

    def test_unsorted_breakpoints(self):
        """정렬되지 않은 인덱스도 올바르게 처리"""
        prompt = "AABBCCDD"
        segments = set_breakpoints(prompt, [6, 2, 4])

        assert len(segments) == 4
        # 정렬된 순서로 분할되어야 함
        assert segments[0].end == 2
        assert segments[1].end == 4
        assert segments[2].end == 6
        assert segments[3].end == 8

    def test_invalid_breakpoints_filtered(self):
        """범위 밖 인덱스는 무시"""
        prompt = "ABC"
        # 0과 len(prompt) 이상은 무효
        segments = set_breakpoints(prompt, [0, 3, 5, -1])

        # 유효 인덱스 없음 → 마지막 세그먼트만
        assert len(segments) == 1
        assert segments[0].start == 0
        assert segments[0].end == 3

    def test_segment_cache_keys_differ(self):
        """다른 세그먼트는 다른 캐시 키"""
        prompt = "AAABBB"
        segments = set_breakpoints(prompt, [3])

        assert segments[0].cache_key != segments[1].cache_key


class TestGetCacheStats:
    """get_cache_stats 함수 테스트"""

    def test_empty_stats(self):
        """빈 캐시 통계"""
        stats = get_cache_stats()
        assert isinstance(stats, CacheStats)
        assert stats.total_entries == 0
        assert stats.total_hits == 0
        assert stats.total_tokens_saved == 0
        assert stats.hit_rate == 0.0
        assert stats.estimated_cost_saved == 0.0

    def test_stats_accuracy(self):
        """캐시 사용 후 통계 정확성"""
        # 2개 엔트리 생성, 하나에 3번 히트
        get_or_create_cache("k1", "프롬프트 A", ttl=3600)
        get_or_create_cache("k2", "프롬프트 B", ttl=3600)

        for _ in range(3):
            get_or_create_cache("k1", "프롬프트 A", ttl=3600)

        stats = get_cache_stats()
        assert stats.total_entries == 2
        assert stats.total_hits == 3
        assert stats.total_tokens_saved > 0
        assert stats.hit_rate > 0.0
        assert stats.estimated_cost_saved > 0.0

    def test_hit_rate_calculation(self):
        """히트율 계산 검증: hits / (hits + entries)"""
        get_or_create_cache("k1", "p", ttl=3600)
        # 2번 히트
        get_or_create_cache("k1", "p", ttl=3600)
        get_or_create_cache("k1", "p", ttl=3600)

        stats = get_cache_stats()
        # hits=2, entries=1, rate = 2/(2+1) ≈ 0.6667
        assert abs(stats.hit_rate - 2.0 / 3.0) < 0.01


class TestInvalidateCache:
    """invalidate_cache 함수 테스트"""

    def test_specific_key(self):
        """특정 키 무효화"""
        get_or_create_cache("k1", "p1", ttl=3600)
        get_or_create_cache("k2", "p2", ttl=3600)

        invalidate_cache("k1")

        assert "k1" not in _cache_store
        assert "k2" in _cache_store

    def test_all_cache(self):
        """전체 무효화"""
        get_or_create_cache("k1", "p1", ttl=3600)
        get_or_create_cache("k2", "p2", ttl=3600)

        invalidate_cache()

        assert len(_cache_store) == 0

    def test_nonexistent_key(self):
        """존재하지 않는 키 무효화 → 에러 없음"""
        invalidate_cache("nonexistent")
        # 예외 발생하지 않아야 함


class TestCleanupExpired:
    """cleanup_expired 함수 테스트"""

    def test_cleanup_removes_expired(self):
        """만료 엔트리 제거"""
        # TTL 0으로 즉시 만료
        get_or_create_cache("expired1", "p1", ttl=0)
        get_or_create_cache("expired2", "p2", ttl=0)
        get_or_create_cache("valid", "p3", ttl=3600)

        time.sleep(0.01)

        removed = cleanup_expired()
        assert removed == 2
        assert "expired1" not in _cache_store
        assert "expired2" not in _cache_store
        assert "valid" in _cache_store

    def test_cleanup_returns_count(self):
        """제거된 수 반환"""
        removed = cleanup_expired()
        assert removed == 0

    def test_cleanup_no_valid_removed(self):
        """유효 엔트리는 제거하지 않음"""
        get_or_create_cache("valid1", "p1", ttl=3600)
        get_or_create_cache("valid2", "p2", ttl=3600)

        removed = cleanup_expired()
        assert removed == 0
        assert len(_cache_store) == 2
