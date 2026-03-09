"""
vLLM 서빙 시뮬레이션 서비스.

PagedAttention + 추측 디코딩 + KV 캐시 오프로딩을 시뮬레이션한다.
"""

from dataclasses import dataclass, field
from typing import Optional
import uuid
import math


@dataclass
class ServingConfig:
    """서빙 설정"""
    model_name: str
    max_batch_size: int = 32
    gpu_memory_gb: float = 24.0
    kv_cache_size: int = 2048
    speculative_draft_model: Optional[str] = None


@dataclass
class ServingMetrics:
    """서빙 메트릭"""
    requests_processed: int = 0
    avg_latency_ms: float = 0.0
    throughput_tps: float = 0.0
    cache_hit_rate: float = 0.0
    gpu_utilization: float = 0.0


@dataclass
class InferenceRequest:
    """추론 요청"""
    request_id: str = ""
    prompt: str = ""
    max_tokens: int = 256
    temperature: float = 0.7


def create_config(
    model_name: str,
    batch_size: int = 32,
    gpu_memory: float = 24.0
) -> ServingConfig:
    """서빙 설정 생성"""
    if not model_name:
        raise ValueError("model_name은 필수입니다")
    if batch_size <= 0:
        raise ValueError("batch_size는 양수여야 합니다")
    if gpu_memory <= 0:
        raise ValueError("gpu_memory는 양수여야 합니다")

    return ServingConfig(
        model_name=model_name,
        max_batch_size=batch_size,
        gpu_memory_gb=gpu_memory,
        kv_cache_size=int(gpu_memory * 128),  # GPU 메모리 비례 KV 캐시
    )


def estimate_throughput(config: ServingConfig, request_count: int) -> ServingMetrics:
    """
    처리량 추정.

    배치 크기와 GPU 메모리 기반으로 처리량을 시뮬레이션한다.
    """
    if request_count <= 0:
        return ServingMetrics()

    # GPU 메모리 기반 기본 처리 속도 (tokens/sec)
    base_tps = config.gpu_memory_gb * 50  # 24GB → 1200 tps 기준

    # 배치 효율: 배치 크기가 클수록 처리량 증가 (로그 스케일)
    batch_efficiency = min(1.0, math.log2(max(1, config.max_batch_size)) / 5.0)
    effective_tps = base_tps * (0.5 + 0.5 * batch_efficiency)

    # 추측 디코딩 시 추가 가속
    if config.speculative_draft_model:
        effective_tps *= 1.4  # 약 40% 가속

    # 배치당 처리 수
    batches_needed = math.ceil(request_count / config.max_batch_size)
    avg_tokens_per_request = 256  # 가정

    # 지연시간 계산
    total_tokens = request_count * avg_tokens_per_request
    total_time_s = total_tokens / effective_tps
    avg_latency_ms = (total_time_s / request_count) * 1000

    # GPU 활용률: 배치 채움률 기반
    last_batch_fill = (request_count % config.max_batch_size) or config.max_batch_size
    avg_fill = ((batches_needed - 1) * config.max_batch_size + last_batch_fill) / (batches_needed * config.max_batch_size)
    gpu_utilization = min(0.95, avg_fill * 0.9)

    # 캐시 히트율: 요청 수 많을수록 히트율 상승
    cache_hit_rate = min(0.9, 0.1 + (request_count / (request_count + 100)) * 0.8)

    return ServingMetrics(
        requests_processed=request_count,
        avg_latency_ms=round(avg_latency_ms, 2),
        throughput_tps=round(effective_tps, 2),
        cache_hit_rate=round(cache_hit_rate, 4),
        gpu_utilization=round(gpu_utilization, 4),
    )


