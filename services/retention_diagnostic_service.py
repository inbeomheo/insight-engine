"""
청취 유지율 진단 서비스 (T12.4)
에피소드의 retention curve를 분석하여 이탈 구간과 원인을 진단합니다.
"""
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 급락 감지 임계치 (%)
DROP_THRESHOLD = 10.0

# 등급 기준 (평균 유지율 %)
GRADE_THRESHOLDS = {
    'S': 80.0,
    'A': 65.0,
    'B': 50.0,
    'C': 35.0,
    # 35% 미만: D
}

# 이탈 원인 추정 규칙
CAUSE_RULES = {
    'intro_too_long': {
        'max_time_seconds': 60,
        'description': '인트로가 너무 김 — 60초 이내 핵심 전달 필요',
    },
    'content_shift': {
        'description': '주제 전환 구간 — 부드러운 전환 필요',
    },
    'boring_section': {
        'description': '지루한 구간 — 예시/이야기/시각 자료 추가 필요',
    },
    'abrupt_ending': {
        'min_time_ratio': 0.85,
        'description': '갑작스러운 종료 — 마무리 구간 강화 필요',
    },
}


@dataclass
class DropPoint:
    """유지율 급락 지점"""
    timestamp: str
    retention_before: float
    retention_after: float
    drop_amount: float
    likely_cause: str


@dataclass
class RetentionDiagnosis:
    """유지율 진단 결과"""
    episode_id: str
    avg_retention: float
    drop_points: list[DropPoint] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    grade: str = 'C'


def _parse_time_to_seconds(time_str: str) -> float:
    """시간 문자열을 초로 변환합니다. (MM:SS 또는 HH:MM:SS)"""
    parts = time_str.strip().split(':')
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0.0


def _calculate_grade(avg_retention: float) -> str:
    """평균 유지율로 등급을 결정합니다."""
    for grade, threshold in GRADE_THRESHOLDS.items():
        if avg_retention >= threshold:
            return grade
    return 'D'


def _infer_cause(
    timestamp: str,
    total_duration_seconds: float,
    drop_amount: float,
    position_index: int,
    total_points: int,
) -> str:
    """급락 원인을 추정합니다."""
    time_seconds = _parse_time_to_seconds(timestamp)

    # 초반 60초 이내 급락 → 인트로가 너무 김
    if time_seconds <= CAUSE_RULES['intro_too_long']['max_time_seconds']:
        return 'intro_too_long'

    # 전체 길이의 85% 이후 급락 → 갑작스러운 종료
    if total_duration_seconds > 0:
        ratio = time_seconds / total_duration_seconds
        if ratio >= CAUSE_RULES['abrupt_ending']['min_time_ratio']:
            return 'abrupt_ending'

    # 큰 급락 (20%+) → 주제 전환
    if drop_amount >= 20.0:
        return 'content_shift'

    # 그 외 → 지루한 구간
    return 'boring_section'


def _generate_recommendations(
    drop_points: list[DropPoint],
    avg_retention: float,
    grade: str,
) -> list[str]:
    """진단 결과에 기반한 개선 권고를 생성합니다."""
    recommendations = []

    # 등급별 전체 권고
    if grade in ('D', 'C'):
        recommendations.append(
            f"평균 유지율이 {avg_retention:.1f}%로 낮습니다. "
            "전반적인 구성 재검토가 필요합니다."
        )

    # 원인별 권고
    causes = [dp.likely_cause for dp in drop_points]

    if 'intro_too_long' in causes:
        recommendations.append(CAUSE_RULES['intro_too_long']['description'])

    if 'content_shift' in causes:
        recommendations.append(CAUSE_RULES['content_shift']['description'])

    if 'boring_section' in causes:
        recommendations.append(CAUSE_RULES['boring_section']['description'])

    if 'abrupt_ending' in causes:
        recommendations.append(CAUSE_RULES['abrupt_ending']['description'])

    # 급락 지점이 많으면 추가 권고
    if len(drop_points) >= 3:
        recommendations.append(
            f"급락 구간이 {len(drop_points)}개로 많습니다. "
            "콘텐츠 길이를 줄이거나 구간별 흥미 요소를 추가하세요."
        )

    if not recommendations:
        recommendations.append("유지율이 양호합니다. 현재 구성을 유지하세요.")

    return recommendations


def diagnose_retention(episode_data: dict) -> RetentionDiagnosis:
    """에피소드의 청취 유지율을 진단합니다.

    Args:
        episode_data: {
            "episode_id": "ep-001",
            "retention_curve": [
                {"time": "00:00", "retention": 100},
                {"time": "01:00", "retention": 85},
                ...
            ]
        }

    Returns:
        RetentionDiagnosis: 진단 결과

    Raises:
        ValueError: episode_data가 유효하지 않을 때
    """
    if not episode_data:
        raise ValueError("episode_data는 필수입니다")

    episode_id = episode_data.get('episode_id', '')
    if not episode_id:
        raise ValueError("episode_id는 필수입니다")

    curve = episode_data.get('retention_curve', [])
    if not curve or len(curve) < 2:
        raise ValueError("retention_curve에 최소 2개 데이터 포인트가 필요합니다")

    # 전체 에피소드 길이 추정
    last_time = curve[-1].get('time', '00:00')
    total_duration = _parse_time_to_seconds(last_time)

    # 평균 유지율 계산
    retention_values = [point.get('retention', 0) for point in curve]
    avg_retention = round(sum(retention_values) / len(retention_values), 1)

    # 급락 지점 탐지
    drop_points = []
    for i in range(1, len(curve)):
        prev = curve[i - 1]
        curr = curve[i]

        ret_before = float(prev.get('retention', 0))
        ret_after = float(curr.get('retention', 0))
        drop_amount = ret_before - ret_after

        if drop_amount >= DROP_THRESHOLD:
            cause = _infer_cause(
                timestamp=curr.get('time', '00:00'),
                total_duration_seconds=total_duration,
                drop_amount=drop_amount,
                position_index=i,
                total_points=len(curve),
            )

            drop_points.append(DropPoint(
                timestamp=curr.get('time', '00:00'),
                retention_before=ret_before,
                retention_after=ret_after,
                drop_amount=round(drop_amount, 1),
                likely_cause=cause,
            ))

    grade = _calculate_grade(avg_retention)
    recommendations = _generate_recommendations(drop_points, avg_retention, grade)

    diagnosis = RetentionDiagnosis(
        episode_id=episode_id,
        avg_retention=avg_retention,
        drop_points=drop_points,
        recommendations=recommendations,
        grade=grade,
    )

    logger.info(
        f"유지율 진단: episode={episode_id}, "
        f"평균={avg_retention}%, 등급={grade}, 급락={len(drop_points)}개"
    )
    return diagnosis
