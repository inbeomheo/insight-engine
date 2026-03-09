"""
비디오-코믹 서비스 — 비디오 장면을 만화 패널로 변환
"""

import uuid
from dataclasses import dataclass, field


@dataclass
class ComicPanel:
    """만화 패널"""
    panel_id: str
    description: str
    dialogue: str
    visual_style: str  # manga / western / minimal
    position: int
    size: str  # small / medium / large


@dataclass
class ComicStrip:
    """만화 스트립"""
    strip_id: str
    title: str
    panels: list[ComicPanel] = field(default_factory=list)
    page_layout: str = 'strip'


def create_strip(title: str, scenes: list[dict]) -> ComicStrip:
    """장면 → 패널 변환"""
    panels = []
    for i, scene in enumerate(scenes):
        panel = ComicPanel(
            panel_id=str(uuid.uuid4())[:8],
            description=scene.get('description', ''),
            dialogue=scene.get('dialogue', ''),
            visual_style=scene.get('visual_style', 'manga'),
            position=i,
            size=scene.get('size', 'medium')
        )
        panels.append(panel)

    layout = generate_layout(len(panels))

    return ComicStrip(
        strip_id=str(uuid.uuid4())[:8],
        title=title,
        panels=panels,
        page_layout=layout
    )


def add_dialogue(strip: ComicStrip, panel_id: str, dialogue: str) -> ComicStrip:
    """대사 추가"""
    new_panels = []
    found = False
    for p in strip.panels:
        if p.panel_id == panel_id:
            found = True
            new_panels.append(ComicPanel(
                panel_id=p.panel_id,
                description=p.description,
                dialogue=dialogue,
                visual_style=p.visual_style,
                position=p.position,
                size=p.size
            ))
        else:
            new_panels.append(p)

    if not found:
        raise ValueError(f"패널을 찾을 수 없습니다: {panel_id}")

    return ComicStrip(
        strip_id=strip.strip_id,
        title=strip.title,
        panels=new_panels,
        page_layout=strip.page_layout
    )


def reorder_panels(strip: ComicStrip, panel_ids: list[str]) -> ComicStrip:
    """패널 재정렬"""
    panel_map = {p.panel_id: p for p in strip.panels}
    new_panels = []

    for i, pid in enumerate(panel_ids):
        if pid not in panel_map:
            raise ValueError(f"패널을 찾을 수 없습니다: {pid}")
        p = panel_map[pid]
        new_panels.append(ComicPanel(
            panel_id=p.panel_id,
            description=p.description,
            dialogue=p.dialogue,
            visual_style=p.visual_style,
            position=i,
            size=p.size
        ))

    return ComicStrip(
        strip_id=strip.strip_id,
        title=strip.title,
        panels=new_panels,
        page_layout=strip.page_layout
    )


def generate_layout(panel_count: int) -> str:
    """패널 수 기반 레이아웃"""
    if panel_count <= 3:
        return 'strip'
    elif panel_count <= 6:
        return 'half-page'
    else:
        return 'full-page'
