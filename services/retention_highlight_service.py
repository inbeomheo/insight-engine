"""
유지율 기반 하이라이트 서비스

시청 유지율(retention) 데이터를 분석하여
피크, 회복, 안정 구간을 하이라이트로 추출하는 규칙 기반 서비스.
외부 API 호출 없음.
"""
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class RetentionHighlight:
    """유지율 하이라이트."""
    timestamp: str              # "MM:SS" 형식
    retention_rate: float       # 0.0 ~ 1.0 (또는 0 ~ 100)
    highlight_type: str         # "peak", "recovery", "steady"
    duration_seconds: int       # 하이라이트 구간 길이
    description: str            # 설명


# ── 하이라이트 유형 상수 ──
TYPE_PEAK = "peak"            # 유지율 최고점
TYPE_RECOVERY = "recovery"    # 이탈 후 회복
TYPE_STEADY = "steady"        # 안정적 유지

# ── 임계값 설정 ──
_PEAK_PERCENTILE = 0.85       # 상위 15% 이상이면 피크
_RECOVERY_DROP = 0.10         # 10% 이상 하락 후
_RECOVERY_RISE = 0.05         # 5% 이상 회복하면 recovery
_STEADY_MIN_DURATION = 3      # 안정 구간 최소 3개 연속 데이터포인트
_STEADY_VARIANCE = 0.03       # 변동폭 3% 이내면 안정


def _normalize_rate(rate: float) -> float:
    """유지율을 0.0~1.0 범위로 정규화."""
    if rate > 1.0:
        return rate / 100.0
    return max(0.0, min(1.0, rate))


def _format_timestamp(seconds: int) -> str:
    """초를 'MM:SS' 형식으로 변환."""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def _parse_timestamp(ts: str) -> int:
    """'MM:SS' 또는 'HH:MM:SS'를 초로 변환."""
    parts = ts.strip().split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0


def _extract_data_points(retention_data: List[Dict]) -> List[Dict]:
    """입력 데이터를 정규화된 데이터포인트 목록으로 변환."""
    points = []
    for i, item in enumerate(retention_data):
        # timestamp가 있으면 파싱, 없으면 인덱스 기반 (10초 간격 가정)
        if "timestamp" in item:
            seconds = _parse_timestamp(str(item["timestamp"]))
        else:
            seconds = i * 10

        rate = _normalize_rate(item.get("retention_rate", item.get("rate", 0.0)))
        points.append({
            "seconds": seconds,
            "rate": rate,
            "index": i,
        })
    return points


def _find_peaks(points: List[Dict]) -> List[RetentionHighlight]:
    """유지율 최고점 구간 탐지."""
    if not points:
        return []

    rates = [p["rate"] for p in points]
    threshold = sorted(rates, reverse=True)[max(0, int(len(rates) * (1 - _PEAK_PERCENTILE)) - 1)]

    highlights = []
    i = 0
    while i < len(points):
        if points[i]["rate"] >= threshold:
            # 연속 피크 구간 찾기
            start = i
            while i < len(points) and points[i]["rate"] >= threshold:
                i += 1
            end = i - 1

            peak_rate = max(points[j]["rate"] for j in range(start, end + 1))
            duration = points[end]["seconds"] - points[start]["seconds"]
            if duration <= 0:
                duration = 10  # 최소 1 데이터포인트

            highlights.append(RetentionHighlight(
                timestamp=_format_timestamp(points[start]["seconds"]),
                retention_rate=round(peak_rate, 4),
                highlight_type=TYPE_PEAK,
                duration_seconds=duration,
                description=f"유지율 최고점 구간 ({peak_rate:.1%})",
            ))
        else:
            i += 1

    return highlights


def _find_recoveries(points: List[Dict]) -> List[RetentionHighlight]:
    """이탈 후 회복 구간 탐지."""
    if len(points) < 3:
        return []

    highlights = []
    i = 1
    while i < len(points) - 1:
        # 하락 감지
        if points[i]["rate"] < points[i - 1]["rate"] - _RECOVERY_DROP:
            drop_point = i
            # 회복 감지
            for j in range(i + 1, len(points)):
                if points[j]["rate"] > points[drop_point]["rate"] + _RECOVERY_RISE:
                    duration = points[j]["seconds"] - points[drop_point]["seconds"]
                    if duration <= 0:
                        duration = 10

                    highlights.append(RetentionHighlight(
                        timestamp=_format_timestamp(points[drop_point]["seconds"]),
                        retention_rate=round(points[j]["rate"], 4),
                        highlight_type=TYPE_RECOVERY,
                        duration_seconds=duration,
                        description=f"이탈 후 회복 ({points[drop_point]['rate']:.1%} → {points[j]['rate']:.1%})",
                    ))
                    i = j
                    break
            else:
                i += 1
        else:
            i += 1

    return highlights


def _find_steady(points: List[Dict]) -> List[RetentionHighlight]:
    """안정적 유지 구간 탐지."""
    if len(points) < _STEADY_MIN_DURATION:
        return []

    highlights = []
    i = 0
    while i < len(points) - _STEADY_MIN_DURATION + 1:
        # 연속 구간에서 분산 체크
        window = points[i:i + _STEADY_MIN_DURATION]
        rates = [p["rate"] for p in window]
        rate_range = max(rates) - min(rates)

        if rate_range <= _STEADY_VARIANCE:
            # 안정 구간 확장
            end = i + _STEADY_MIN_DURATION
            while end < len(points):
                extended_rates = [p["rate"] for p in points[i:end + 1]]
                if max(extended_rates) - min(extended_rates) <= _STEADY_VARIANCE:
                    end += 1
                else:
                    break
            end -= 1

            avg_rate = sum(p["rate"] for p in points[i:end + 1]) / (end - i + 1)
            duration = points[end]["seconds"] - points[i]["seconds"]
            if duration <= 0:
                duration = 10

            highlights.append(RetentionHighlight(
                timestamp=_format_timestamp(points[i]["seconds"]),
                retention_rate=round(avg_rate, 4),
                highlight_type=TYPE_STEADY,
                duration_seconds=duration,
                description=f"안정적 유지 구간 (평균 {avg_rate:.1%}, 변동 ±{rate_range:.1%})",
            ))
            i = end + 1
        else:
            i += 1

    return highlights


def highlight_by_retention(retention_data: List[Dict]) -> List[RetentionHighlight]:
    """
    유지율 데이터로 하이라이트 구간을 추출한다.

    Args:
        retention_data: 유지율 데이터 목록. 각 dict에:
            - retention_rate 또는 rate (float): 유지율 (0~1 또는 0~100)
            - timestamp (str, 선택): "MM:SS" 형식. 없으면 10초 간격 가정.

    Returns:
        List[RetentionHighlight]: 하이라이트 목록 (시간순 정렬)

    Raises:
        ValueError: 데이터가 비어있을 때
    """
    if not retention_data:
        raise ValueError("유지율 데이터가 비어있습니다")

    points = _extract_data_points(retention_data)

    # 세 가지 유형의 하이라이트 탐지
    peaks = _find_peaks(points)
    recoveries = _find_recoveries(points)
    steadies = _find_steady(points)

    # 합산 후 시간순 정렬
    all_highlights = peaks + recoveries + steadies
    all_highlights.sort(key=lambda h: _parse_timestamp(h.timestamp))

    return all_highlights
