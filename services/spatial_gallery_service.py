"""
공간 갤러리 서비스 — 3D 갤러리 공간에 콘텐츠 배치
"""

import uuid
import math
from dataclasses import dataclass, field


@dataclass
class GalleryItem:
    """갤러리 아이템"""
    item_id: str
    title: str
    content_type: str  # image / text / video
    position_3d: dict  # x, y, z
    rotation: float
    scale: float


@dataclass
class Gallery:
    """갤러리"""
    gallery_id: str
    title: str
    items: list[GalleryItem] = field(default_factory=list)
    dimensions: dict = field(default_factory=lambda: {'width': 10, 'height': 5, 'depth': 10})


def create_gallery(title: str, dimensions: dict) -> Gallery:
    """갤러리 생성"""
    return Gallery(
        gallery_id=str(uuid.uuid4())[:8],
        title=title,
        dimensions=dimensions
    )


def place_item(gallery: Gallery, item_config: dict) -> Gallery:
    """아이템 배치"""
    item = GalleryItem(
        item_id=str(uuid.uuid4())[:8],
        title=item_config.get('title', ''),
        content_type=item_config.get('content_type', 'image'),
        position_3d=item_config.get('position_3d', {'x': 0, 'y': 0, 'z': 0}),
        rotation=item_config.get('rotation', 0.0),
        scale=item_config.get('scale', 1.0)
    )
    new_items = gallery.items + [item]
    return Gallery(
        gallery_id=gallery.gallery_id,
        title=gallery.title,
        items=new_items,
        dimensions=gallery.dimensions
    )


def auto_arrange(gallery: Gallery, layout: str = 'wall') -> Gallery:
    """자동 배치 — wall / floating / circular"""
    if not gallery.items:
        return gallery

    count = len(gallery.items)
    w = gallery.dimensions.get('width', 10)
    h = gallery.dimensions.get('height', 5)
    d = gallery.dimensions.get('depth', 10)

    new_items = []

    if layout == 'wall':
        # 벽면 배치 — x 균등 분배, y 중앙, z = 0
        spacing = w / max(count + 1, 1)
        for i, item in enumerate(gallery.items):
            new_items.append(GalleryItem(
                item_id=item.item_id,
                title=item.title,
                content_type=item.content_type,
                position_3d={'x': round(spacing * (i + 1), 2), 'y': round(h / 2, 2), 'z': 0},
                rotation=0.0,
                scale=item.scale
            ))

    elif layout == 'floating':
        # 부유 배치 — 3D 공간 분산
        for i, item in enumerate(gallery.items):
            x = round((i % 3 + 1) * w / 4, 2)
            y = round((i % 2 + 1) * h / 3, 2)
            z = round((i // 3 + 1) * d / (count // 3 + 2), 2)
            new_items.append(GalleryItem(
                item_id=item.item_id,
                title=item.title,
                content_type=item.content_type,
                position_3d={'x': x, 'y': y, 'z': z},
                rotation=round(i * 15.0, 2),
                scale=item.scale
            ))

    elif layout == 'circular':
        # 원형 배치
        radius = min(w, d) / 3
        center_x = w / 2
        center_z = d / 2
        for i, item in enumerate(gallery.items):
            angle = 2 * math.pi * i / count
            x = round(center_x + radius * math.cos(angle), 2)
            z = round(center_z + radius * math.sin(angle), 2)
            rotation = round(math.degrees(angle), 2)
            new_items.append(GalleryItem(
                item_id=item.item_id,
                title=item.title,
                content_type=item.content_type,
                position_3d={'x': x, 'y': round(h / 2, 2), 'z': z},
                rotation=rotation,
                scale=item.scale
            ))
    else:
        new_items = list(gallery.items)

    return Gallery(
        gallery_id=gallery.gallery_id,
        title=gallery.title,
        items=new_items,
        dimensions=gallery.dimensions
    )


def check_collisions(gallery: Gallery, min_distance: float = 1.0) -> list[tuple]:
    """충돌 감지 — 최소 거리 이내 아이템 쌍"""
    collisions = []
    items = gallery.items

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a = items[i].position_3d
            b = items[j].position_3d
            dist = math.sqrt(
                (a.get('x', 0) - b.get('x', 0)) ** 2 +
                (a.get('y', 0) - b.get('y', 0)) ** 2 +
                (a.get('z', 0) - b.get('z', 0)) ** 2
            )
            if dist < min_distance:
                collisions.append((items[i].item_id, items[j].item_id))

    return collisions
