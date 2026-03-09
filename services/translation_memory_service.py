"""
번역 메모리 서비스

이전에 승인된 번역을 인메모리 저장소에 보관하고,
새 번역 요청 시 정확/유사 매치를 검색하여 재사용합니다.
순수 파이썬, 외부 API 호출 없음.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class TranslationEntry:
    """번역 메모리 항목."""
    entry_id: str
    source: str
    target: str
    source_lang: str
    target_lang: str
    created_at: str = ''
    use_count: int = 0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class TranslationMatch:
    """번역 메모리 검색 결과."""
    entry: TranslationEntry
    similarity: float
    exact: bool


# 인메모리 저장소
_memory_store: List[TranslationEntry] = []

# 유사 매치 임계값
_SIMILARITY_THRESHOLD = 0.7


def _tokenize(text: str) -> set:
    """텍스트를 단어 집합으로 변환합니다 (소문자 정규화)."""
    return set(text.lower().split())


def _jaccard_similarity(text_a: str, text_b: str) -> float:
    """두 텍스트 간 Jaccard 유사도를 계산합니다.

    Jaccard = |A ∩ B| / |A ∪ B|
    """
    set_a = _tokenize(text_a)
    set_b = _tokenize(text_b)

    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0

    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def store_translation(
    source: str,
    target: str,
    source_lang: str,
    target_lang: str,
) -> TranslationEntry:
    """번역 쌍을 메모리에 저장합니다.

    Args:
        source: 원문
        target: 번역문
        source_lang: 원문 언어 코드 (ko, en, ja 등)
        target_lang: 번역 언어 코드

    Returns:
        저장된 TranslationEntry
    """
    entry = TranslationEntry(
        entry_id=str(uuid.uuid4()),
        source=source.strip(),
        target=target.strip(),
        source_lang=source_lang.strip().lower(),
        target_lang=target_lang.strip().lower(),
    )
    _memory_store.append(entry)
    return entry


def lookup_memory(
    sentence: str,
    target_lang: str,
) -> Optional[TranslationMatch]:
    """번역 메모리에서 일치하는 항목을 검색합니다.

    정확 매치 우선, 없으면 Jaccard 유사도 기반 유사 매치를 반환합니다.

    Args:
        sentence: 번역할 원문
        target_lang: 목표 언어 코드

    Returns:
        TranslationMatch 또는 None (매치 없음)
    """
    if not sentence or not sentence.strip():
        return None

    sentence_stripped = sentence.strip()
    target_lang_lower = target_lang.strip().lower()

    best_match: Optional[TranslationMatch] = None
    best_similarity = 0.0

    for entry in _memory_store:
        # 목표 언어가 다르면 건너뜀
        if entry.target_lang != target_lang_lower:
            continue

        # 정확 매치 확인
        if entry.source == sentence_stripped:
            entry.use_count += 1
            return TranslationMatch(entry=entry, similarity=1.0, exact=True)

        # 유사 매치 확인
        similarity = _jaccard_similarity(entry.source, sentence_stripped)
        if similarity >= _SIMILARITY_THRESHOLD and similarity > best_similarity:
            best_similarity = similarity
            best_match = TranslationMatch(
                entry=entry,
                similarity=round(similarity, 4),
                exact=False,
            )

    if best_match:
        best_match.entry.use_count += 1

    return best_match


def get_memory_stats() -> dict:
    """번역 메모리 통계를 반환합니다.

    Returns:
        총 항목 수, 언어 쌍별 수, 가장 많이 사용된 항목 등
    """
    if not _memory_store:
        return {
            'total_entries': 0,
            'language_pairs': {},
            'most_used': None,
            'avg_use_count': 0.0,
        }

    # 언어 쌍별 집계
    lang_pairs: dict = {}
    most_used = _memory_store[0]

    for entry in _memory_store:
        pair_key = f"{entry.source_lang}->{entry.target_lang}"
        lang_pairs[pair_key] = lang_pairs.get(pair_key, 0) + 1
        if entry.use_count > most_used.use_count:
            most_used = entry

    total = len(_memory_store)
    total_uses = sum(e.use_count for e in _memory_store)

    return {
        'total_entries': total,
        'language_pairs': lang_pairs,
        'most_used': {
            'entry_id': most_used.entry_id,
            'source': most_used.source,
            'target': most_used.target,
            'use_count': most_used.use_count,
        },
        'avg_use_count': round(total_uses / total, 2) if total > 0 else 0.0,
    }


def clear_memory() -> int:
    """번역 메모리를 초기화합니다. 삭제된 항목 수를 반환합니다."""
    count = len(_memory_store)
    _memory_store.clear()
    return count
