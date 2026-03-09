"""
이탈 구간 리컷 시뮬레이션 서비스

시청자 이탈률 데이터를 분석해 이탈이 높은 구간을
제거/압축하는 리컷 계획을 생성하는 규칙 기반 서비스.
외부 API 호출 없음.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class RemovedSegment:
    """제거 대상 구간."""
    start: str            # "MM:SS" 형식
    end: str              # "MM:SS" 형식
    duration_seconds: int
    reason: str


@dataclass
class RecutPlan:
    """리컷 시뮬레이션 결과."""
    original_length: int          # 원본 영상 길이 (초)
    recut_length: int             # 리컷 후 예상 길이 (초)
    removed_segments: List[RemovedSegment]
    estimated_improvement: float  # 예상 유지율 개선치 (0.0 ~ 1.0)


# ── 임계값 설정 ──
_DROPOUT_THRESHOLD = 0.15     # 이탈률 15% 이상이면 제거 대상
_SEVERE_DROPOUT = 0.25        # 이탈률 25% 이상이면 심각한 이탈
_MIN_SEGMENT_DURATION = 5     # 최소 5초 이상 구간만 제거 대상
_MAX_REMOVAL_RATIO = 0.40     # 전체 영상의 40% 이상 제거 금지
_IMPROVEMENT_PER_REMOVAL = 0.02  # 구간당 기본 개선치


def _parse_timestamp(ts: str) -> int:
    """'MM:SS' 또는 'HH:MM:SS'를 초로 변환."""
    parts = ts.strip().split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0


def _format_timestamp(seconds: int) -> str:
    """초를 'MM:SS' 형식으로 변환."""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def _normalize_rate(rate: float) -> float:
    """이탈률을 0.0~1.0 범위로 정규화."""
    if rate > 1.0:
        return rate / 100.0
    return max(0.0, min(1.0, rate))


def _classify_reason(dropout_rate: float) -> str:
    """이탈률에 따른 제거 사유 분류."""
    if dropout_rate >= _SEVERE_DROPOUT:
        return "심각한 시청자 이탈 (이탈률 {:.1%})".format(dropout_rate)
    elif dropout_rate >= _DROPOUT_THRESHOLD:
        return "높은 이탈률 구간 (이탈률 {:.1%})".format(dropout_rate)
    return "이탈률 초과 구간"


def _estimate_improvement(segments: List[RemovedSegment], original_length: int) -> float:
    """제거 구간 기반 유지율 개선 예측."""
    if original_length <= 0 or not segments:
        return 0.0

    total_removed = sum(s.duration_seconds for s in segments)
    removal_ratio = total_removed / original_length

    # 기본 개선 = 구간 수 × 기본 개선치 + 제거 비율 보너스
    base_improvement = len(segments) * _IMPROVEMENT_PER_REMOVAL
    ratio_bonus = removal_ratio * 0.1  # 제거 비율의 10%를 보너스로

    improvement = base_improvement + ratio_bonus
    # 최대 30% 개선으로 제한
    return round(min(improvement, 0.30), 4)


def simulate_recut(dropout_data: List[Dict]) -> RecutPlan:
    """
    이탈 구간 리컷 시뮬레이션을 실행한다.

    Args:
        dropout_data: 이탈률 데이터 목록. 각 dict에:
            - timestamp 또는 start (str): 구간 시작 ("MM:SS")
            - end (str, 선택): 구간 끝. 없으면 다음 항목 시작까지.
            - dropout_rate 또는 rate (float): 이탈률 (0~1 또는 0~100)
            - duration_seconds (int, 선택): 구간 길이

    Returns:
        RecutPlan: 리컷 계획

    Raises:
        ValueError: 데이터가 비어있을 때
    """
    if not dropout_data:
        raise ValueError("이탈률 데이터가 비어있습니다")

    # 데이터 정규화
    segments_to_remove: List[RemovedSegment] = []
    parsed_data = []

    for i, item in enumerate(dropout_data):
        ts_str = item.get("timestamp", item.get("start", "00:00"))
        start_sec = _parse_timestamp(str(ts_str))
        rate = _normalize_rate(item.get("dropout_rate", item.get("rate", 0.0)))

        # 구간 끝 결정
        if "end" in item:
            end_sec = _parse_timestamp(str(item["end"]))
        elif "duration_seconds" in item:
            end_sec = start_sec + item["duration_seconds"]
        elif i + 1 < len(dropout_data):
            next_ts = dropout_data[i + 1].get("timestamp", dropout_data[i + 1].get("start", "00:00"))
            end_sec = _parse_timestamp(str(next_ts))
        else:
            end_sec = start_sec + 10  # 기본 10초

        parsed_data.append({
            "start_sec": start_sec,
            "end_sec": end_sec,
            "rate": rate,
        })

    # 원본 영상 길이 추정
    if parsed_data:
        original_length = max(d["end_sec"] for d in parsed_data)
    else:
        original_length = 0

    # 이탈 임계값 초과 구간 식별
    for data in parsed_data:
        if data["rate"] >= _DROPOUT_THRESHOLD:
            duration = data["end_sec"] - data["start_sec"]
            if duration >= _MIN_SEGMENT_DURATION:
                segments_to_remove.append(RemovedSegment(
                    start=_format_timestamp(data["start_sec"]),
                    end=_format_timestamp(data["end_sec"]),
                    duration_seconds=duration,
                    reason=_classify_reason(data["rate"]),
                ))

    # 최대 제거 비율 제한
    if original_length > 0:
        total_removable = int(original_length * _MAX_REMOVAL_RATIO)
        accumulated = 0
        limited_segments = []
        for seg in segments_to_remove:
            if accumulated + seg.duration_seconds <= total_removable:
                limited_segments.append(seg)
                accumulated += seg.duration_seconds
            else:
                # 부분 제거는 하지 않음
                break
        segments_to_remove = limited_segments

    # 리컷 후 길이 계산
    total_removed = sum(s.duration_seconds for s in segments_to_remove)
    recut_length = max(0, original_length - total_removed)

    # 유지율 개선 예측
    improvement = _estimate_improvement(segments_to_remove, original_length)

    return RecutPlan(
        original_length=original_length,
        recut_length=recut_length,
        removed_segments=segments_to_remove,
        estimated_improvement=improvement,
    )
