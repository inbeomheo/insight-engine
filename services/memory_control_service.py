"""메모리 컨트롤 서비스

대화 메모리를 관리합니다. 메모리 추가, 회상, 압축, 만료, 요약 기능을 제공합니다.
"""
import re
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import Counter


@dataclass
class MemoryEntry:
    """메모리 항목"""
    entry_id: str                       # 항목 고유 ID
    content: str                        # 메모리 내용
    importance: float = 0.5            # 중요도 (0~1)
    created_at: str = ''               # 생성 시각 (ISO 형식)
    expires_at: str | None = None      # 만료 시각 (None = 영구)
    tags: list[str] = field(default_factory=list)  # 태그 목록


@dataclass
class MemoryStore:
    """메모리 저장소"""
    store_id: str                       # 저장소 고유 ID
    entries: list[MemoryEntry] = field(default_factory=list)
    max_entries: int = 100              # 최대 항목 수


def _now_iso() -> str:
    """현재 시각 ISO 형식 문자열"""
    return datetime.utcnow().isoformat()


def _parse_iso(dt_str: str) -> datetime:
    """ISO 문자열 → datetime 변환"""
    # fromisoformat으로 처리
    return datetime.fromisoformat(dt_str)


def _extract_keywords(text: str) -> set[str]:
    """텍스트에서 키워드 추출 (2자 이상)"""
    tokens = re.findall(r'[\w가-힣]+', text.lower())
    return {t for t in tokens if len(t) >= 2}


def add_memory(
    store: MemoryStore,
    content: str,
    importance: float = 0.5,
    tags: list[str] | None = None,
    ttl_hours: int | None = None,
) -> MemoryStore:
    """메모리 추가

    Args:
        store: 대상 저장소
        content: 메모리 내용
        importance: 중요도 (0~1)
        tags: 태그 목록
        ttl_hours: 유효 시간 (None이면 영구)

    Returns:
        업데이트된 MemoryStore
    """
    importance = max(0.0, min(1.0, importance))
    now = _now_iso()
    expires_at = None
    if ttl_hours is not None and ttl_hours > 0:
        expires_at = (datetime.utcnow() + timedelta(hours=ttl_hours)).isoformat()

    entry = MemoryEntry(
        entry_id=uuid.uuid4().hex[:8],
        content=content,
        importance=importance,
        created_at=now,
        expires_at=expires_at,
        tags=tags or [],
    )

    new_entries = list(store.entries) + [entry]

    # max_entries 초과 시 중요도 낮은 것부터 제거
    if len(new_entries) > store.max_entries:
        new_entries.sort(key=lambda e: e.importance, reverse=True)
        new_entries = new_entries[:store.max_entries]

    return MemoryStore(
        store_id=store.store_id,
        entries=new_entries,
        max_entries=store.max_entries,
    )


def recall(
    store: MemoryStore,
    query: str,
    top_k: int = 5,
) -> list[MemoryEntry]:
    """키워드 매칭 기반 메모리 회상

    Args:
        store: 대상 저장소
        query: 검색 질의
        top_k: 상위 K개 반환

    Returns:
        관련 메모리 항목 목록 (관련성 내림차순)
    """
    if not store.entries or not query:
        return []

    query_keywords = _extract_keywords(query)
    if not query_keywords:
        # 키워드 없으면 중요도 순
        sorted_entries = sorted(store.entries, key=lambda e: e.importance, reverse=True)
        return sorted_entries[:top_k]

    scored: list[tuple[float, MemoryEntry]] = []
    for entry in store.entries:
        entry_keywords = _extract_keywords(entry.content)
        tag_keywords = {t.lower() for t in entry.tags}
        all_keywords = entry_keywords | tag_keywords

        if not all_keywords:
            scored.append((0.0, entry))
            continue

        intersection = query_keywords & all_keywords
        # 키워드 매칭 점수 + 중요도 가중치
        keyword_score = len(intersection) / len(query_keywords)
        combined_score = keyword_score * 0.7 + entry.importance * 0.3
        scored.append((combined_score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in scored[:top_k]]


def compress_memories(
    store: MemoryStore,
    target_count: int,
) -> MemoryStore:
    """메모리 압축

    중요도 낮은 메모리를 제거하여 target_count 이하로 줄입니다.

    Args:
        store: 대상 저장소
        target_count: 목표 항목 수

    Returns:
        압축된 MemoryStore
    """
    if len(store.entries) <= target_count:
        return MemoryStore(
            store_id=store.store_id,
            entries=list(store.entries),
            max_entries=store.max_entries,
        )

    # 중요도 내림차순 정렬 후 상위 target_count개 유지
    sorted_entries = sorted(store.entries, key=lambda e: e.importance, reverse=True)
    kept = sorted_entries[:target_count]

    return MemoryStore(
        store_id=store.store_id,
        entries=kept,
        max_entries=store.max_entries,
    )


def expire_memories(
    store: MemoryStore,
    current_time: str | None = None,
) -> MemoryStore:
    """만료 메모리 제거

    Args:
        store: 대상 저장소
        current_time: 현재 시각 (ISO 형식, None이면 실제 현재 시각)

    Returns:
        만료 항목 제거된 MemoryStore
    """
    now = _parse_iso(current_time) if current_time else datetime.utcnow()

    active: list[MemoryEntry] = []
    for entry in store.entries:
        if entry.expires_at is None:
            active.append(entry)
        else:
            try:
                exp = _parse_iso(entry.expires_at)
                if exp > now:
                    active.append(entry)
            except (ValueError, TypeError):
                # 파싱 실패 시 유지
                active.append(entry)

    return MemoryStore(
        store_id=store.store_id,
        entries=active,
        max_entries=store.max_entries,
    )


def summarize_store(store: MemoryStore) -> dict:
    """저장소 요약 통계

    Args:
        store: 대상 저장소

    Returns:
        요약 딕셔너리 (total_entries, tag_distribution, avg_importance, expired_count)
    """
    total = len(store.entries)

    if total == 0:
        return {
            'total_entries': 0,
            'tag_distribution': {},
            'avg_importance': 0.0,
            'expired_count': 0,
        }

    # 태그 분포
    tag_counter: Counter = Counter()
    for entry in store.entries:
        for tag in entry.tags:
            tag_counter[tag] += 1

    # 평균 중요도
    avg_importance = sum(e.importance for e in store.entries) / total

    # 만료 항목 수
    now = datetime.utcnow()
    expired = 0
    for entry in store.entries:
        if entry.expires_at:
            try:
                exp = _parse_iso(entry.expires_at)
                if exp <= now:
                    expired += 1
            except (ValueError, TypeError):
                pass

    return {
        'total_entries': total,
        'tag_distribution': dict(tag_counter),
        'avg_importance': round(avg_importance, 3),
        'expired_count': expired,
    }
