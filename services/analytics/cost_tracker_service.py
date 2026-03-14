"""
API 사용 비용 추적 서비스 (F6-05)
모델별 입력/출력 토큰 → 달러 비용 계산
"""
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any

from services.core.logging_config import ServiceLogger

logger = ServiceLogger('CostTrackerService')

# 모델별 1K 토큰 단가 (USD) — 최신 가격은 config.py 참조
_PRICE_TABLE: dict[str, dict[str, float]] = {
    'gemini/gemini-2.5-flash': {'input': 0.00015, 'output': 0.0006},
    'gemini/gemini-2.5-pro': {'input': 0.00125, 'output': 0.01},
    'deepseek/deepseek-chat': {'input': 0.00014, 'output': 0.00028},
    'deepseek/deepseek-reasoner': {'input': 0.00055, 'output': 0.00219},
    'zhipuai/GLM-4.7': {'input': 0.0005, 'output': 0.0005},
    'default': {'input': 0.001, 'output': 0.002},
}


class CostTrackerService:
    """API 토큰 소비 비용 추적"""

    def __init__(self):
        # 기록: [{timestamp, model, input_tokens, output_tokens, cost_usd, user_id}]
        self._records: list[dict] = []

    def record(self, model: str, input_tokens: int, output_tokens: int,
               user_id: str = '', timestamp: str | None = None) -> float:
        """토큰 사용 기록 + 비용 계산 후 반환 (USD)"""
        cost = self.calculate_cost(model, input_tokens, output_tokens)
        self._records.append({
            'timestamp': timestamp or datetime.now(timezone.utc).isoformat(),
            'model': model,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'cost_usd': cost,
            'user_id': user_id,
        })
        return cost

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """모델별 비용 계산 (USD)"""
        price = _PRICE_TABLE.get(model, _PRICE_TABLE['default'])
        cost = (input_tokens / 1000 * price['input']) + (output_tokens / 1000 * price['output'])
        return round(cost, 6)

    def get_total_cost(self, days: int | None = None) -> dict[str, Any]:
        """전체 또는 최근 N일 총 비용"""
        records = self._filter_by_days(days)
        total = sum(r['cost_usd'] for r in records)
        return {
            'period_days': days,
            'total_cost_usd': round(total, 4),
            'total_records': len(records),
        }

    def get_cost_by_model(self, days: int | None = None) -> list[dict]:
        """모델별 비용 집계"""
        records = self._filter_by_days(days)
        model_map: dict[str, list[dict]] = defaultdict(list)
        for r in records:
            model_map[r['model']].append(r)

        result = []
        for model, recs in sorted(model_map.items()):
            result.append({
                'model': model,
                'call_count': len(recs),
                'total_input_tokens': sum(r['input_tokens'] for r in recs),
                'total_output_tokens': sum(r['output_tokens'] for r in recs),
                'total_cost_usd': round(sum(r['cost_usd'] for r in recs), 4),
            })
        return result

    def get_cost_by_user(self, days: int | None = None) -> list[dict]:
        """사용자별 비용 집계"""
        records = self._filter_by_days(days)
        user_map: dict[str, float] = defaultdict(float)
        for r in records:
            user_map[r['user_id']] += r['cost_usd']
        return [
            {'user_id': uid, 'total_cost_usd': round(cost, 4)}
            for uid, cost in sorted(user_map.items(), key=lambda x: -x[1])
        ]

    def get_daily_cost(self, days: int = 30) -> list[dict]:
        """일별 비용 추세"""
        records = self._filter_by_days(days)
        daily: dict[str, float] = defaultdict(float)
        for r in records:
            day = r['timestamp'][:10]
            daily[day] += r['cost_usd']
        return [
            {'date': k, 'cost_usd': round(v, 4)}
            for k, v in sorted(daily.items())
        ]

    def _filter_by_days(self, days: int | None) -> list[dict]:
        if days is None:
            return self._records
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return [r for r in self._records if self._parse_ts(r['timestamp']) >= cutoff]

    @staticmethod
    def _parse_ts(ts: str) -> datetime:
        try:
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)
