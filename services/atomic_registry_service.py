"""원자 레지스트리 서비스

재사용 가능한 최소 콘텐츠 단위(fact, definition, quote, statistic, example)를
등록·검색·검증·사용 추적하는 레지스트리를 제공합니다.
"""
import re
import uuid
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class AtomicUnit:
    """원자 콘텐츠 단위"""
    unit_id: str                        # 단위 고유 ID
    content: str                        # 콘텐츠 내용
    unit_type: str                      # fact / definition / quote / statistic / example
    source: str = ''                    # 출처
    verified: bool = False              # 검증 완료 여부
    usage_count: int = 0               # 사용 횟수


@dataclass
class Registry:
    """원자 레지스트리"""
    registry_id: str                    # 레지스트리 고유 ID
    units: list[AtomicUnit] = field(default_factory=list)
    type_index: dict[str, list[str]] = field(default_factory=dict)  # 타입 → 단위 ID 인덱스


_VALID_UNIT_TYPES = {'fact', 'definition', 'quote', 'statistic', 'example'}


def _rebuild_type_index(units: list[AtomicUnit]) -> dict[str, list[str]]:
    """타입 → 단위 ID 인덱스 재구축"""
    idx: dict[str, list[str]] = defaultdict(list)
    for unit in units:
        idx[unit.unit_type].append(unit.unit_id)
    return dict(idx)


def _is_duplicate(units: list[AtomicUnit], content: str) -> bool:
    """중복 콘텐츠 체크 (정규화 후 비교)"""
    normalized = content.strip().lower()
    for unit in units:
        if unit.content.strip().lower() == normalized:
            return True
    return False


def register_unit(
    registry: Registry,
    content: str,
    unit_type: str,
    source: str = '',
) -> Registry:
    """원자 단위 등록

    중복 콘텐츠는 등록하지 않습니다.

    Args:
        registry: 대상 레지스트리
        content: 콘텐츠 내용
        unit_type: 단위 유형 (fact/definition/quote/statistic/example)
        source: 출처

    Returns:
        업데이트된 Registry

    Raises:
        ValueError: 유효하지 않은 unit_type
    """
    if unit_type not in _VALID_UNIT_TYPES:
        raise ValueError(f"유효하지 않은 단위 유형: {unit_type}. "
                         f"허용: {_VALID_UNIT_TYPES}")

    if not content or not content.strip():
        raise ValueError("콘텐츠가 비어있습니다.")

    # 중복 체크
    if _is_duplicate(registry.units, content):
        return registry

    unit = AtomicUnit(
        unit_id=uuid.uuid4().hex[:8],
        content=content.strip(),
        unit_type=unit_type,
        source=source,
        verified=False,
        usage_count=0,
    )

    new_units = list(registry.units) + [unit]
    new_index = _rebuild_type_index(new_units)

    return Registry(
        registry_id=registry.registry_id,
        units=new_units,
        type_index=new_index,
    )


def search_units(
    registry: Registry,
    query: str,
    unit_type: str | None = None,
) -> list[AtomicUnit]:
    """원자 단위 검색

    키워드 매칭 + 타입 필터로 검색합니다.

    Args:
        registry: 대상 레지스트리
        query: 검색 키워드
        unit_type: 타입 필터 (None이면 전체)

    Returns:
        매칭된 AtomicUnit 목록
    """
    candidates = registry.units

    # 타입 필터
    if unit_type:
        candidates = [u for u in candidates if u.unit_type == unit_type]

    # 키워드 매칭
    if not query or not query.strip():
        return candidates

    query_lower = query.strip().lower()
    query_tokens = set(re.findall(r'[\w가-힣]+', query_lower))

    scored: list[tuple[float, AtomicUnit]] = []
    for unit in candidates:
        content_lower = unit.content.lower()

        # 전체 쿼리 포함 여부
        if query_lower in content_lower:
            scored.append((1.0, unit))
            continue

        # 토큰 매칭
        content_tokens = set(re.findall(r'[\w가-힣]+', content_lower))
        if query_tokens:
            match_ratio = len(query_tokens & content_tokens) / len(query_tokens)
            if match_ratio > 0:
                scored.append((match_ratio, unit))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [unit for _, unit in scored]


def verify_unit(registry: Registry, unit_id: str) -> Registry:
    """원자 단위 검증 완료 처리

    Args:
        registry: 대상 레지스트리
        unit_id: 대상 단위 ID

    Returns:
        업데이트된 Registry

    Raises:
        ValueError: unit_id가 존재하지 않을 때
    """
    found = False
    new_units: list[AtomicUnit] = []
    for unit in registry.units:
        if unit.unit_id == unit_id:
            found = True
            new_units.append(AtomicUnit(
                unit_id=unit.unit_id,
                content=unit.content,
                unit_type=unit.unit_type,
                source=unit.source,
                verified=True,
                usage_count=unit.usage_count,
            ))
        else:
            new_units.append(unit)

    if not found:
        raise ValueError(f"단위 ID '{unit_id}'를 찾을 수 없습니다.")

    return Registry(
        registry_id=registry.registry_id,
        units=new_units,
        type_index=_rebuild_type_index(new_units),
    )


def get_most_used(registry: Registry, top_k: int = 5) -> list[AtomicUnit]:
    """사용 빈도 상위 단위 조회

    Args:
        registry: 대상 레지스트리
        top_k: 상위 K개

    Returns:
        사용 빈도 내림차순 AtomicUnit 목록
    """
    sorted_units = sorted(
        registry.units,
        key=lambda u: u.usage_count,
        reverse=True,
    )
    return sorted_units[:top_k]


def increment_usage(registry: Registry, unit_id: str) -> Registry:
    """사용 횟수 증가

    Args:
        registry: 대상 레지스트리
        unit_id: 대상 단위 ID

    Returns:
        업데이트된 Registry

    Raises:
        ValueError: unit_id가 존재하지 않을 때
    """
    found = False
    new_units: list[AtomicUnit] = []
    for unit in registry.units:
        if unit.unit_id == unit_id:
            found = True
            new_units.append(AtomicUnit(
                unit_id=unit.unit_id,
                content=unit.content,
                unit_type=unit.unit_type,
                source=unit.source,
                verified=unit.verified,
                usage_count=unit.usage_count + 1,
            ))
        else:
            new_units.append(unit)

    if not found:
        raise ValueError(f"단위 ID '{unit_id}'를 찾을 수 없습니다.")

    return Registry(
        registry_id=registry.registry_id,
        units=new_units,
        type_index=_rebuild_type_index(new_units),
    )
