"""
제너레이티브 UI 서비스 — 콘텐츠에 맞는 UI 레이아웃 메타데이터 생성
"""

import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class UIComponent:
    """UI 컴포넌트"""
    component_id: str
    component_type: str  # text / image / chart / card / list / cta
    content: str
    style: dict = field(default_factory=dict)
    position: dict = field(default_factory=dict)  # row, col, span


@dataclass
class UILayout:
    """UI 레이아웃"""
    layout_id: str
    title: str
    components: list = field(default_factory=list)  # list[UIComponent]
    grid_cols: int = 1
    theme: str = "default"


# 콘텐츠 타입별 기본 그리드 설정
_CONTENT_TYPE_GRID = {
    "blog": 2,
    "dashboard": 3,
    "landing": 1,
    "article": 2,
    "report": 3,
}

# 콘텐츠 타입별 기본 컴포넌트 구성
_CONTENT_TYPE_COMPONENTS = {
    "blog": [
        ("text", "제목 영역"),
        ("image", "대표 이미지"),
        ("text", "본문 콘텐츠"),
        ("cta", "관련 글 보기"),
    ],
    "dashboard": [
        ("chart", "주요 지표 차트"),
        ("card", "요약 카드"),
        ("list", "최근 활동"),
        ("chart", "트렌드 차트"),
    ],
    "landing": [
        ("text", "히어로 섹션"),
        ("image", "제품 이미지"),
        ("card", "기능 소개"),
        ("cta", "시작하기"),
    ],
}

VALID_COMPONENT_TYPES = {"text", "image", "chart", "card", "list", "cta"}


def _new_id(prefix: str = "comp") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def generate_layout(content: str, content_type: str = "blog") -> UILayout:
    """콘텐츠 타입별 레이아웃 생성

    Args:
        content: 레이아웃에 포함할 콘텐츠 텍스트
        content_type: blog / dashboard / landing 등

    Returns:
        UILayout: 생성된 레이아웃
    """
    grid_cols = _CONTENT_TYPE_GRID.get(content_type, 1)
    component_configs = _CONTENT_TYPE_COMPONENTS.get(
        content_type,
        [("text", "본문"), ("cta", "더 보기")],
    )

    components = []
    for idx, (comp_type, label) in enumerate(component_configs):
        row = idx // grid_cols
        col = idx % grid_cols
        comp = UIComponent(
            component_id=_new_id(),
            component_type=comp_type,
            content=f"{label}: {content[:80]}" if comp_type == "text" else label,
            style={"padding": "8px"},
            position={"row": row, "col": col, "span": 1},
        )
        components.append(comp)

    return UILayout(
        layout_id=_new_id("layout"),
        title=f"{content_type} 레이아웃",
        components=components,
        grid_cols=grid_cols,
        theme="default",
    )


def add_component(
    layout: UILayout,
    component_type: str,
    content: str,
    style: Optional[dict] = None,
) -> UILayout:
    """레이아웃에 컴포넌트 추가

    Args:
        layout: 대상 레이아웃
        component_type: 컴포넌트 유형
        content: 콘텐츠 텍스트
        style: 스타일 딕셔너리 (선택)

    Returns:
        UILayout: 컴포넌트가 추가된 레이아웃
    """
    if component_type not in VALID_COMPONENT_TYPES:
        raise ValueError(f"유효하지 않은 컴포넌트 타입: {component_type}")

    # 다음 위치 계산
    existing_count = len(layout.components)
    row = existing_count // layout.grid_cols
    col = existing_count % layout.grid_cols

    new_comp = UIComponent(
        component_id=_new_id(),
        component_type=component_type,
        content=content,
        style=style or {"padding": "8px"},
        position={"row": row, "col": col, "span": 1},
    )

    new_components = list(layout.components) + [new_comp]
    return UILayout(
        layout_id=layout.layout_id,
        title=layout.title,
        components=new_components,
        grid_cols=layout.grid_cols,
        theme=layout.theme,
    )


def reorder_components(layout: UILayout, order: list) -> UILayout:
    """컴포넌트 재정렬

    Args:
        layout: 대상 레이아웃
        order: component_id 목록 (새 순서)

    Returns:
        UILayout: 재정렬된 레이아웃
    """
    comp_map = {c.component_id: c for c in layout.components}

    # order에 없는 ID가 있으면 에러
    for cid in order:
        if cid not in comp_map:
            raise ValueError(f"존재하지 않는 컴포넌트 ID: {cid}")

    # 재정렬 + 위치 재계산
    reordered = []
    for idx, cid in enumerate(order):
        comp = comp_map[cid]
        row = idx // layout.grid_cols
        col = idx % layout.grid_cols
        updated = UIComponent(
            component_id=comp.component_id,
            component_type=comp.component_type,
            content=comp.content,
            style=comp.style,
            position={"row": row, "col": col, "span": 1},
        )
        reordered.append(updated)

    # order에 포함되지 않은 컴포넌트는 뒤에 유지
    remaining = [c for c in layout.components if c.component_id not in order]
    for comp in remaining:
        idx = len(reordered)
        row = idx // layout.grid_cols
        col = idx % layout.grid_cols
        updated = UIComponent(
            component_id=comp.component_id,
            component_type=comp.component_type,
            content=comp.content,
            style=comp.style,
            position={"row": row, "col": col, "span": 1},
        )
        reordered.append(updated)

    return UILayout(
        layout_id=layout.layout_id,
        title=layout.title,
        components=reordered,
        grid_cols=layout.grid_cols,
        theme=layout.theme,
    )


def export_layout_spec(layout: UILayout) -> dict:
    """레이아웃을 JSON 스펙으로 내보내기

    Args:
        layout: 대상 레이아웃

    Returns:
        dict: JSON 직렬화 가능한 스펙
    """
    return {
        "layout_id": layout.layout_id,
        "title": layout.title,
        "grid_cols": layout.grid_cols,
        "theme": layout.theme,
        "components": [asdict(c) for c in layout.components],
        "component_count": len(layout.components),
    }
