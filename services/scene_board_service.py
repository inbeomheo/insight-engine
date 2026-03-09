"""
장면 보드 서비스 — 비디오/콘텐츠의 장면별 스토리보드 구성
"""

import uuid
import math
from dataclasses import dataclass, field


@dataclass
class Scene:
    """장면"""
    scene_id: str
    title: str
    description: str
    duration_sec: float
    visual_notes: str
    audio_notes: str
    order: int


@dataclass
class SceneBoard:
    """장면 보드"""
    board_id: str
    title: str
    scenes: list = field(default_factory=list)  # list[Scene]
    total_duration: float = 0.0


def _new_id(prefix: str = "scene") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _recalculate_duration(scenes: list) -> float:
    """총 재생 시간 재계산"""
    return sum(s.duration_sec for s in scenes)


def create_board(title: str) -> SceneBoard:
    """보드 생성

    Args:
        title: 보드 제목

    Returns:
        SceneBoard: 생성된 보드
    """
    if not title.strip():
        raise ValueError("보드 제목은 비어있을 수 없습니다.")

    return SceneBoard(
        board_id=_new_id("board"),
        title=title.strip(),
        scenes=[],
        total_duration=0.0,
    )


def add_scene(board: SceneBoard, scene_config: dict) -> SceneBoard:
    """장면 추가 (order 자동 부여)

    Args:
        board: 대상 보드
        scene_config: 장면 설정
            title, description, duration_sec, visual_notes, audio_notes

    Returns:
        SceneBoard: 장면이 추가된 보드
    """
    duration = scene_config.get("duration_sec", 0.0)
    if duration < 0:
        raise ValueError("장면 길이는 0 이상이어야 합니다.")

    next_order = len(board.scenes) + 1

    scene = Scene(
        scene_id=scene_config.get("scene_id", _new_id()),
        title=scene_config.get("title", ""),
        description=scene_config.get("description", ""),
        duration_sec=duration,
        visual_notes=scene_config.get("visual_notes", ""),
        audio_notes=scene_config.get("audio_notes", ""),
        order=next_order,
    )

    new_scenes = list(board.scenes) + [scene]
    return SceneBoard(
        board_id=board.board_id,
        title=board.title,
        scenes=new_scenes,
        total_duration=_recalculate_duration(new_scenes),
    )


def reorder_scenes(board: SceneBoard, scene_ids: list) -> SceneBoard:
    """장면 순서 변경

    Args:
        board: 대상 보드
        scene_ids: 새 순서의 scene_id 목록

    Returns:
        SceneBoard: 재정렬된 보드
    """
    scene_map = {s.scene_id: s for s in board.scenes}

    for sid in scene_ids:
        if sid not in scene_map:
            raise ValueError(f"존재하지 않는 장면 ID: {sid}")

    reordered = []
    for idx, sid in enumerate(scene_ids, 1):
        s = scene_map[sid]
        reordered.append(Scene(
            scene_id=s.scene_id,
            title=s.title,
            description=s.description,
            duration_sec=s.duration_sec,
            visual_notes=s.visual_notes,
            audio_notes=s.audio_notes,
            order=idx,
        ))

    # scene_ids에 없는 장면은 뒤에 추가
    remaining = [s for s in board.scenes if s.scene_id not in scene_ids]
    for s in remaining:
        reordered.append(Scene(
            scene_id=s.scene_id,
            title=s.title,
            description=s.description,
            duration_sec=s.duration_sec,
            visual_notes=s.visual_notes,
            audio_notes=s.audio_notes,
            order=len(reordered) + 1,
        ))

    return SceneBoard(
        board_id=board.board_id,
        title=board.title,
        scenes=reordered,
        total_duration=_recalculate_duration(reordered),
    )


def calculate_pacing(board: SceneBoard) -> dict:
    """페이싱 분석 — 평균 장면 길이, 최장/최단, 변동성

    Args:
        board: 대상 보드

    Returns:
        dict: {scene_count, avg_duration, max_duration, min_duration, variance, std_dev}
    """
    if not board.scenes:
        return {
            "scene_count": 0,
            "avg_duration": 0.0,
            "max_duration": 0.0,
            "min_duration": 0.0,
            "variance": 0.0,
            "std_dev": 0.0,
            "total_duration": 0.0,
        }

    durations = [s.duration_sec for s in board.scenes]
    n = len(durations)
    avg = sum(durations) / n
    variance = sum((d - avg) ** 2 for d in durations) / n

    return {
        "scene_count": n,
        "avg_duration": round(avg, 2),
        "max_duration": max(durations),
        "min_duration": min(durations),
        "variance": round(variance, 2),
        "std_dev": round(math.sqrt(variance), 2),
        "total_duration": round(sum(durations), 2),
    }


def split_scene(board: SceneBoard, scene_id: str, split_point: float) -> SceneBoard:
    """장면 분할 — 하나의 장면을 split_point 기준으로 두 개로 나눔

    Args:
        board: 대상 보드
        scene_id: 분할할 장면 ID
        split_point: 분할 시점 (초, 0 < split_point < duration)

    Returns:
        SceneBoard: 분할된 보드
    """
    scene_map = {s.scene_id: s for s in board.scenes}
    if scene_id not in scene_map:
        raise ValueError(f"존재하지 않는 장면 ID: {scene_id}")

    original = scene_map[scene_id]
    if split_point <= 0 or split_point >= original.duration_sec:
        raise ValueError(
            f"분할 시점은 0과 {original.duration_sec} 사이여야 합니다."
        )

    # 두 개 장면으로 분할
    part_a = Scene(
        scene_id=_new_id(),
        title=f"{original.title} (앞)",
        description=original.description,
        duration_sec=round(split_point, 2),
        visual_notes=original.visual_notes,
        audio_notes=original.audio_notes,
        order=0,  # 아래에서 재계산
    )
    part_b = Scene(
        scene_id=_new_id(),
        title=f"{original.title} (뒤)",
        description=original.description,
        duration_sec=round(original.duration_sec - split_point, 2),
        visual_notes=original.visual_notes,
        audio_notes=original.audio_notes,
        order=0,
    )

    # 기존 장면을 두 개로 교체
    new_scenes = []
    for s in board.scenes:
        if s.scene_id == scene_id:
            new_scenes.append(part_a)
            new_scenes.append(part_b)
        else:
            new_scenes.append(s)

    # order 재부여
    for idx, s in enumerate(new_scenes):
        new_scenes[idx] = Scene(
            scene_id=s.scene_id,
            title=s.title,
            description=s.description,
            duration_sec=s.duration_sec,
            visual_notes=s.visual_notes,
            audio_notes=s.audio_notes,
            order=idx + 1,
        )

    return SceneBoard(
        board_id=board.board_id,
        title=board.title,
        scenes=new_scenes,
        total_duration=_recalculate_duration(new_scenes),
    )
