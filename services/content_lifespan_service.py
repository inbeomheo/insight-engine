"""
콘텐츠 수명 예측 서비스

콘텐츠 메타데이터와 성과 데이터를 기반으로
예상 수명(일), 감쇠율, 피크 날짜, 영향 요인을 예측합니다.
"""
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class LifespanPrediction:
    """콘텐츠 수명 예측 결과"""
    content_id: str
    predicted_days: int
    decay_rate: float
    peak_date: str
    factors: List[str] = field(default_factory=list)


# 콘텐츠 유형별 기본 수명 (일)
_BASE_LIFESPAN: Dict[str, int] = {
    "blog": 365,
    "sns": 3,
    "video": 180,
    "newsletter": 7,
    "tutorial": 540,
    "news": 2,
    "evergreen": 730,
}

# 품질 지표별 수명 보정 계수
_QUALITY_FACTORS: Dict[str, float] = {
    "seo_optimized": 1.5,         # SEO 최적화 시 수명 50% 증가
    "high_engagement": 1.3,       # 높은 참여율
    "has_backlinks": 1.4,         # 백링크 보유
    "trending_topic": 0.6,        # 트렌드 주제는 수명 단축
    "seasonal": 0.5,              # 시즈널 콘텐츠
    "updated_regularly": 1.8,     # 정기 업데이트
    "multimedia": 1.2,            # 멀티미디어 포함
}


def _estimate_base_lifespan(content: dict) -> int:
    """콘텐츠 유형과 메타데이터로 기본 수명을 추정합니다."""
    content_type = content.get("type", "blog").lower()
    return _BASE_LIFESPAN.get(content_type, 90)


def _apply_quality_modifiers(base_days: int, qualities: List[str]) -> tuple:
    """품질 요인을 적용하여 수명을 보정합니다.

    Returns:
        (보정된 수명 일수, 적용된 요인 설명 리스트)
    """
    adjusted = float(base_days)
    applied_factors: List[str] = []

    for quality in qualities:
        q = quality.lower().strip()
        if q in _QUALITY_FACTORS:
            multiplier = _QUALITY_FACTORS[q]
            adjusted *= multiplier
            direction = "증가" if multiplier > 1 else "감소"
            applied_factors.append(
                f"{q}: 수명 {direction} (x{multiplier})"
            )

    return int(adjusted), applied_factors


def _calculate_decay_rate(predicted_days: int) -> float:
    """일일 감쇠율을 계산합니다.

    수명 종료 시 원래 트래픽의 10%로 감소한다고 가정합니다.
    지수 감쇠 모델: traffic(t) = e^(-decay_rate * t)
    """
    if predicted_days <= 0:
        return 1.0

    # -ln(0.1) / predicted_days
    decay = -math.log(0.1) / predicted_days
    return round(decay, 6)


def _estimate_peak_date(content: dict, predicted_days: int) -> str:
    """피크 트래픽 날짜를 추정합니다."""
    published = content.get("published_date", "")

    try:
        pub_date = datetime.strptime(published, "%Y-%m-%d")
    except (ValueError, TypeError):
        pub_date = datetime.now()

    # 피크는 수명의 약 15~25% 시점에 발생한다고 가정
    content_type = content.get("type", "blog").lower()
    if content_type in ("sns", "news"):
        peak_offset = max(1, int(predicted_days * 0.1))
    else:
        peak_offset = max(1, int(predicted_days * 0.2))

    peak_date = pub_date + timedelta(days=peak_offset)
    return peak_date.strftime("%Y-%m-%d")


def predict_lifespan(content: dict) -> LifespanPrediction:
    """콘텐츠 수명을 예측합니다.

    Args:
        content: 콘텐츠 메타데이터 딕셔너리.
            - content_id (str): 콘텐츠 식별자
            - type (str): 콘텐츠 유형 (blog, sns, video 등)
            - qualities (list[str]): 품질 특성 리스트
            - published_date (str): 발행일 (YYYY-MM-DD)

    Returns:
        LifespanPrediction: 예상 수명, 감쇠율, 피크 날짜, 영향 요인.
    """
    content_id = content.get("content_id", "unknown")

    if not content:
        logger.warning("빈 콘텐츠 데이터가 전달되었습니다.")
        return LifespanPrediction(
            content_id=content_id,
            predicted_days=0,
            decay_rate=0.0,
            peak_date="",
        )

    base_days = _estimate_base_lifespan(content)
    qualities = content.get("qualities", [])
    predicted_days, factors = _apply_quality_modifiers(base_days, qualities)

    # 콘텐츠 유형도 요인으로 기록
    content_type = content.get("type", "blog")
    factors.insert(0, f"콘텐츠 유형: {content_type} (기본 {base_days}일)")

    decay_rate = _calculate_decay_rate(predicted_days)
    peak_date = _estimate_peak_date(content, predicted_days)

    logger.info(
        "수명 예측 완료: content=%s, 예상 %d일, 감쇠율=%.6f",
        content_id, predicted_days, decay_rate,
    )

    return LifespanPrediction(
        content_id=content_id,
        predicted_days=predicted_days,
        decay_rate=decay_rate,
        peak_date=peak_date,
        factors=factors,
    )
