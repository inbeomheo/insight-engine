"""스마트 리프레임 서비스

영상을 Shorts/Reels 등 다른 화면 비율로 리프레임하는 계획을 생성한다.
자막 기반 장면 분석으로 크롭 영역을 결정한다.
"""
import re
from dataclasses import dataclass, field


@dataclass
class ReframeResult:
    """리프레임 결과"""
    video_id: str
    original_aspect: str       # "16:9"
    target_aspect: str         # "9:16"
    crop_regions: list         # [{"start": "MM:SS", "end": "MM:SS", "x": N, "y": N, "w": N, "h": N}]
    strategy: str              # "center" | "speaker_track" | "content_aware"


# 지원하는 화면 비율과 해상도 매핑 (원본 1920x1080 기준)
_ASPECT_CONFIGS = {
    "9:16": {"w": 608, "h": 1080, "label": "Shorts/Reels"},
    "1:1": {"w": 1080, "h": 1080, "label": "Instagram 정사각형"},
    "4:5": {"w": 864, "h": 1080, "label": "Instagram 피드"},
    "4:3": {"w": 1440, "h": 1080, "label": "전통 TV"},
}

# 원본 해상도 기본값
_ORIGINAL_WIDTH = 1920
_ORIGINAL_HEIGHT = 1080

# 장면 전환 감지 키워드 (자막 기반)
_SCENE_CHANGE_MARKERS = [
    '다음으로', '그래서', '한편', '또한', '그런데', '하지만',
    '이제', '자', '좋습니다', '다음', '첫번째', '두번째',
]


def reframe_for_shorts(
    video_id: str,
    aspect: str = "9:16",
    transcript: str = "",
) -> ReframeResult:
    """Shorts/Reels용 리프레임 계획 생성

    Args:
        video_id: 대상 영상 ID
        aspect: 목표 화면 비율 (기본 9:16)
        transcript: 자막 텍스트 (장면 분석용, 선택)

    Returns:
        ReframeResult: 리프레임 크롭 계획
    """
    if not video_id or not video_id.strip():
        raise ValueError("video_id는 비어 있을 수 없습니다")

    aspect = aspect.strip()
    if aspect not in _ASPECT_CONFIGS:
        raise ValueError(
            f"지원하지 않는 화면 비율: {aspect}. "
            f"지원 비율: {', '.join(_ASPECT_CONFIGS.keys())}"
        )

    # 전략 결정
    strategy = _determine_strategy(transcript)

    # 자막 기반 장면 구간 분할
    segments = _split_transcript_segments(transcript)

    # 각 구간별 크롭 영역 계산
    config = _ASPECT_CONFIGS[aspect]
    crop_regions = _compute_crop_regions(segments, config, strategy)

    return ReframeResult(
        video_id=video_id,
        original_aspect="16:9",
        target_aspect=aspect,
        crop_regions=crop_regions,
        strategy=strategy,
    )


def get_supported_aspects() -> dict:
    """지원하는 화면 비율 목록 반환"""
    return {k: v["label"] for k, v in _ASPECT_CONFIGS.items()}


def _determine_strategy(transcript: str) -> str:
    """자막 내용 기반 리프레임 전략 결정

    - 자막 없음: center (중앙 크롭)
    - 1인칭/발표 키워드 다수: speaker_track (화자 추적)
    - 그 외: content_aware (내용 기반)
    """
    if not transcript or len(transcript.strip()) < 50:
        return "center"

    # 발표/강의 패턴 감지
    speaker_keywords = ['저는', '제가', '여러분', '안녕하세요', '오늘은', '설명']
    speaker_count = sum(1 for kw in speaker_keywords if kw in transcript)

    if speaker_count >= 3:
        return "speaker_track"

    return "content_aware"


