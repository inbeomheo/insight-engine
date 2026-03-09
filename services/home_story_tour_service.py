"""
홈스토리 투어 서비스 — 부동산/인테리어 투어 콘텐츠 구조화
"""

import uuid
from dataclasses import dataclass, field


@dataclass
class Room:
    """방"""
    room_id: str
    name: str
    description: str
    features: list[str]
    area_sqm: float
    photos: list[str]


@dataclass
class HomeTour:
    """홈 투어"""
    tour_id: str
    title: str
    rooms: list[Room] = field(default_factory=list)
    total_area: float = 0.0
    highlights: list[str] = field(default_factory=list)


def create_tour(title: str, rooms_config: list[dict]) -> HomeTour:
    """홈 투어 생성"""
    rooms = []
    total_area = 0.0
    all_features = []

    for rc in rooms_config:
        room = Room(
            room_id=str(uuid.uuid4())[:8],
            name=rc.get('name', ''),
            description=rc.get('description', ''),
            features=rc.get('features', []),
            area_sqm=rc.get('area_sqm', 0.0),
            photos=rc.get('photos', [])
        )
        rooms.append(room)
        total_area += room.area_sqm
        all_features.extend(room.features)

    # 하이라이트: 특징 빈도 상위 항목
    feat_counts: dict[str, int] = {}
    for f in all_features:
        feat_counts[f] = feat_counts.get(f, 0) + 1
    highlights = sorted(feat_counts, key=feat_counts.get, reverse=True)[:3]

    return HomeTour(
        tour_id=str(uuid.uuid4())[:8],
        title=title,
        rooms=rooms,
        total_area=round(total_area, 2),
        highlights=highlights
    )


def add_room(tour: HomeTour, room_config: dict) -> HomeTour:
    """방 추가"""
    room = Room(
        room_id=str(uuid.uuid4())[:8],
        name=room_config.get('name', ''),
        description=room_config.get('description', ''),
        features=room_config.get('features', []),
        area_sqm=room_config.get('area_sqm', 0.0),
        photos=room_config.get('photos', [])
    )
    new_rooms = tour.rooms + [room]
    new_total = round(tour.total_area + room.area_sqm, 2)

    return HomeTour(
        tour_id=tour.tour_id,
        title=tour.title,
        rooms=new_rooms,
        total_area=new_total,
        highlights=tour.highlights
    )


def generate_narrative(tour: HomeTour) -> str:
    """투어 내러티브 생성"""
    parts = [f"'{tour.title}' 투어에 오신 것을 환영합니다."]
    parts.append(f"총 면적 {tour.total_area}㎡의 공간을 둘러봅니다.")
    parts.append("")

    for i, room in enumerate(tour.rooms, 1):
        parts.append(f"{i}. {room.name} ({room.area_sqm}㎡)")
        parts.append(f"   {room.description}")
        if room.features:
            parts.append(f"   특징: {', '.join(room.features)}")
        parts.append("")

    if tour.highlights:
        parts.append(f"이 집의 핵심 포인트: {', '.join(tour.highlights)}")

    return '\n'.join(parts)


def calculate_stats(tour: HomeTour) -> dict:
    """통계 — 총 면적, 방 수, 특징 빈도"""
    feat_counts: dict[str, int] = {}
    for room in tour.rooms:
        for f in room.features:
            feat_counts[f] = feat_counts.get(f, 0) + 1

    return {
        'total_area': tour.total_area,
        'room_count': len(tour.rooms),
        'feature_frequency': feat_counts,
        'avg_room_area': round(tour.total_area / max(len(tour.rooms), 1), 2)
    }
