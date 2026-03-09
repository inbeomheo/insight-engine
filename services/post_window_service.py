"""
게시 윈도우 예측 서비스

게시 히스토리(posted_at, engagement)를 분석하여
요일/시간대별 최적 게시 타이밍을 예측합니다.
"""
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)

# 요일 한국어 매핑
_DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday",
              "Friday", "Saturday", "Sunday"]
_DAY_KR = {
    "Monday": "월", "Tuesday": "화", "Wednesday": "수",
    "Thursday": "목", "Friday": "금", "Saturday": "토", "Sunday": "일",
}

# 시간대 가중치 (프라임타임에 약간의 보정)
_PRIMETIME_HOURS = {7, 8, 9, 12, 13, 18, 19, 20, 21}
_PRIMETIME_BONUS = 0.05


@dataclass
class TimeSlot:
    """최적 게시 시간대"""
    day_of_week: str   # "Monday" 등
    hour: int          # 0-23
    predicted_engagement: float  # 예상 참여율
    confidence: float  # 0.0~1.0


def _parse_history(history: list[dict]) -> list[tuple[datetime, float]]:
    """히스토리 레코드를 (datetime, engagement) 튜플 리스트로 변환."""
    parsed = []
    for record in history:
        posted_at = record.get("posted_at")
        engagement = record.get("engagement", 0)
        if not posted_at:
            continue
        # 문자열이면 파싱, datetime이면 그대로
        if isinstance(posted_at, str):
            try:
                dt = datetime.fromisoformat(posted_at)
            except (ValueError, TypeError):
                logger.warning("날짜 파싱 실패: %s", posted_at)
                continue
        elif isinstance(posted_at, datetime):
            dt = posted_at
        else:
            continue
        parsed.append((dt, float(engagement)))
    return parsed


def _aggregate_slots(
    parsed: list[tuple[datetime, float]],
) -> dict[tuple[str, int], list[float]]:
    """(요일, 시간) 키별로 engagement 값을 수집."""
    slots: dict[tuple[str, int], list[float]] = defaultdict(list)
    for dt, eng in parsed:
        day_name = _DAY_NAMES[dt.weekday()]
        slots[(day_name, dt.hour)].append(eng)
    return slots


def _calculate_confidence(sample_count: int, total_count: int) -> float:
    """샘플 수에 따른 신뢰도 계산.

    데이터가 많을수록 높은 신뢰도, 최소 3개 이상이면 0.5 이상.
    """
    if total_count == 0:
        return 0.0
    # 슬롯별 샘플 비중 + 절대 샘플 수 기반
    ratio = min(sample_count / max(total_count, 1), 1.0)
    absolute = min(sample_count / 10.0, 1.0)  # 10개면 최대
    return round(min((ratio + absolute) / 2, 1.0), 2)


def predict_best_window(
    history: list[dict],
    followers: int = 0,
    top_n: int = 5,
) -> List[TimeSlot]:
    """게시 히스토리에서 최적 시간대 예측.

    Args:
        history: [{"posted_at": "ISO문자열", "engagement": 숫자}] 형태
        followers: 팔로워 수 (프라임타임 가중치 조정에 사용)
        top_n: 반환할 상위 슬롯 수

    Returns:
        engagement 예측 점수 내림차순의 TimeSlot 리스트
    """
    if not history:
        logger.info("히스토리가 비어 있어 기본 시간대 반환")
        return _default_slots()

    parsed = _parse_history(history)
    if not parsed:
        logger.warning("유효한 히스토리 레코드 없음")
        return _default_slots()

    slots = _aggregate_slots(parsed)
    total_count = len(parsed)

    results: list[TimeSlot] = []
    for (day, hour), engagements in slots.items():
        avg_eng = sum(engagements) / len(engagements)
        # 프라임타임 보너스 (팔로워 1000+ 이면 보너스 증가)
        bonus = _PRIMETIME_BONUS if hour in _PRIMETIME_HOURS else 0.0
        if followers >= 1000 and hour in _PRIMETIME_HOURS:
            bonus *= 1.5
        predicted = round(avg_eng * (1 + bonus), 2)
        confidence = _calculate_confidence(len(engagements), total_count)

        results.append(TimeSlot(
            day_of_week=day,
            hour=hour,
            predicted_engagement=predicted,
            confidence=confidence,
        ))

    # 예측 engagement 내림차순 정렬
    results.sort(key=lambda s: s.predicted_engagement, reverse=True)
    return results[:top_n]


def _default_slots() -> list[TimeSlot]:
    """데이터 없을 때 일반적인 최적 시간대 반환."""
    defaults = [
        ("Tuesday", 9), ("Wednesday", 12), ("Thursday", 19),
        ("Monday", 8), ("Friday", 18),
    ]
    return [
        TimeSlot(day_of_week=d, hour=h, predicted_engagement=0.0, confidence=0.0)
        for d, h in defaults
    ]


def format_slot_kr(slot: TimeSlot) -> str:
    """TimeSlot을 한국어 문자열로 변환."""
    day_kr = _DAY_KR.get(slot.day_of_week, slot.day_of_week)
    return f"{day_kr}요일 {slot.hour}시 (참여 예측: {slot.predicted_engagement}, 신뢰도: {slot.confidence})"
