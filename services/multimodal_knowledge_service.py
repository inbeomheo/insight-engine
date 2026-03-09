"""멀티모달 지식 서비스

텍스트/이미지/오디오/비디오 메타데이터를 통합 관리합니다.
태그 기반 검색, 크로스모달 연결, 통계 조회 기능을 제공합니다.
"""
import uuid
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class KnowledgeItem:
    """지식 항목"""
    item_id: str                        # 항목 고유 ID
    modality: str                       # text / image / audio / video
    content: str                        # 콘텐츠 텍스트 (또는 파일 경로/설명)
    metadata: dict = field(default_factory=dict)  # 메타데이터
    tags: list[str] = field(default_factory=list)  # 태그 목록
    created_at: str = ''               # 생성 시각 (ISO 형식)


@dataclass
class KnowledgeBase:
    """지식 베이스"""
    kb_id: str                          # 지식 베이스 고유 ID
    items: list[KnowledgeItem] = field(default_factory=list)
    index: dict[str, list[str]] = field(default_factory=dict)  # 태그 → 아이템 ID 인덱스


_VALID_MODALITIES = {'text', 'image', 'audio', 'video'}


def _rebuild_index(items: list[KnowledgeItem]) -> dict[str, list[str]]:
    """태그 → 아이템 ID 인덱스 재구축"""
    idx: dict[str, list[str]] = defaultdict(list)
    for item in items:
        for tag in item.tags:
            tag_lower = tag.lower()
            idx[tag_lower].append(item.item_id)
    return dict(idx)


def add_item(
    kb: KnowledgeBase,
    modality: str,
    content: str,
    metadata: dict | None = None,
    tags: list[str] | None = None,
) -> KnowledgeBase:
    """지식 항목 추가 + 인덱스 업데이트

    Args:
        kb: 대상 지식 베이스
        modality: 모달리티 (text/image/audio/video)
        content: 콘텐츠 내용
        metadata: 메타데이터
        tags: 태그 목록

    Returns:
        업데이트된 KnowledgeBase
    """
    if modality not in _VALID_MODALITIES:
        raise ValueError(f"유효하지 않은 모달리티: {modality}. "
                         f"허용: {_VALID_MODALITIES}")

    item = KnowledgeItem(
        item_id=uuid.uuid4().hex[:8],
        modality=modality,
        content=content,
        metadata=metadata or {},
        tags=tags or [],
        created_at=datetime.utcnow().isoformat(),
    )

    new_items = list(kb.items) + [item]
    new_index = _rebuild_index(new_items)

    return KnowledgeBase(
        kb_id=kb.kb_id,
        items=new_items,
        index=new_index,
    )


def search_by_tags(
    kb: KnowledgeBase,
    tags: list[str],
    match_mode: str = 'AND',
) -> list[KnowledgeItem]:
    """태그 기반 검색

    Args:
        kb: 대상 지식 베이스
        tags: 검색 태그 목록
        match_mode: 'AND' (모든 태그 일치) / 'OR' (하나 이상 일치)

    Returns:
        매칭된 KnowledgeItem 목록
    """
    if not tags:
        return list(kb.items)

    search_tags = {t.lower() for t in tags}

    results: list[KnowledgeItem] = []
    for item in kb.items:
        item_tags = {t.lower() for t in item.tags}

        if match_mode.upper() == 'AND':
            if search_tags.issubset(item_tags):
                results.append(item)
        else:  # OR
            if search_tags & item_tags:
                results.append(item)

    return results


def cross_modal_link(
    kb: KnowledgeBase,
    item_id_a: str,
    item_id_b: str,
    relation: str = 'related',
) -> dict:
    """크로스모달 연결 정보 생성

    두 아이템 간의 크로스모달 연결을 기술하는 딕셔너리를 반환합니다.

    Args:
        kb: 대상 지식 베이스
        item_id_a: 첫 번째 아이템 ID
        item_id_b: 두 번째 아이템 ID
        relation: 관계 유형

    Returns:
        연결 정보 딕셔너리

    Raises:
        ValueError: 아이템 ID가 존재하지 않을 때
    """
    item_map = {item.item_id: item for item in kb.items}

    if item_id_a not in item_map:
        raise ValueError(f"아이템 ID '{item_id_a}'를 찾을 수 없습니다.")
    if item_id_b not in item_map:
        raise ValueError(f"아이템 ID '{item_id_b}'를 찾을 수 없습니다.")

    a = item_map[item_id_a]
    b = item_map[item_id_b]

    return {
        'link_id': uuid.uuid4().hex[:8],
        'item_a': item_id_a,
        'item_b': item_id_b,
        'modality_a': a.modality,
        'modality_b': b.modality,
        'relation': relation,
        'is_cross_modal': a.modality != b.modality,
    }


def get_statistics(kb: KnowledgeBase) -> dict:
    """모달리티별 통계

    Args:
        kb: 대상 지식 베이스

    Returns:
        통계 딕셔너리 (total, by_modality, tag_count, unique_tags)
    """
    modality_count: dict[str, int] = defaultdict(int)
    all_tags: set[str] = set()

    for item in kb.items:
        modality_count[item.modality] += 1
        for tag in item.tags:
            all_tags.add(tag.lower())

    return {
        'total': len(kb.items),
        'by_modality': dict(modality_count),
        'tag_count': len(all_tags),
        'unique_tags': sorted(all_tags),
    }
