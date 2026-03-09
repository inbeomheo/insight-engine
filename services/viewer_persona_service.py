"""시청 페르소나 추론 및 관심사 이동 감지 서비스

시청 히스토리를 분석하여 시청자 페르소나를 추론하고,
최근/과거 시청 데이터를 비교하여 관심사 이동을 감지합니다.
순수 Python 로직으로 외부 API를 호출하지 않습니다.
"""
import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)

# --- 페르소나 유형별 판별 기준 ---

# 카테고리 다양성 임계값 (고유 카테고리 수 / 전체 영상 수)
_EXPLORER_DIVERSITY_THRESHOLD = 0.6

# 딥다이버 판별: 동일 카테고리 비율 임계값
_DEEP_DIVER_DOMINANT_RATIO = 0.6

# 시청 비율(watch_ratio) 가중 평균 기준
_HIGH_ENGAGEMENT_THRESHOLD = 0.7

# 영상 길이 구간 (초)
_SHORT_DURATION = 600       # 10분 이하
_LONG_DURATION = 1800       # 30분 이상

# 관심사 이동 감지: 최소 영상 수
_MIN_VIDEOS_FOR_SHIFT = 2


@dataclass
class VideoMeta:
    """시청 영상 메타데이터"""
    video_id: str
    title: str
    category: str
    duration_seconds: int
    watch_ratio: float  # 0.0 ~ 1.0


@dataclass
class ViewerPersona:
    """시청자 페르소나 분석 결과"""
    persona_type: str        # "learner" | "explorer" | "deep_diver"
    confidence: float        # 0.0 ~ 1.0
    interests: List[str] = field(default_factory=list)
    preferred_length: str = "medium"   # "short" | "medium" | "long"
    engagement_pattern: str = ""       # 참여 패턴 설명


@dataclass
class InterestShift:
    """관심사 이동 분석 결과"""
    from_topics: List[str] = field(default_factory=list)
    to_topics: List[str] = field(default_factory=list)
    shift_strength: float = 0.0   # 0.0 ~ 1.0
    period: str = ""
    recommendation: str = ""


def _parse_video(raw: dict) -> VideoMeta:
    """dict를 VideoMeta로 변환. 누락/잘못된 필드는 기본값 사용."""
    return VideoMeta(
        video_id=str(raw.get("video_id", "")),
        title=str(raw.get("title", "")),
        category=str(raw.get("category", "")),
        duration_seconds=max(0, int(raw.get("duration_seconds", 0))),
        watch_ratio=max(0.0, min(1.0, float(raw.get("watch_ratio", 0.0)))),
    )


def _classify_length(duration_seconds: int) -> str:
    """영상 길이를 short/medium/long으로 분류"""
    if duration_seconds <= _SHORT_DURATION:
        return "short"
    if duration_seconds >= _LONG_DURATION:
        return "long"
    return "medium"


def _determine_preferred_length(videos: List[VideoMeta]) -> str:
    """시청 비율 가중 평균으로 선호 길이 결정"""
    if not videos:
        return "medium"

    # watch_ratio를 가중치로 사용하여 길이 선호도 집계
    length_scores: Counter = Counter()
    for v in videos:
        length = _classify_length(v.duration_seconds)
        length_scores[length] += v.watch_ratio

    if not length_scores:
        return "medium"

    return length_scores.most_common(1)[0][0]


def _compute_category_stats(videos: List[VideoMeta]) -> tuple:
    """카테고리 통계 계산. (카테고리 카운터, 다양성 비율, 최빈 카테고리 비율) 반환"""
    if not videos:
        return Counter(), 0.0, 0.0

    cat_counter = Counter(v.category for v in videos if v.category)
    total = len(videos)
    unique = len(cat_counter)

    diversity = unique / total if total > 0 else 0.0
    dominant_ratio = cat_counter.most_common(1)[0][1] / total if cat_counter and total > 0 else 0.0

    return cat_counter, diversity, dominant_ratio


