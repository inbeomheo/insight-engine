"""
예산 인지형 멀티모델 게이트웨이 테스트

services/budget_gateway_service.py 의 핵심 기능을 검증:
- 예산 내/초과 시 라우팅
- 지출 추적 및 비용 계산
- 예산 현황 조회
- 한도 설정/업데이트
- 기간별 지출 집계
- 일일 초기화
- 최저가 프로바이더 조회
"""
import time
import pytest
from unittest.mock import patch

from services.budget_gateway_service import (
    route_request,
    track_spend,
    get_budget_status,
    set_budget_limits,
    get_total_spend,
    reset_daily_spend,
    get_cheapest_provider,
    _reset_all,
    _spend_records,
    _budget_limits,
    SpendRecord,
    BudgetLimit,
    BudgetReport,
    ProviderChoice,
)


@pytest.fixture(autouse=True)
def clean_state():
    """각 테스트 전후로 내부 상태 초기화"""
    _reset_all()
    yield
    _reset_all()


class TestRouteRequest:
    """route_request 함수 테스트"""

    def test_route_request_primary(self):
        """예산 내 기본 프로바이더 반환"""
        choice = route_request(prompt_tokens=1000, preferred_provider='gemini')

        assert choice.provider == 'gemini'
        assert choice.reason == 'primary'
        assert 'gemini' in choice.model

    def test_route_request_budget_exceeded(self):
        """예산 초과 시 저렴한 프로바이더로 fallback"""
        # gemini 예산 한도를 극소로 설정
        set_budget_limits('gemini', daily_limit=0.0001, monthly_limit=0.001)

        # gemini 지출 기록 (한도 초과)
        track_spend('gemini', 'gemini/gemini-3.1-flash-lite-preview',
                     tokens_in=100000, tokens_out=50000,
                     price_per_input=0.075, price_per_output=0.30)

        choice = route_request(prompt_tokens=1000, preferred_provider='gemini')

        # gemini 이외의 프로바이더로 fallback되어야 함
        assert choice.provider != 'gemini'
        assert choice.reason == 'budget_fallback'

    def test_route_request_no_limits(self):
        """한도 미설정 시 기본 프로바이더 반환 (무제한)"""
        # 한도 설정 없이 호출
        choice = route_request(prompt_tokens=5000, preferred_provider='deepseek')

        assert choice.provider == 'deepseek'
        assert choice.reason == 'primary'

    def test_route_request_default_provider(self):
        """preferred_provider 미지정 시 gemini 기본 선택"""
        choice = route_request(prompt_tokens=1000)

        assert choice.provider == 'gemini'
        assert choice.reason == 'primary'

    def test_route_request_with_budget_config(self):
        """budget_config 파라미터로 즉석 예산 설정"""
        route_request(
            prompt_tokens=1000,
            preferred_provider='deepseek',
            budget_config={'daily_limit': 5.0, 'monthly_limit': 50.0},
        )

        # 한도가 설정되었는지 확인
        assert 'deepseek' in _budget_limits
        assert _budget_limits['deepseek'].daily_limit == 5.0
        assert _budget_limits['deepseek'].monthly_limit == 50.0


class TestTrackSpend:
    """track_spend 함수 테스트"""

    def test_track_spend(self):
        """지출 기록이 정확하게 저장되는지 확인"""
        record = track_spend(
            provider='gemini',
            model='gemini/gemini-3.1-flash-lite-preview',
            tokens_in=10000,
            tokens_out=5000,
            price_per_input=0.075,
            price_per_output=0.30,
        )

        assert isinstance(record, SpendRecord)
        assert record.provider == 'gemini'
        assert record.model == 'gemini/gemini-3.1-flash-lite-preview'
        assert record.tokens_in == 10000
        assert record.tokens_out == 5000
        assert record.timestamp > 0
        assert len(_spend_records) == 1

    def test_track_spend_cost_calculation(self):
        """비용 계산 정확성: cost = (in * price_in + out * price_out) / 1M"""
        record = track_spend(
            provider='deepseek',
            model='deepseek/deepseek-chat',
            tokens_in=1_000_000,  # 1M tokens
            tokens_out=500_000,   # 0.5M tokens
            price_per_input=0.27,
            price_per_output=1.10,
        )

        # 예상: (1M * 0.27 + 0.5M * 1.10) / 1M = 0.27 + 0.55 = 0.82
        expected_cost = (1_000_000 * 0.27 + 500_000 * 1.10) / 1_000_000
        assert abs(record.cost - expected_cost) < 1e-9

    def test_track_spend_zero_price(self):
        """Ollama처럼 무료 프로바이더 비용 = 0"""
        record = track_spend(
            provider='ollama',
            model='ollama_chat/llama3.2',
            tokens_in=50000,
            tokens_out=10000,
            price_per_input=0.0,
            price_per_output=0.0,
        )

        assert record.cost == 0.0


class TestGetBudgetStatus:
    """get_budget_status 함수 테스트"""

    def test_get_budget_status_all(self):
        """전체 프로바이더 예산 현황 조회"""
        set_budget_limits('gemini', daily_limit=1.0, monthly_limit=10.0)
        set_budget_limits('deepseek', daily_limit=2.0, monthly_limit=20.0)

        # gemini 지출 기록
        track_spend('gemini', 'gemini/test', 10000, 5000,
                     price_per_input=0.075, price_per_output=0.30)

        reports = get_budget_status()

        assert len(reports) == 2
        providers = {r.provider for r in reports}
        assert providers == {'gemini', 'deepseek'}

        # gemini 보고서 확인
        gemini_report = next(r for r in reports if r.provider == 'gemini')
        assert gemini_report.daily_limit == 1.0
        assert gemini_report.monthly_limit == 10.0
        assert gemini_report.daily_spent > 0
        assert gemini_report.daily_remaining < 1.0

    def test_get_budget_status_specific(self):
        """특정 프로바이더만 조회"""
        set_budget_limits('gemini', daily_limit=1.0, monthly_limit=10.0)
        set_budget_limits('deepseek', daily_limit=2.0, monthly_limit=20.0)

        reports = get_budget_status(provider='gemini')

        assert len(reports) == 1
        assert reports[0].provider == 'gemini'
        assert reports[0].daily_limit == 1.0

    def test_get_budget_status_no_limits(self):
        """한도 미설정 프로바이더 조회 → 빈 목록"""
        reports = get_budget_status(provider='unknown')

        assert reports == []


