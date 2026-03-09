"""
런타임 조립 서비스 — 모듈러 콘텐츠를 런타임에 동적 조립
"""

import uuid
from dataclasses import dataclass, field


# 유효한 모듈 유형
VALID_MODULE_TYPES = {"header", "body", "sidebar", "footer", "cta"}


@dataclass
class ContentModule:
    """콘텐츠 모듈"""
    module_id: str
    module_type: str  # header / body / sidebar / footer / cta
    content: str = ""
    priority: int = 0  # 높을수록 먼저 표시
    conditions: dict = field(default_factory=dict)


@dataclass
class AssembledPage:
    """조립된 페이지"""
    page_id: str
    modules: list[ContentModule] = field(default_factory=list)
    layout_type: str = "default"
    metadata: dict = field(default_factory=dict)


def register_module(
    modules: list[ContentModule], new_module: ContentModule
) -> list[ContentModule]:
    """모듈 등록

    동일 module_id가 이미 존재하면 교체.

    Args:
        modules: 기존 모듈 목록
        new_module: 새 모듈

    Returns:
        업데이트된 모듈 목록
    """
    # 동일 ID 교체
    for i, m in enumerate(modules):
        if m.module_id == new_module.module_id:
            modules[i] = new_module
            return modules

    modules.append(new_module)
    return modules


def evaluate_conditions(module: ContentModule, context: dict) -> bool:
    """조건 평가

    module.conditions의 모든 키-값이 context에 매칭되어야 통과.
    조건이 비어 있으면 항상 통과.

    Args:
        module: 평가할 모듈
        context: 런타임 컨텍스트

    Returns:
        조건 통과 여부
    """
    if not module.conditions:
        return True

    for key, expected in module.conditions.items():
        actual = context.get(key)
        if actual is None:
            return False

        # 리스트 조건: actual이 리스트 내 포함되면 통과
        if isinstance(expected, list):
            if actual not in expected:
                return False
        else:
            if actual != expected:
                return False

    return True


def assemble_page(
    modules: list[ContentModule],
    context: dict,
    layout_type: str = "default",
) -> AssembledPage:
    """조건 통과 모듈만 조립, priority 순 정렬

    Args:
        modules: 전체 모듈 목록
        context: 런타임 컨텍스트
        layout_type: 레이아웃 유형

    Returns:
        조립된 페이지
    """
    # 조건 통과 모듈 필터링
    passed = [m for m in modules if evaluate_conditions(m, context)]

    # priority 내림차순 정렬 (높은 우선순위 먼저)
    passed.sort(key=lambda m: m.priority, reverse=True)

    # 메타데이터 구성
    type_counts: dict[str, int] = {}
    for m in passed:
        type_counts[m.module_type] = type_counts.get(m.module_type, 0) + 1

    metadata = {
        "total_modules": len(passed),
        "module_types": type_counts,
        "context_keys": list(context.keys()),
    }

    return AssembledPage(
        page_id=str(uuid.uuid4()),
        modules=passed,
        layout_type=layout_type,
        metadata=metadata,
    )


def get_variants(
    modules: list[ContentModule], contexts: list[dict]
) -> list[AssembledPage]:
    """여러 컨텍스트별 변형 생성

    Args:
        modules: 전체 모듈 목록
        contexts: 컨텍스트 목록

    Returns:
        컨텍스트별 조립된 페이지 목록
    """
    return [
        assemble_page(modules, ctx, layout_type=f"variant-{i}")
        for i, ctx in enumerate(contexts)
    ]
