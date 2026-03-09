"""
콘텐츠 일몰 서비스

오래된 콘텐츠의 일몰(sunset) 계획을 생성합니다.
나이, 교체 URL 유무, 콘텐츠 유형에 따라
적절한 조치(리다이렉트, 아카이브, 업데이트 등)를 권장.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

logger = logging.getLogger(__name__)

# 나이 기준 (일)
_AGE_THRESHOLDS = {
    "fresh": 90,       # 3개월 이내: 아직 신선
    "mature": 180,     # 6개월: 점검 필요
    "aging": 365,      # 1년: 업데이트 권장
    "stale": 730,      # 2년: 일몰 고려
}

# 나이대별 기본 액션
_AGE_ACTIONS: dict[str, list[str]] = {
    "fresh": [
        "현재 콘텐츠는 신선합니다. 정기 점검만 진행하세요.",
    ],
    "mature": [
        "통계/수치 데이터를 최신화하세요.",
        "외부 링크 유효성을 확인하세요.",
        "최근 트렌드 반영 여부를 점검하세요.",
    ],
    "aging": [
        "콘텐츠를 전면 업데이트하거나 리라이트하세요.",
        "검색 순위 변동을 확인하고 SEO를 재최적화하세요.",
        "낡은 스크린샷/이미지를 교체하세요.",
        "댓글에서 언급된 오류를 수정하세요.",
    ],
    "stale": [
        "콘텐츠 아카이브를 고려하세요.",
        "대체 콘텐츠가 있으면 301 리다이렉트를 설정하세요.",
        "검색 유입이 여전히 있다면 핵심 정보만 남기고 축소하세요.",
        "noindex 태그 추가를 검토하세요.",
    ],
}


@dataclass
class SunsetPlan:
    """콘텐츠 일몰 계획"""
    content_id: str
    sunset_date: str              # ISO 형식
    actions: List[str]            # 권장 조치 리스트
    replacement_url: Optional[str] = None
    age_category: str = ""        # "fresh" | "mature" | "aging" | "stale"
    urgency: str = ""             # "low" | "medium" | "high"


def _categorize_age(age_days: int) -> str:
    """나이(일)를 카테고리로 분류."""
    if age_days < _AGE_THRESHOLDS["fresh"]:
        return "fresh"
    elif age_days < _AGE_THRESHOLDS["mature"]:
        return "mature"
    elif age_days < _AGE_THRESHOLDS["aging"]:
        return "aging"
    else:
        return "stale"


def _determine_urgency(age_category: str, has_replacement: bool) -> str:
    """긴급도 결정."""
    if age_category == "stale":
        return "high"
    elif age_category == "aging":
        return "high" if has_replacement else "medium"
    elif age_category == "mature":
        return "medium" if has_replacement else "low"
    else:
        return "low"


def _calculate_sunset_date(age_days: int, age_category: str) -> str:
    """일몰 예정일 계산.

    카테고리별로 다른 유예 기간을 적용.
    """
    grace_periods = {
        "fresh": 365,    # 1년 후 재점검
        "mature": 180,   # 6개월 후
        "aging": 90,     # 3개월 후
        "stale": 30,     # 1개월 후 (즉시 조치 권장)
    }
    grace_days = grace_periods.get(age_category, 90)
    sunset = datetime.now() + timedelta(days=grace_days)
    return sunset.strftime("%Y-%m-%d")


def _build_actions(
    age_category: str,
    replacement_url: str | None,
) -> list[str]:
    """카테고리 + 교체 URL 유무에 따른 액션 목록 생성."""
    actions = list(_AGE_ACTIONS.get(age_category, []))

    if replacement_url:
        actions.insert(0, f"대체 콘텐츠로 301 리다이렉트 설정: {replacement_url}")
        if age_category in ("aging", "stale"):
            actions.append("기존 URL에 '이 콘텐츠는 업데이트되었습니다' 배너를 표시하세요.")

    return actions


def plan_sunset(
    content_id: str,
    replacement_url: str | None = None,
    age_days: int = 365,
) -> SunsetPlan:
    """콘텐츠 일몰 계획 생성.

    Args:
        content_id: 콘텐츠 식별자
        replacement_url: 대체 콘텐츠 URL (없으면 None)
        age_days: 콘텐츠 나이 (일 단위, 기본 365일)

    Returns:
        SunsetPlan: 일몰 예정일, 권장 조치, 긴급도 포함
    """
    if not content_id or not content_id.strip():
        logger.warning("빈 content_id")
        return SunsetPlan(
            content_id="",
            sunset_date=datetime.now().strftime("%Y-%m-%d"),
            actions=["유효한 콘텐츠 ID를 입력하세요."],
            age_category="",
            urgency="low",
        )

    # 음수 나이는 0으로 보정
    age_days = max(age_days, 0)

    age_category = _categorize_age(age_days)
    has_replacement = bool(replacement_url and replacement_url.strip())
    urgency = _determine_urgency(age_category, has_replacement)
    sunset_date = _calculate_sunset_date(age_days, age_category)
    actions = _build_actions(age_category, replacement_url if has_replacement else None)

    logger.info(
        "일몰 계획: id=%s, age=%d일, category=%s, urgency=%s",
        content_id, age_days, age_category, urgency,
    )

    return SunsetPlan(
        content_id=content_id.strip(),
        sunset_date=sunset_date,
        actions=actions,
        replacement_url=replacement_url.strip() if has_replacement else None,
        age_category=age_category,
        urgency=urgency,
    )


def get_urgency_label_kr(urgency: str) -> str:
    """긴급도를 한국어 라벨로 변환."""
    labels = {"low": "낮음", "medium": "보통", "high": "높음"}
    return labels.get(urgency, urgency)
