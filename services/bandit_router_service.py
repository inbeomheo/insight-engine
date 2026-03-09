"""
밴딧 라우터 서비스

Multi-Armed Bandit 알고리즘(Epsilon-Greedy)을 사용하여
여러 변형에 트래픽을 동적으로 분배합니다.
성능이 좋은 변형에 더 많은 트래픽을 할당하면서도
탐색(exploration)을 유지합니다.
"""
import logging
import math
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class RoutedVariant:
    """트래픽이 할당된 변형"""
    variant_id: str
    allocated_traffic: int          # 배분된 트래픽 수
    expected_reward: float          # 예상 보상 (0.0~1.0)


@dataclass
class RoutingPlan:
    """트래픽 라우팅 계획"""
    variants: List[RoutedVariant] = field(default_factory=list)
    algorithm: str = 'epsilon-greedy'
    exploration_rate: float = 0.1   # 탐색 비율 (epsilon)


# 기본 설정
_DEFAULT_EPSILON = 0.1   # 10% 탐색
_MIN_EPSILON = 0.01      # 최소 탐색 비율
_MAX_EPSILON = 0.5       # 최대 탐색 비율


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


def _compute_reward(variant: dict) -> float:
    """변형의 예상 보상을 계산합니다."""
    # reward가 직접 있으면 사용
    if 'reward' in variant:
        return max(_safe_float(variant['reward']), 0.0)
    if 'expected_reward' in variant:
        return max(_safe_float(variant['expected_reward']), 0.0)

    # 성공/시도 비율로 계산
    successes = _safe_int(variant.get('successes', variant.get('conversions', 0)))
    trials = _safe_int(variant.get('trials', variant.get('impressions', 0)))
    if trials > 0:
        return successes / trials

    # 메트릭 값 직접 사용
    return max(_safe_float(variant.get('metric_value', variant.get('engagement', 0))), 0.0)


def _calculate_epsilon(variants: list) -> float:
    """변형 데이터 기반으로 적정 epsilon을 계산합니다."""
    # 데이터가 적으면 탐색 비율 높임
    total_trials = sum(
        _safe_int(v.get('trials', v.get('impressions', 0)))
        for v in variants
    )
    if total_trials == 0:
        return _MAX_EPSILON

    # 데이터가 많을수록 epsilon 감소 (로그 감소)
    per_variant = total_trials / max(len(variants), 1)
    if per_variant < 10:
        return _MAX_EPSILON
    if per_variant < 100:
        return 0.2
    if per_variant < 1000:
        return _DEFAULT_EPSILON

    return _MIN_EPSILON


def _allocate_epsilon_greedy(
    variants: list,
    traffic: int,
    epsilon: float,
) -> list:
    """Epsilon-Greedy 알고리즘으로 트래픽을 분배합니다."""
    n = len(variants)
    if n == 0:
        return []

    # 각 변형의 보상 계산
    rewards = [(i, _compute_reward(v)) for i, v in enumerate(variants)]
    rewards.sort(key=lambda x: x[1], reverse=True)

    # 탐색 트래픽 (epsilon 비율)
    explore_traffic = max(int(traffic * epsilon), n)  # 최소 변형 수만큼
    explore_per_variant = explore_traffic // n
    explore_remainder = explore_traffic - explore_per_variant * n

    # 활용 트래픽 (나머지 → 최고 보상 변형에 집중)
    exploit_traffic = traffic - explore_traffic

    allocations = [0] * n
    # 탐색: 균등 분배
    for i in range(n):
        allocations[i] += explore_per_variant
    # 탐색 나머지: 상위 변형부터
    for i in range(explore_remainder):
        idx = rewards[i % n][0]
        allocations[idx] += 1

    # 활용: 보상 비례 분배
    total_reward = sum(r for _, r in rewards)
    if total_reward > 0:
        for orig_idx, reward in rewards:
            share = reward / total_reward
            allocations[orig_idx] += int(exploit_traffic * share)
    else:
        # 보상 데이터 없으면 균등 분배
        per = exploit_traffic // n
        for i in range(n):
            allocations[i] += per
        # 나머지 1위에게
        if exploit_traffic % n > 0:
            allocations[rewards[0][0]] += exploit_traffic % n

    # 총합 보정 (반올림 오차)
    total_allocated = sum(allocations)
    diff = traffic - total_allocated
    if diff != 0:
        allocations[rewards[0][0]] += diff

    return allocations


def route_content(variants: list, traffic: int) -> RoutingPlan:
    """Multi-Armed Bandit으로 변형에 트래픽을 분배합니다.

    Args:
        variants: 변형 딕셔너리 리스트. 각 항목에
                  id(또는 variant_id), reward(또는 successes/trials),
                  metric_value 등 포함.
        traffic: 분배할 총 트래픽 수

    Returns:
        RoutingPlan (알고리즘, 탐색 비율, 변형별 트래픽 할당)
    """
    if not variants or traffic <= 0:
        return RoutingPlan(
            variants=[],
            algorithm='epsilon-greedy',
            exploration_rate=_DEFAULT_EPSILON,
        )

    epsilon = _calculate_epsilon(variants)
    allocations = _allocate_epsilon_greedy(variants, traffic, epsilon)

    routed = []
    for i, v in enumerate(variants):
        vid = str(v.get('id', v.get('variant_id', f'variant_{i}')))
        reward = _compute_reward(v)
        routed.append(RoutedVariant(
            variant_id=vid,
            allocated_traffic=allocations[i],
            expected_reward=round(reward, 4),
        ))

    # 할당량 내림차순 정렬
    routed.sort(key=lambda r: r.allocated_traffic, reverse=True)

    return RoutingPlan(
        variants=routed,
        algorithm='epsilon-greedy',
        exploration_rate=round(epsilon, 4),
    )
