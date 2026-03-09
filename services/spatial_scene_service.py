"""
2D→공간 장면 변환 서비스.

2D 레이아웃을 3D 공간 좌표로 변환한다.
"""

from dataclasses import dataclass, field
import math
import uuid


@dataclass
class Object2D:
    """2D 오브젝트"""
    object_id: str = ""
    name: str = ""
    x: float = 0.0
    y: float = 0.0
    width: float = 1.0
    height: float = 1.0
    layer: int = 0


@dataclass
class Object3D:
    """3D 오브젝트"""
    object_id: str = ""
    name: str = ""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    scale: float = 1.0


@dataclass
class SpatialScene:
    """공간 장면"""
    scene_id: str = ""
    objects: list = field(default_factory=list)
    camera_position: dict = field(default_factory=lambda: {"x": 0, "y": 0, "z": 10})


def convert_to_3d(
    objects_2d: list,
    depth_scale: float = 2.0
) -> SpatialScene:
    """
    레이어 기반 깊이 변환.

    layer 값이 클수록 더 먼 깊이(z)에 배치한다.
    """
    objects_3d = []

    for obj in objects_2d:
        # z 좌표: 레이어 × 깊이 스케일
        z = -obj.layer * depth_scale

        # 스케일: 먼 오브젝트일수록 작게 (원근감)
        scale = max(0.3, 1.0 - obj.layer * 0.15)

        obj_3d = Object3D(
            object_id=obj.object_id or str(uuid.uuid4()),
            name=obj.name,
            x=obj.x,
            y=obj.y,
            z=z,
            scale=round(scale, 3),
        )
        objects_3d.append(obj_3d)

    # 카메라 위치: 모든 오브젝트를 볼 수 있는 위치
    if objects_3d:
        max_z = max(abs(o.z) for o in objects_3d) if objects_3d else 0
        camera_z = max_z + 10
    else:
        camera_z = 10

    return SpatialScene(
        scene_id=str(uuid.uuid4()),
        objects=objects_3d,
        camera_position={"x": 0, "y": 0, "z": camera_z},
    )


def arrange_gallery(
    items: list,
    layout: str = "grid"
) -> SpatialScene:
    """
    갤러리 배치.

    layout: 'grid', 'circle', 'spiral'
    """
    objects_3d = []

    if layout == "grid":
        cols = max(1, math.ceil(math.sqrt(len(items))))
        for i, item in enumerate(items):
            row = i // cols
            col = i % cols
            obj = Object3D(
                object_id=str(uuid.uuid4()),
                name=item,
                x=col * 2.0,
                y=-row * 2.0,
                z=0.0,
                scale=1.0,
            )
            objects_3d.append(obj)

    elif layout == "circle":
        radius = max(2.0, len(items) * 0.5)
        for i, item in enumerate(items):
            angle = (2 * math.pi * i) / max(1, len(items))
            obj = Object3D(
                object_id=str(uuid.uuid4()),
                name=item,
                x=round(radius * math.cos(angle), 3),
                y=round(radius * math.sin(angle), 3),
                z=0.0,
                scale=1.0,
            )
            objects_3d.append(obj)

    elif layout == "spiral":
        for i, item in enumerate(items):
            angle = i * 0.8  # 나선 각도
            radius = 1.0 + i * 0.5  # 나선 반경 증가
            obj = Object3D(
                object_id=str(uuid.uuid4()),
                name=item,
                x=round(radius * math.cos(angle), 3),
                y=round(radius * math.sin(angle), 3),
                z=round(-i * 0.3, 3),  # 깊이도 점점 증가
                scale=max(0.5, 1.0 - i * 0.05),
            )
            objects_3d.append(obj)
    else:
        raise ValueError(f"지원하지 않는 layout: {layout}")

    return SpatialScene(
        scene_id=str(uuid.uuid4()),
        objects=objects_3d,
        camera_position={"x": 0, "y": 0, "z": 15},
    )


def calculate_bounds(scene: SpatialScene) -> dict:
    """바운딩 박스 계산"""
    if not scene.objects:
        return {
            "min": {"x": 0, "y": 0, "z": 0},
            "max": {"x": 0, "y": 0, "z": 0},
            "center": {"x": 0, "y": 0, "z": 0},
            "size": {"x": 0, "y": 0, "z": 0},
        }

    xs = [o.x for o in scene.objects]
    ys = [o.y for o in scene.objects]
    zs = [o.z for o in scene.objects]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)

    return {
        "min": {"x": min_x, "y": min_y, "z": min_z},
        "max": {"x": max_x, "y": max_y, "z": max_z},
        "center": {
            "x": round((min_x + max_x) / 2, 3),
            "y": round((min_y + max_y) / 2, 3),
            "z": round((min_z + max_z) / 2, 3),
        },
        "size": {
            "x": round(max_x - min_x, 3),
            "y": round(max_y - min_y, 3),
            "z": round(max_z - min_z, 3),
        },
    }
