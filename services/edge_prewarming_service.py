"""
에지 프리워밍 서비스.

CDN 에지 노드 캐시 워밍 전략을 수립한다.
"""

from dataclasses import dataclass, field
import uuid


@dataclass
class EdgeNode:
    """에지 노드"""
    node_id: str = ""
    region: str = ""
    capacity_mb: float = 1000.0
    current_usage_mb: float = 0.0
    latency_ms: float = 50.0


@dataclass
class WarmingPlan:
    """워밍 계획"""
    content_id: str = ""
    target_nodes: list = field(default_factory=list)
    priority: int = 1
    estimated_time_ms: float = 0.0


def select_nodes(
    nodes: list,
    content_size_mb: float,
    max_nodes: int = 5
) -> list:
    """
    최적 노드 선택.

    잔여 용량이 충분하고 지연이 낮은 노드를 우선 선택한다.
    """
    # 잔여 용량이 content_size_mb 이상인 노드만 필터
    eligible = [
        n for n in nodes
        if (n.capacity_mb - n.current_usage_mb) >= content_size_mb
    ]

    # 지연시간 오름차순 정렬
    eligible.sort(key=lambda n: n.latency_ms)

    return eligible[:max_nodes]


def create_warming_plan(
    content_id: str,
    content_size: float,
    nodes: list
) -> WarmingPlan:
    """워밍 계획 생성"""
    selected = select_nodes(nodes, content_size)
    target_ids = [n.node_id for n in selected]

    # 우선순위: 콘텐츠 크기 기반 (큰 콘텐츠일수록 높은 우선순위)
    if content_size > 100:
        priority = 1
    elif content_size > 10:
        priority = 2
    else:
        priority = 3

    estimated_time = estimate_warming_time_from_nodes(content_size, selected)

    return WarmingPlan(
        content_id=content_id,
        target_nodes=target_ids,
        priority=priority,
        estimated_time_ms=round(estimated_time, 2),
    )


def estimate_warming_time(plan: WarmingPlan, nodes: list) -> float:
    """워밍 예상 시간 (ms)"""
    return plan.estimated_time_ms


def estimate_warming_time_from_nodes(content_size: float, target_nodes: list) -> float:
    """노드 리스트 기반 워밍 예상 시간"""
    if not target_nodes:
        return 0.0

    # 병렬 전송이므로 가장 느린 노드가 병목
    # 전송 시간 = 콘텐츠 크기 / 대역폭(가정: 100MB/s) + 노드 지연
    transfer_time_ms = (content_size / 100) * 1000  # MB → ms 변환

    max_total = 0.0
    for node in target_nodes:
        total = node.latency_ms + transfer_time_ms
        max_total = max(max_total, total)

    return max_total


def get_node_utilization(nodes: list) -> dict:
    """노드별 사용률"""
    result = {}
    for node in nodes:
        utilization = node.current_usage_mb / node.capacity_mb if node.capacity_mb > 0 else 0.0
        result[node.node_id] = {
            "region": node.region,
            "capacity_mb": node.capacity_mb,
            "used_mb": node.current_usage_mb,
            "free_mb": round(node.capacity_mb - node.current_usage_mb, 2),
            "utilization": round(utilization, 4),
        }
    return result
