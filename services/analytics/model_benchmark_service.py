"""
모델별 성능 비교 서비스 (F6-14)
프로바이더/모델별 속도 / 비용 / 품질 벤치마크
"""
from collections import defaultdict
from typing import Any

from services.logging_config import ServiceLogger

logger = ServiceLogger('ModelBenchmarkService')


class ModelBenchmarkService:
    """AI 모델 성능 벤치마크 집계"""

    def __init__(self):
        # model → [{duration_ms, input_tokens, output_tokens, cost_usd, quality_score, success}]
        self._data: dict[str, list[dict]] = defaultdict(list)

    def record(self, model: str, duration_ms: float, input_tokens: int,
               output_tokens: int, cost_usd: float = 0.0, quality_score: float = 0.0,
               success: bool = True) -> None:
        """모델 호출 벤치마크 기록"""
        self._data[model].append({
            'duration_ms': duration_ms,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'cost_usd': cost_usd,
            'quality_score': quality_score,
            'success': success,
        })

    def get_benchmark(self) -> list[dict]:
        """전체 모델 벤치마크 비교"""
        result = []
        for model, records in self._data.items():
            n = len(records)
            successes = [r for r in records if r['success']]
            ns = len(successes)
            result.append({
                'model': model,
                'call_count': n,
                'success_rate': round(ns / n * 100, 1) if n > 0 else 0,
                'avg_duration_ms': round(
                    sum(r['duration_ms'] for r in successes) / ns, 1
                ) if ns > 0 else 0,
                'avg_output_tokens': round(
                    sum(r['output_tokens'] for r in successes) / ns, 0
                ) if ns > 0 else 0,
                'avg_cost_usd': round(
                    sum(r['cost_usd'] for r in records) / n, 6
                ),
                'avg_quality': round(
                    sum(r['quality_score'] for r in successes) / ns, 2
                ) if ns > 0 else 0,
                'tokens_per_sec': self._tokens_per_sec(successes),
            })
        result.sort(key=lambda x: -x['avg_quality'])
        return result

    def get_model_detail(self, model: str) -> dict[str, Any]:
        """특정 모델 상세 통계"""
        records = self._data.get(model, [])
        if not records:
            return {'model': model, 'count': 0}
        n = len(records)
        durations = [r['duration_ms'] for r in records if r['success']]
        costs = [r['cost_usd'] for r in records]
        return {
            'model': model,
            'count': n,
            'avg_duration_ms': round(sum(durations) / len(durations), 1) if durations else 0,
            'min_duration_ms': round(min(durations), 1) if durations else 0,
            'max_duration_ms': round(max(durations), 1) if durations else 0,
            'total_cost_usd': round(sum(costs), 4),
        }

    def rank_by(self, metric: str = 'avg_quality') -> list[dict]:
        """특정 지표 기준 모델 순위"""
        benchmark = self.get_benchmark()
        reverse = metric not in {'avg_duration_ms', 'avg_cost_usd'}
        benchmark.sort(key=lambda x: x.get(metric, 0), reverse=reverse)
        return [{'rank': i + 1, **b} for i, b in enumerate(benchmark)]

    @staticmethod
    def _tokens_per_sec(records: list[dict]) -> float:
        if not records:
            return 0.0
        total_tokens = sum(r['output_tokens'] for r in records)
        total_ms = sum(r['duration_ms'] for r in records)
        if total_ms == 0:
            return 0.0
        return round(total_tokens / (total_ms / 1000), 1)