def simulate_speculative_decode(
    draft_tokens: list[str],
    target_tokens: list[str]
) -> dict:
    """
    추측 디코딩 시뮬레이션.

    드래프트 모델이 생성한 토큰과 타깃 모델 토큰의 일치율로
    acceptance_rate와 speedup을 계산한다.
    """
    if not draft_tokens or not target_tokens:
        return {
            "acceptance_rate": 0.0,
            "accepted_count": 0,
            "total_draft": len(draft_tokens),
            "speedup": 1.0,
        }

    # 일치하는 토큰 수 계산 (순서대로)
    accepted = 0
    for d, t in zip(draft_tokens, target_tokens):
        if d == t:
            accepted += 1
        else:
            break  # 첫 불일치에서 중단 (연속 일치만 카운트)

    acceptance_rate = accepted / len(draft_tokens) if draft_tokens else 0.0

    # 가속 계산: 수락된 토큰만큼 타깃 모델 호출 절약
    # 드래프트 모델은 타깃의 1/10 비용이라고 가정
    draft_cost = len(draft_tokens) * 0.1
    target_cost_without = len(draft_tokens) * 1.0
    target_cost_with = (len(draft_tokens) - accepted) * 1.0 + draft_cost

    speedup = target_cost_without / target_cost_with if target_cost_with > 0 else 1.0

    return {
        "acceptance_rate": round(acceptance_rate, 4),
        "accepted_count": accepted,
        "total_draft": len(draft_tokens),
        "speedup": round(speedup, 4),
    }


def manage_kv_cache(
    cache_size: int,
    active_requests: int,
    eviction_policy: str = "lru"
) -> dict:
    """
    KV 캐시 관리.

    캐시 용량과 활성 요청에 따라 할당/해제를 시뮬레이션한다.
    eviction_policy: 'lru' 또는 'fifo'
    """
    if eviction_policy not in ("lru", "fifo"):
        raise ValueError(f"지원하지 않는 eviction_policy: {eviction_policy}")

    if cache_size <= 0:
        raise ValueError("cache_size는 양수여야 합니다")

    # 요청당 KV 캐시 슬롯 (평균 토큰 수 기반)
    slots_per_request = 64
    required_slots = active_requests * slots_per_request

    allocated = min(required_slots, cache_size)
    evicted = max(0, required_slots - cache_size)
    utilization = allocated / cache_size if cache_size > 0 else 0.0

    return {
        "total_slots": cache_size,
        "allocated_slots": allocated,
        "free_slots": max(0, cache_size - allocated),
        "evicted_entries": evicted,
        "utilization": round(utilization, 4),
        "eviction_policy": eviction_policy,
        "can_accept_more": allocated < cache_size,
    }


def calculate_memory_usage(config: ServingConfig) -> dict:
    """
    GPU 메모리 사용량 추정.

    모델 가중치, KV 캐시, 활성화 메모리를 분리 계산한다.
    """
    total_memory = config.gpu_memory_gb

    # 모델 크기 추정 (이름 기반 휴리스틱)
    model_name_lower = config.model_name.lower()
    if "70b" in model_name_lower:
        model_weight_gb = 35.0  # FP16 기준
    elif "13b" in model_name_lower:
        model_weight_gb = 6.5
    elif "7b" in model_name_lower:
        model_weight_gb = 3.5
    elif "3b" in model_name_lower:
        model_weight_gb = 1.5
    else:
        model_weight_gb = 3.5  # 기본값

    # KV 캐시 메모리: 슬롯당 약 0.5MB
    kv_cache_gb = (config.kv_cache_size * 0.5) / 1024

    # 활성화 메모리: 배치 크기 비례
    activation_gb = config.max_batch_size * 0.05

    used_gb = model_weight_gb + kv_cache_gb + activation_gb
    free_gb = max(0, total_memory - used_gb)

    return {
        "total_gb": total_memory,
        "model_weights_gb": round(model_weight_gb, 2),
        "kv_cache_gb": round(kv_cache_gb, 2),
        "activation_gb": round(activation_gb, 2),
        "used_gb": round(used_gb, 2),
        "free_gb": round(free_gb, 2),
        "utilization": round(min(1.0, used_gb / total_memory), 4),
        "fits_in_memory": used_gb <= total_memory,
    }
