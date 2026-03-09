"""
모션 그래픽 인포카드 오버레이 서비스
영상의 하이라이트 구간에 인포카드 오버레이 데이터를 생성한다.
"""
import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# 유효한 위치 값
VALID_POSITIONS = {"top_left", "top_right", "bottom_left", "bottom_right", "center"}

# 하이라이트 타입별 기본 스타일
TYPE_STYLE_MAP = {
    "stat": "highlight",
    "quote": "quote",
    "key_point": "emphasis",
    "definition": "info",
    "warning": "alert",
}

# 기본 스타일
DEFAULT_STYLE = "default"
DEFAULT_POSITION = "bottom_right"
DEFAULT_DURATION = 5


@dataclass
class InfocardOverlay:
    """인포카드 오버레이 데이터"""
    card_id: str
    video_id: str
    timestamp: str
    title: str
    content: str
    position: str
    duration_seconds: int
    style: str


def _validate_timestamp(ts: str) -> bool:
    """타임스탬프 형식 검증 (MM:SS 또는 HH:MM:SS)"""
    return bool(re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', ts))


def _normalize_timestamp(ts: str) -> str:
    """타임스탬프를 MM:SS 형식으로 정규화"""
    parts = ts.split(':')
    if len(parts) == 3:
        # HH:MM:SS → 시간을 분으로 변환
        h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
        total_min = h * 60 + m
        return f"{total_min:02d}:{s:02d}"
    elif len(parts) == 2:
        m, s = int(parts[0]), int(parts[1])
        return f"{m:02d}:{s:02d}"
    return ts


def _resolve_position(highlight: dict) -> str:
    """하이라이트에서 위치 결정"""
    pos = highlight.get("position", DEFAULT_POSITION)
    if pos in VALID_POSITIONS:
        return pos
    return DEFAULT_POSITION


def _resolve_style(highlight: dict) -> str:
    """하이라이트 타입에 따라 스타일 결정"""
    h_type = highlight.get("type", "")
    return TYPE_STYLE_MAP.get(h_type, DEFAULT_STYLE)


def _build_title(highlight: dict) -> str:
    """하이라이트에서 제목 생성"""
    text = highlight.get("text", "").strip()
    if not text:
        return "정보"
    # 제목은 최대 50자
    if len(text) > 50:
        return text[:47] + "..."
    return text


def overlay_infocards(
    video_id: str,
    highlights: List[Dict],
) -> List[InfocardOverlay]:
    """하이라이트 목록으로 인포카드 오버레이를 생성한다.

    Args:
        video_id: YouTube 영상 ID
        highlights: 하이라이트 목록
            [{"timestamp": "01:30", "text": "핵심 포인트", "type": "stat"}]

    Returns:
        InfocardOverlay 리스트
    """
    if not video_id or not video_id.strip():
        logger.warning("video_id가 비어 있습니다")
        return []

    if not highlights:
        logger.info("하이라이트가 없어 빈 리스트를 반환합니다")
        return []

    video_id = video_id.strip()
    result: List[InfocardOverlay] = []

    for idx, hl in enumerate(highlights):
        if not isinstance(hl, dict):
            logger.warning("하이라이트 #%d: dict가 아닌 값 무시", idx)
            continue

        ts = hl.get("timestamp", "")
        if not ts or not _validate_timestamp(ts):
            logger.warning("하이라이트 #%d: 유효하지 않은 타임스탬프 '%s'", idx, ts)
            continue

        normalized_ts = _normalize_timestamp(ts)
        title = _build_title(hl)
        content = hl.get("text", "").strip()
        position = _resolve_position(hl)
        style = _resolve_style(hl)
        duration = hl.get("duration", DEFAULT_DURATION)

        # duration 범위 제한 (1~30초)
        if not isinstance(duration, (int, float)):
            duration = DEFAULT_DURATION
        duration = max(1, min(30, int(duration)))

        card = InfocardOverlay(
            card_id=str(uuid.uuid4()),
            video_id=video_id,
            timestamp=normalized_ts,
            title=title,
            content=content,
            position=position,
            duration_seconds=duration,
            style=style,
        )
        result.append(card)

    logger.info(
        "video_id=%s: %d개 하이라이트 중 %d개 인포카드 생성",
        video_id, len(highlights), len(result),
    )
    return result
