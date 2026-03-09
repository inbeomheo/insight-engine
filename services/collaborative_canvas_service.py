"""
실시간 공동 캔버스 서비스 — 여러 사용자의 동시 편집 시뮬레이션
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class CanvasElement:
    """캔버스 요소"""
    element_id: str
    element_type: str  # text / shape / image / sticky_note
    content: str
    position: dict = field(default_factory=dict)  # {x, y}
    size: dict = field(default_factory=dict)       # {w, h}
    author: str = ""
    last_modified: str = ""


@dataclass
class Canvas:
    """캔버스"""
    canvas_id: str
    title: str
    elements: list = field(default_factory=list)       # list[CanvasElement]
    collaborators: list = field(default_factory=list)   # list[str]


VALID_ELEMENT_TYPES = {"text", "shape", "image", "sticky_note"}


def _new_id(prefix: str = "elem") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_canvas(title: str, owner: str) -> Canvas:
    """캔버스 생성

    Args:
        title: 캔버스 제목
        owner: 소유자 ID

    Returns:
        Canvas: 생성된 캔버스
    """
    if not title.strip():
        raise ValueError("캔버스 제목은 비어있을 수 없습니다.")

    return Canvas(
        canvas_id=_new_id("canvas"),
        title=title.strip(),
        elements=[],
        collaborators=[owner],
    )


def add_element(canvas: Canvas, element_config: dict) -> Canvas:
    """요소 추가

    Args:
        canvas: 대상 캔버스
        element_config: 요소 설정
            element_type, content, position ({x, y}), size ({w, h}), author

    Returns:
        Canvas: 요소가 추가된 캔버스
    """
    elem_type = element_config.get("element_type", "text")
    if elem_type not in VALID_ELEMENT_TYPES:
        raise ValueError(f"유효하지 않은 요소 타입: {elem_type}")

    author = element_config.get("author", "")

    elem = CanvasElement(
        element_id=element_config.get("element_id", _new_id()),
        element_type=elem_type,
        content=element_config.get("content", ""),
        position=element_config.get("position", {"x": 0, "y": 0}),
        size=element_config.get("size", {"w": 100, "h": 100}),
        author=author,
        last_modified=_timestamp(),
    )

    new_elements = list(canvas.elements) + [elem]

    # 새 작성자 자동 추가
    collaborators = list(canvas.collaborators)
    if author and author not in collaborators:
        collaborators.append(author)

    return Canvas(
        canvas_id=canvas.canvas_id,
        title=canvas.title,
        elements=new_elements,
        collaborators=collaborators,
    )


def move_element(canvas: Canvas, element_id: str, new_position: dict) -> Canvas:
    """요소 이동

    Args:
        canvas: 대상 캔버스
        element_id: 이동할 요소 ID
        new_position: 새 위치 {x, y}

    Returns:
        Canvas: 업데이트된 캔버스
    """
    found = False
    new_elements = []
    for elem in canvas.elements:
        if elem.element_id == element_id:
            found = True
            updated = CanvasElement(
                element_id=elem.element_id,
                element_type=elem.element_type,
                content=elem.content,
                position=new_position,
                size=elem.size,
                author=elem.author,
                last_modified=_timestamp(),
            )
            new_elements.append(updated)
        else:
            new_elements.append(elem)

    if not found:
        raise ValueError(f"존재하지 않는 요소 ID: {element_id}")

    return Canvas(
        canvas_id=canvas.canvas_id,
        title=canvas.title,
        elements=new_elements,
        collaborators=canvas.collaborators,
    )


def detect_overlap(canvas: Canvas) -> list:
    """겹치는 요소 쌍 탐지 (AABB 충돌 감지)

    Args:
        canvas: 대상 캔버스

    Returns:
        list[tuple]: 겹치는 (element_id_a, element_id_b) 쌍 목록
    """
    overlaps = []
    elements = canvas.elements

    for i in range(len(elements)):
        for j in range(i + 1, len(elements)):
            a = elements[i]
            b = elements[j]

            ax = a.position.get("x", 0)
            ay = a.position.get("y", 0)
            aw = a.size.get("w", 100)
            ah = a.size.get("h", 100)

            bx = b.position.get("x", 0)
            by = b.position.get("y", 0)
            bw = b.size.get("w", 100)
            bh = b.size.get("h", 100)

            # AABB 충돌 감지
            if (ax < bx + bw and ax + aw > bx and
                    ay < by + bh and ay + ah > by):
                overlaps.append((a.element_id, b.element_id))

    return overlaps


def get_contributor_stats(canvas: Canvas) -> dict:
    """기여자별 요소 수 통계

    Args:
        canvas: 대상 캔버스

    Returns:
        dict: {author: {count, element_types: [...]}}
    """
    stats = {}
    for elem in canvas.elements:
        author = elem.author or "anonymous"
        if author not in stats:
            stats[author] = {"count": 0, "element_types": []}
        stats[author]["count"] += 1
        if elem.element_type not in stats[author]["element_types"]:
            stats[author]["element_types"].append(elem.element_type)

    return stats
