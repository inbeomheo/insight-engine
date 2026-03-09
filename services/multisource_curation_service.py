"""
멀티소스 큐레이션 서비스.

여러 출처의 콘텐츠를 수집, 필터링, 큐레이션한다.
"""

from dataclasses import dataclass, field
import uuid
from datetime import datetime


@dataclass
class CurationSource:
    """큐레이션 출처"""
    source_id: str = ""
    name: str = ""
    source_type: str = "blog"  # blog / news / paper / video
    reliability: float = 0.5   # 0.0 ~ 1.0


@dataclass
class CuratedItem:
    """큐레이션 항목"""
    item_id: str = ""
    title: str = ""
    summary: str = ""
    source: CurationSource = None
    relevance: float = 0.0
    added_at: str = ""


@dataclass
class CurationCollection:
    """큐레이션 컬렉션"""
    collection_id: str = ""
    topic: str = ""
    items: list = field(default_factory=list)


def add_source(
    sources: list,
    name: str,
    source_type: str,
    reliability: float
) -> list:
    """출처 추가"""
    new_source = CurationSource(
        source_id=str(uuid.uuid4()),
        name=name,
        source_type=source_type,
        reliability=max(0.0, min(1.0, reliability)),
    )
    return list(sources) + [new_source]


def _compute_relevance(topic: str, title: str, summary: str) -> float:
    """토픽과 콘텐츠의 관련성 점수 계산 (키워드 겹침 기반)"""
    topic_words = set(topic.lower().split())
    content_words = set((title + " " + summary).lower().split())

    if not topic_words:
        return 0.0

    overlap = len(topic_words & content_words)
    return min(1.0, overlap / len(topic_words))


def curate(
    topic: str,
    candidates: list,
    sources: list
) -> CurationCollection:
    """
    관련성 + 신뢰도 기반 큐레이션.

    candidates: [{"title": str, "summary": str, "source_id": str}, ...]
    """
    source_map = {s.source_id: s for s in sources}
    items = []

    for candidate in candidates:
        source = source_map.get(candidate.get("source_id"))
        if not source:
            continue

        relevance = _compute_relevance(
            topic,
            candidate.get("title", ""),
            candidate.get("summary", ""),
        )

        # 최소 관련성 필터 (0.1 이상만)
        if relevance < 0.1:
            continue

        item = CuratedItem(
            item_id=str(uuid.uuid4()),
            title=candidate.get("title", ""),
            summary=candidate.get("summary", ""),
            source=source,
            relevance=round(relevance, 4),
            added_at=datetime.utcnow().isoformat(),
        )
        items.append(item)

    return CurationCollection(
        collection_id=str(uuid.uuid4()),
        topic=topic,
        items=items,
    )


def rank_items(collection: CurationCollection) -> list:
    """
    복합 점수 정렬.

    점수 = relevance * 0.6 + source.reliability * 0.4
    """
    def composite_score(item):
        reliability = item.source.reliability if item.source else 0.0
        return item.relevance * 0.6 + reliability * 0.4

    sorted_items = sorted(collection.items, key=composite_score, reverse=True)
    return sorted_items


def deduplicate(collection: CurationCollection) -> CurationCollection:
    """
    제목 유사도 기반 중복 제거.

    제목이 동일하거나 80% 이상 겹치는 항목을 제거한다.
    """
    if not collection.items:
        return collection

    unique_items = []
    seen_titles = []

    for item in collection.items:
        title_words = set(item.title.lower().split())
        is_duplicate = False

        for seen in seen_titles:
            if not title_words or not seen:
                continue
            overlap = len(title_words & seen)
            similarity = overlap / max(len(title_words), len(seen))

            if similarity >= 0.8:
                is_duplicate = True
                break

        if not is_duplicate:
            unique_items.append(item)
            seen_titles.append(title_words)

    return CurationCollection(
        collection_id=collection.collection_id,
        topic=collection.topic,
        items=unique_items,
    )
