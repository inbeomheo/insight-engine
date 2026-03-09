"""
실험 가속 서비스

진행 중인 실험(A/B 테스트 등)의 상태를 분석하여
실험 완료를 앞당기기 위한 권고 행동과 예상 완료 시점을 제공합니다.
"""
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AccelerationPlan:
    """실험 가속 계획"""
    experiment_id: str
    current_progress: float              # 현재 진행률 (0.0~1.0)
    recommended_actions: List[str] = field(default_factory=list)
    estimated_completion: str = ''       # ISO 날짜 형식 예상 완료일


# 권고 행동 템플릿
_ACTIONS = {
    'increase_traffic': '트래픽을 {pct}% 증가시키면 실험 기간을 단축할 수 있습니다',
    'reduce_variants': '성능이 낮은 변형을 제거하여 남은 변형에 트래픽을 집중하세요',
    'extend_hours': '피크 시간대(18~22시)에 트래픽을 집중 배분하세요',
    'early_stop': '현재 데이터로 통계적 유의성이 확보되어 조기 종료를 권고합니다',
    'wait': '충분한 표본이 모일 때까지 기다려야 합니다 (현재 {n}건/{target}건)',
    'add_metric': '보조 지표를 추가하여 다각도 분석을 권장합니다',
}


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _calculate_progress(data: dict) -> float:
    """실험 데이터에서 진행률을 계산합니다."""
    # 직접 progress 값이 있으면 사용
    if 'progress' in data:
        return min(max(_safe_float(data['progress']), 0.0), 1.0)

    # 표본 수 / 목표 표본 수 기반
    current = _safe_int(data.get('current_samples', data.get('sample_size', 0)))
    target = _safe_int(data.get('target_samples', data.get('required_samples', 0)))
    if target > 0:
        return min(current / target, 1.0)

    # 경과 시간 / 전체 기간 기반
    elapsed = _safe_float(data.get('elapsed_days', 0))
    total = _safe_float(data.get('total_days', 0))
    if total > 0:
        return min(elapsed / total, 1.0)

    return 0.0


def _estimate_completion(data: dict, progress: float) -> str:
    """예상 완료일을 추정합니다."""
    if progress >= 1.0:
        return datetime.now().strftime('%Y-%m-%d')

    if progress <= 0:
        # 진행률 0이면 기본 14일 후
        est = datetime.now() + timedelta(days=14)
        return est.strftime('%Y-%m-%d')

    # 현재 속도 기반 예측
    elapsed = _safe_float(data.get('elapsed_days', 0))
    if elapsed > 0:
        total_estimated = elapsed / progress
        remaining = total_estimated - elapsed
        est = datetime.now() + timedelta(days=max(remaining, 1))
        return est.strftime('%Y-%m-%d')

    # 표본 수 기반 예측
    current = _safe_int(data.get('current_samples', 0))
    target = _safe_int(data.get('target_samples', 0))
    daily_rate = _safe_float(data.get('daily_sample_rate', 0))
    if daily_rate > 0 and target > current:
        remaining_samples = target - current
        remaining_days = math.ceil(remaining_samples / daily_rate)
        est = datetime.now() + timedelta(days=remaining_days)
        return est.strftime('%Y-%m-%d')

    # 진행률 기반 기본 추정 (30일 전체 기준)
    remaining_pct = 1.0 - progress
    est = datetime.now() + timedelta(days=max(int(remaining_pct * 30), 1))
    return est.strftime('%Y-%m-%d')


def _generate_actions(data: dict, progress: float) -> list:
    """진행 상태에 따른 권고 행동을 생성합니다."""
    actions = []

    current = _safe_int(data.get('current_samples', 0))
    target = _safe_int(data.get('target_samples', 0))
    num_variants = _safe_int(data.get('num_variants', data.get('variants_count', 0)))
    confidence = _safe_float(data.get('confidence', 0))

    # 조기 종료 가능 여부
    if confidence >= 0.95 and progress >= 0.5:
        actions.append(_ACTIONS['early_stop'])
        return actions

    # 표본 부족
    if target > 0 and current < target:
        actions.append(_ACTIONS['wait'].format(n=current, target=target))

    # 진행률이 낮으면 트래픽 증가 권고
    if progress < 0.3:
        pct = int((0.5 - progress) * 100)
        actions.append(_ACTIONS['increase_traffic'].format(pct=max(pct, 20)))

    # 변형 수가 많으면 축소 권고
    if num_variants > 3 and progress > 0.3:
        actions.append(_ACTIONS['reduce_variants'])

    # 피크 시간대 집중
    if progress < 0.6:
        actions.append(_ACTIONS['extend_hours'])

    # 보조 지표 추가 권고 (변형이 2개 이하이고 진행률이 높을 때)
    if num_variants <= 2 and progress > 0.5:
        actions.append(_ACTIONS['add_metric'])

    return actions if actions else ['현재 실험이 정상적으로 진행 중입니다']


def accelerate_experiment(experiment_data: dict) -> AccelerationPlan:
    """실험 가속 계획을 생성합니다.

    Args:
        experiment_data: 실험 데이터 딕셔너리.
            - experiment_id (str): 실험 ID
            - progress (float, 선택): 직접 진행률 (0~1)
            - current_samples / target_samples (int): 표본 수
            - elapsed_days / total_days (float): 경과/전체 일수
            - daily_sample_rate (float): 일일 표본 수집률
            - num_variants (int): 변형 수
            - confidence (float): 현재 신뢰도

    Returns:
        AccelerationPlan
    """
    if not experiment_data:
        return AccelerationPlan(
            experiment_id='unknown',
            current_progress=0.0,
            recommended_actions=['실험 데이터가 없습니다'],
            estimated_completion='',
        )

    exp_id = str(experiment_data.get('experiment_id', experiment_data.get('id', 'unknown')))
    progress = _calculate_progress(experiment_data)
    actions = _generate_actions(experiment_data, progress)
    completion = _estimate_completion(experiment_data, progress)

    return AccelerationPlan(
        experiment_id=exp_id,
        current_progress=round(progress, 4),
        recommended_actions=actions,
        estimated_completion=completion,
    )