class TestSetBudgetLimits:
    """set_budget_limits 함수 테스트"""

    def test_set_budget_limits(self):
        """한도 설정"""
        limit = set_budget_limits('gemini', daily_limit=5.0, monthly_limit=100.0)

        assert isinstance(limit, BudgetLimit)
        assert limit.provider == 'gemini'
        assert limit.daily_limit == 5.0
        assert limit.monthly_limit == 100.0
        assert 'gemini' in _budget_limits

    def test_set_budget_limits_update(self):
        """기존 한도 업데이트"""
        set_budget_limits('gemini', daily_limit=5.0, monthly_limit=100.0)
        updated = set_budget_limits('gemini', daily_limit=10.0, monthly_limit=200.0)

        assert updated.daily_limit == 10.0
        assert updated.monthly_limit == 200.0
        # 덮어쓰기 확인
        assert _budget_limits['gemini'].daily_limit == 10.0


class TestGetTotalSpend:
    """get_total_spend 함수 테스트"""

    def test_get_total_spend_daily(self):
        """일일 총 지출 집계"""
        # 오늘 지출 기록 2건
        track_spend('gemini', 'model-a', 10000, 5000, 0.075, 0.30)
        track_spend('deepseek', 'model-b', 20000, 10000, 0.27, 1.10)

        total = get_total_spend(period='daily')

        # 두 기록의 합계여야 함
        expected = (
            (10000 * 0.075 + 5000 * 0.30) / 1_000_000
            + (20000 * 0.27 + 10000 * 1.10) / 1_000_000
        )
        assert abs(total - round(expected, 6)) < 1e-9

    def test_get_total_spend_monthly(self):
        """월간 총 지출 집계"""
        track_spend('gemini', 'model-a', 10000, 5000, 0.075, 0.30)

        total = get_total_spend(period='monthly')
        assert total > 0

    def test_get_total_spend_no_records(self):
        """기록 없을 때 0 반환"""
        total = get_total_spend(period='daily')
        assert total == 0.0


class TestResetDailySpend:
    """reset_daily_spend 함수 테스트"""

    def test_reset_daily_spend(self):
        """일일 지출 초기화 — 오늘 기록만 삭제"""
        # 오늘 기록
        track_spend('gemini', 'model-a', 10000, 5000, 0.075, 0.30)

        assert len(_spend_records) == 1

        reset_daily_spend()

        # 오늘 기록이 삭제되었으므로 총 지출 0
        total = get_total_spend(period='daily')
        assert total == 0.0

    def test_reset_daily_spend_preserves_old(self):
        """일일 초기화 시 이전 날짜 기록은 보존"""
        # 과거 기록 수동 삽입 (어제)
        old_record = SpendRecord(
            provider='gemini', model='model-a',
            tokens_in=10000, tokens_out=5000, cost=0.005,
            timestamp=time.time() - 86400 * 2,  # 2일 전
        )
        _spend_records.append(old_record)

        # 오늘 기록
        track_spend('gemini', 'model-b', 5000, 2000, 0.075, 0.30)

        assert len(_spend_records) == 2

        reset_daily_spend()

        # 과거 기록은 남아있어야 함
        assert len(_spend_records) == 1
        assert _spend_records[0].model == 'model-a'


class TestGetCheapestProvider:
    """get_cheapest_provider 함수 테스트"""

    def test_get_cheapest_provider_default(self):
        """최저가 프로바이더 조회 (medium 이상)"""
        result = get_cheapest_provider(min_quality='medium')

        assert result is not None
        # zhipuai가 medium 품질이면서 가장 저렴 (output $0.10/M)
        assert result == 'zhipuai'

    def test_get_cheapest_provider_low_quality(self):
        """최저가 프로바이더 (low 이상) — ollama (무료)"""
        result = get_cheapest_provider(min_quality='low')

        assert result == 'ollama'

    def test_get_cheapest_provider_high_quality(self):
        """high 품질만 허용 시"""
        result = get_cheapest_provider(min_quality='high')

        assert result is not None
        # high 품질 중 가장 저렴한 프로바이더
        assert result in ('gemini', 'deepseek')


class TestDataclasses:
    """데이터 클래스 기본 동작 확인"""

    def test_provider_choice_fields(self):
        """ProviderChoice 필드 확인"""
        choice = ProviderChoice(
            provider='gemini',
            model='gemini/test',
            reason='primary',
        )
        assert choice.provider == 'gemini'
        assert choice.model == 'gemini/test'
        assert choice.reason == 'primary'

    def test_budget_report_fields(self):
        """BudgetReport 필드 확인"""
        report = BudgetReport(
            provider='gemini',
            daily_spent=0.5,
            daily_limit=1.0,
            daily_remaining=0.5,
            monthly_spent=5.0,
            monthly_limit=10.0,
            monthly_remaining=5.0,
        )
        assert report.daily_remaining == 0.5
        assert report.monthly_remaining == 5.0