def _split_transcript_segments(transcript: str) -> list:
    """자막을 장면 전환 기준으로 분할

    타임스탬프([MM:SS])가 있으면 사용하고, 없으면 문장 수 기반 균등 분할.

    Returns:
        [{"start_sec": int, "end_sec": int, "text": str}, ...]
    """
    if not transcript or not transcript.strip():
        # 자막 없으면 기본 1개 구간 (전체)
        return [{"start_sec": 0, "end_sec": 60, "text": ""}]

    # 타임스탬프 포함 자막 파싱 ([MM:SS] 텍스트)
    timed = re.findall(r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*(.+)', transcript)
    if timed:
        segments = []
        for i, (time_str, text) in enumerate(timed):
            start_sec = _parse_time(time_str)
            # 다음 타임스탬프까지 또는 +30초
            if i + 1 < len(timed):
                end_sec = _parse_time(timed[i + 1][0])
            else:
                end_sec = start_sec + 30
            segments.append({
                "start_sec": start_sec,
                "end_sec": end_sec,
                "text": text.strip(),
            })
        return _merge_short_segments(segments)

    # 타임스탬프 없으면 문장 기반 균등 분할
    sentences = re.split(r'[.!?。]\s*', transcript)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return [{"start_sec": 0, "end_sec": 60, "text": transcript[:200]}]

    # 5개 구간으로 균등 분할 (최대)
    chunk_size = max(1, len(sentences) // 5)
    segments = []
    sec_per_sentence = 5  # 문장당 약 5초 추정

    for i in range(0, len(sentences), chunk_size):
        chunk = sentences[i:i + chunk_size]
        start = i * sec_per_sentence
        end = (i + len(chunk)) * sec_per_sentence
        segments.append({
            "start_sec": start,
            "end_sec": end,
            "text": " ".join(chunk),
        })

    return segments


def _merge_short_segments(segments: list, min_duration: int = 5) -> list:
    """너무 짧은 구간을 이전 구간에 병합"""
    if len(segments) <= 1:
        return segments

    merged = [segments[0]]
    for seg in segments[1:]:
        duration = seg["end_sec"] - seg["start_sec"]
        if duration < min_duration:
            # 이전 구간에 병합
            merged[-1]["end_sec"] = seg["end_sec"]
            merged[-1]["text"] += " " + seg["text"]
        else:
            merged.append(seg)
    return merged


def _compute_crop_regions(segments: list, config: dict, strategy: str) -> list:
    """각 구간별 크롭 영역 계산

    Args:
        segments: 장면 구간 리스트
        config: 목표 비율 설정 (w, h)
        strategy: 크롭 전략
    """
    crop_w = config["w"]
    crop_h = config["h"]
    regions = []

    for i, seg in enumerate(segments):
        x, y = _calculate_crop_position(i, len(segments), crop_w, crop_h, strategy)

        regions.append({
            "start": _format_seconds(seg["start_sec"]),
            "end": _format_seconds(seg["end_sec"]),
            "x": x,
            "y": y,
            "w": crop_w,
            "h": crop_h,
        })

    return regions


def _calculate_crop_position(
    segment_index: int,
    total_segments: int,
    crop_w: int,
    crop_h: int,
    strategy: str,
) -> tuple:
    """크롭 위치(x, y) 결정

    - center: 항상 중앙
    - speaker_track: 중앙 약간 좌우 이동 (화자 위치 시뮬레이션)
    - content_aware: 구간별로 좌/중/우 분산
    """
    # 중앙 기본 위치
    center_x = (_ORIGINAL_WIDTH - crop_w) // 2
    center_y = (_ORIGINAL_HEIGHT - crop_h) // 2
    # y는 항상 0 (세로가 원본과 같거나 크면)
    y = max(0, center_y)

    if strategy == "center":
        return center_x, y

    if strategy == "speaker_track":
        # 화자가 중앙~약간 좌측에 있다고 가정, 미세 조정
        offset = (segment_index % 3 - 1) * 30  # -30, 0, +30
        x = max(0, min(center_x + offset, _ORIGINAL_WIDTH - crop_w))
        return x, y

    if strategy == "content_aware":
        # 구간별로 좌/중/우 분산
        if total_segments <= 1:
            return center_x, y
        position_ratio = segment_index / max(1, total_segments - 1)
        # 좌(0.2) ~ 우(0.8) 범위에서 크롭
        x_range = _ORIGINAL_WIDTH - crop_w
        x = int(x_range * (0.2 + position_ratio * 0.6))
        x = max(0, min(x, x_range))
        return x, y

    return center_x, y


def _parse_time(time_str: str) -> int:
    """시간 문자열을 초 단위로 변환 (MM:SS 또는 HH:MM:SS)"""
    parts = time_str.split(':')
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return 0


def _format_seconds(seconds: int) -> str:
    """초를 MM:SS 형식으로 변환"""
    m = seconds // 60
    s = seconds % 60
    return f"{m}:{s:02d}"
