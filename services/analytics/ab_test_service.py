"""
A/B 테스트 결과 추적 서비스 (F6-10)
A/B 테스트 정의 / 이벤트 기록 / 통계적 유의성 계산
"""
import math
import uuid
from datetime import datetime, timezone
from typing import Any

from services.core.logging_config import ServiceLogger

logger = ServiceLogger('ABTestService')


class ABTestService:
    """A/B 테스트 관리 및 결과 분석"""

    def __init__(self):
        # test_id → {name, variants, events: []}
        self._tests: dict[str, dict] = {}

    def create_test(self, name: str, variants: list[str]) -> str:
        """A/B 테스트 생성 후 test_id 반환"""
        if len(variants) < 2:
            raise ValueError('variants는 최소 2개 이상이어야 합니다.')
        test_id = str(uuid.uuid4())[:8]
        self._tests[test_id] = {
            'test_id': test_id,
            'name': name,
            'variants': variants,
            'events': [],
            'created_at': datetime.now(timezone.utc).isoformat(),
            'active': True,
        }
        logger.info(f'A/B 테스트 생성: {name} ({test_id})')
        return test_id

    def record_exposure(self, test_id: str, variant: str, user_id: str = '') -> None:
        """노출 이벤트 기록"""
        self._record_event(test_id, variant, 'exposure', user_id)

    def record_conversion(self, test_id: str, variant: str, user_id: str = '') -> None:
        """전환 이벤트 기록"""
        self._record_event(test_id, variant, 'conversion', user_id)

    def get_results(self, test_id: str) -> dict[str, Any]:
        """테스트 결과 및 통계적 유의성 반환"""
        test = self._tests.get(test_id)
        if not test:
            return {'error': f'테스트 없음: {test_id}'}

        variant_stats: dict[str, dict] = {}
        for variant in test['variants']:
            exposures = sum(
                1 for e in test['events']
                if e['variant'] == variant and e['event_type'] == 'exposure'
            )
            conversions = sum(
                1 for e in test['events']
                if e['variant'] == variant and e['event_type'] == 'conversion'
            )
            cvr = conversions / exposures if exposures > 0 else 0.0
            variant_stats[variant] = {
                'exposures': exposures,
                'conversions': conversions,
                'cvr': round(cvr * 100, 2),
            }

        significance = self._calculate_significance(variant_stats, test['variants'])

        return {
            'test_id': test_id,
            'name': test['name'],
            'variants': variant_stats,
            'p_value': significance.get('p_value'),
            'significant': significance.get('significant', False),
            'winner': significance.get('winner'),
            'created_at': test['created_at'],
        }

    def list_tests(self) -> list[dict]:
        """전체 테스트 목록"""
        return [
            {
                'test_id': t['test_id'],
                'name': t['name'],
                'variants': t['variants'],
                'active': t['active'],
                'created_at': t['created_at'],
                'total_events': len(t['events']),
            }
            for t in self._tests.values()
        ]

    def stop_test(self, test_id: str) -> bool:
        """테스트 종료"""
        if test_id in self._tests:
            self._tests[test_id]['active'] = False
            return True
        return False

    def _record_event(self, test_id: str, variant: str, event_type: str, user_id: str) -> None:
        test = self._tests.get(test_id)
        if not test:
            logger.warning(f'존재하지 않는 테스트 ID: {test_id}')
            return
        if variant not in test['variants']:
            logger.warning(f'정의되지 않은 변형: {variant}')
            return
        test['events'].append({
            'variant': variant,
            'event_type': event_type,
            'user_id': user_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })

    @staticmethod
    def _calculate_significance(stats: dict[str, dict], variants: list[str]) -> dict:
        """이항 비율 z-검정 (두 변형 간 전환율 차이)"""
        if len(variants) < 2:
            return {}
        a, b = variants[0], variants[1]
        sa, sb = stats.get(a, {}), stats.get(b, {})
        n1, c1 = sa.get('exposures', 0), sa.get('conversions', 0)
        n2, c2 = sb.get('exposures', 0), sb.get('conversions', 0)

        if n1 == 0 or n2 == 0:
            return {'p_value': None, 'significant': False, 'winner': None}

        p1, p2 = c1 / n1, c2 / n2
        p_pool = (c1 + c2) / (n1 + n2)
        se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
        if se == 0:
            return {'p_value': None, 'significant': False, 'winner': None}

        z = abs(p1 - p2) / se
        # 양측 검정 근사 p-value (정규분포 근사)
        p_value = 2 * (1 - _normal_cdf(z))
        significant = p_value < 0.05
        winner = a if p1 >= p2 else b if significant else None

        return {
            'p_value': round(p_value, 4),
            'significant': significant,
            'winner': winner,
        }


def _normal_cdf(z: float) -> float:
    """표준 정규분포 CDF 근사 (Abramowitz & Stegun)"""
    t = 1.0 / (1.0 + 0.2316419 * abs(z))
    poly = t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))))
    return 1.0 - (1 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * z * z) * poly