def _avg_watch_ratio(videos: List[VideoMeta]) -> float:
    """평균 시청 비율 계산"""
    if not videos:
        return 0.0
    return sum(v.watch_ratio for v in videos) / len(videos)


def infer_persona(watch_history: list[dict]) -> ViewerPersona:
    """시청 히스토리에서 페르소나를 추론합니다.

    분류 기준:
    - deep_diver: 특정 카테고리 집중(60%+) & 높은 시청 비율
    - explorer: 카테고리 다양성이 높음(60%+)
    - learner: 그 외 (중간 집중도, 꾸준한 시청)

    Args:
        watch_history: VideoMeta 필드를 가진 dict 리스트

    Returns:
        ViewerPersona 분석 결과
    """
    if not watch_history:
        return ViewerPersona(
            persona_type="learner",
            confidence=0.0,
            interests=[],
            preferred_length="medium",
            engagement_pattern="시청 데이터가 없어 기본값을 사용합니다.",
        )

    videos = [_parse_video(v) for v in watch_history]
    cat_counter, diversity, dominant_ratio = _compute_category_stats(videos)
    avg_ratio = _avg_watch_ratio(videos)
    preferred_length = _determine_preferred_length(videos)

    # 관심사: 시청 빈도 상위 카테고리 (최대 5개)
    interests = [cat for cat, _ in cat_counter.most_common(5)]

    # --- 페르소나 판별 ---
    persona_type: str
    confidence: float
    engagement_pattern: str

    if dominant_ratio >= _DEEP_DIVER_DOMINANT_RATIO and avg_ratio >= _HIGH_ENGAGEMENT_THRESHOLD:
        # 딥다이버: 특정 분야 집중 + 높은 시청 완료율
        persona_type = "deep_diver"
        confidence = min(1.0, (dominant_ratio + avg_ratio) / 2)
        top_cat = cat_counter.most_common(1)[0][0] if cat_counter else "알 수 없음"
        engagement_pattern = (
            f"'{top_cat}' 카테고리에 집중하며(비율 {dominant_ratio:.0%}), "
            f"평균 {avg_ratio:.0%}까지 시청합니다."
        )
    elif diversity >= _EXPLORER_DIVERSITY_THRESHOLD:
        # 탐색자: 다양한 카테고리 탐색
        persona_type = "explorer"
        confidence = min(1.0, diversity)
        engagement_pattern = (
            f"{len(cat_counter)}개 카테고리를 탐색하며(다양성 {diversity:.0%}), "
            f"평균 {avg_ratio:.0%}까지 시청합니다."
        )
    else:
        # 학습자: 적당히 다양하고 꾸준히 시청
        persona_type = "learner"
        # confidence: 시청 비율이 높을수록, 어느정도 집중할수록 높음
        confidence = min(1.0, (avg_ratio * 0.6 + dominant_ratio * 0.4))
        engagement_pattern = (
            f"{len(cat_counter)}개 카테고리를 학습하며, "
            f"평균 {avg_ratio:.0%}까지 꾸준히 시청합니다."
        )

    return ViewerPersona(
        persona_type=persona_type,
        confidence=round(confidence, 2),
        interests=interests,
        preferred_length=preferred_length,
        engagement_pattern=engagement_pattern,
    )


def detect_interest_shift(
    recent_videos: list[dict],
    older_videos: list[dict],
) -> InterestShift:
    """최근 vs 과거 시청 데이터를 비교하여 관심사 이동을 감지합니다.

    Args:
        recent_videos: 최근 시청 영상 dict 리스트
        older_videos: 과거 시청 영상 dict 리스트

    Returns:
        InterestShift 분석 결과 (shift_strength 0~1)
    """
    if not recent_videos or not older_videos:
        return InterestShift(
            shift_strength=0.0,
            period="데이터 부족",
            recommendation="충분한 시청 데이터가 쌓이면 관심사 변화를 분석할 수 있습니다.",
        )

    recent = [_parse_video(v) for v in recent_videos]
    older = [_parse_video(v) for v in older_videos]

    # 카테고리 분포 비교
    recent_cats = Counter(v.category for v in recent if v.category)
    older_cats = Counter(v.category for v in older if v.category)

    if not recent_cats or not older_cats:
        return InterestShift(
            shift_strength=0.0,
            period="카테고리 정보 부족",
            recommendation="영상 카테고리 정보가 포함된 데이터가 필요합니다.",
        )

    # 비율 정규화
    recent_total = sum(recent_cats.values())
    older_total = sum(older_cats.values())
    recent_dist = {k: v / recent_total for k, v in recent_cats.items()}
    older_dist = {k: v / older_total for k, v in older_cats.items()}

    # 모든 카테고리에 대해 분포 차이 계산 (L1 거리 / 2 → 0~1 범위)
    all_cats = set(recent_dist) | set(older_dist)
    l1_distance = sum(
        abs(recent_dist.get(c, 0.0) - older_dist.get(c, 0.0))
        for c in all_cats
    )
    shift_strength = min(1.0, l1_distance / 2)

    # 감소한 토픽 (과거에 많았는데 최근 줄어든 것)
    from_topics = sorted(
        [c for c in all_cats if older_dist.get(c, 0.0) > recent_dist.get(c, 0.0)],
        key=lambda c: older_dist.get(c, 0.0) - recent_dist.get(c, 0.0),
        reverse=True,
    )[:3]

    # 증가한 토픽 (최근에 새로 등장하거나 비율이 늘어난 것)
    to_topics = sorted(
        [c for c in all_cats if recent_dist.get(c, 0.0) > older_dist.get(c, 0.0)],
        key=lambda c: recent_dist.get(c, 0.0) - older_dist.get(c, 0.0),
        reverse=True,
    )[:3]

    # 기간 설명
    period = f"과거 {len(older)}개 → 최근 {len(recent)}개 영상 비교"

    # 추천
    if shift_strength < 0.2:
        recommendation = "관심사가 안정적입니다. 기존 주제를 유지하세요."
    elif shift_strength < 0.5:
        recommendation = (
            f"관심사가 소폭 이동 중입니다. "
            f"'{to_topics[0]}' 관련 콘텐츠를 늘려보세요."
            if to_topics else "관심사가 소폭 이동 중입니다."
        )
    else:
        recommendation = (
            f"관심사가 크게 변화했습니다. "
            f"'{', '.join(to_topics[:2])}' 중심으로 콘텐츠 전략을 재편하세요."
            if to_topics else "관심사가 크게 변화했습니다."
        )

    return InterestShift(
        from_topics=from_topics,
        to_topics=to_topics,
        shift_strength=round(shift_strength, 2),
        period=period,
        recommendation=recommendation,
    )


def suggest_reframe(video_id: str, shift: InterestShift) -> str:
    """관심사 이동에 기반한 콘텐츠 재생성 제안을 반환합니다.

    Args:
        video_id: 대상 영상 ID
        shift: detect_interest_shift 결과

    Returns:
        재프레임 제안 문자열
    """
    if not video_id:
        return "영상 ID가 필요합니다."

    if shift.shift_strength < 0.1:
        return (
            f"영상 '{video_id}'는 현재 관심사와 잘 맞습니다. "
            f"기존 스타일을 유지하세요."
        )

    if not shift.to_topics:
        return (
            f"영상 '{video_id}'를 재생성할 때 "
            f"최근 시청 트렌드를 반영해보세요."
        )

    new_focus = ", ".join(shift.to_topics[:2])

    if shift.shift_strength < 0.4:
        return (
            f"영상 '{video_id}'를 재생성할 때 "
            f"'{new_focus}' 관점을 보조적으로 추가하세요."
        )

    return (
        f"영상 '{video_id}'를 '{new_focus}' 관점으로 재구성하세요. "
        f"관심사 이동 강도가 {shift.shift_strength:.0%}로 높아 "
        f"콘텐츠 방향 전환이 권장됩니다."
    )
