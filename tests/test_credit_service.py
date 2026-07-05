"""크레딧 서비스 단위 테스트"""
import os
import json
import tempfile
import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_supabase_disabled():
    """Supabase 비활성화 — 로컬 모드 테스트"""
    with patch('services.data.supabase_service.is_supabase_enabled', return_value=False):
        yield


@pytest.fixture
def tmp_credits_file(tmp_path):
    """임시 크레딧 파일"""
    f = tmp_path / 'credits.json'
    f.write_text('{}', encoding='utf-8')
    with patch('services.usage.credit_service._LOCAL_CREDITS_FILE', str(f)):
        yield f


class TestCreditService:
    def test_get_balance_default(self, tmp_credits_file):
        from services.usage.credit_service import CreditService
        balance = CreditService.get_balance('user-123')
        assert balance['balance'] == 10  # 기본 free 크레딧
        assert balance['plan'] == 'free'

    def test_add_credits(self, tmp_credits_file):
        from services.usage.credit_service import CreditService
        result = CreditService.add_credits('user-123', 50, reason='test')
        assert result['success'] is True
        assert result['balance'] == 60  # 10 (기본) + 50

    def test_add_credits_negative_rejected(self, tmp_credits_file):
        from services.usage.credit_service import CreditService
        result = CreditService.add_credits('user-123', -5)
        assert result['success'] is False

    def test_deduct_credits(self, tmp_credits_file):
        from services.usage.credit_service import CreditService
        CreditService.add_credits('user-123', 20)
        result = CreditService.deduct_credits('user-123', 5)
        assert result['success'] is True
        assert result['balance'] == 25  # 10 + 20 - 5

    def test_deduct_insufficient(self, tmp_credits_file):
        from services.usage.credit_service import CreditService
        result = CreditService.deduct_credits('user-123', 100)
        assert result['success'] is False
        assert '부족' in result.get('error', '')

    def test_check_sufficient(self, tmp_credits_file):
        from services.usage.credit_service import CreditService
        assert CreditService.check_sufficient('user-123', 5) is True
        assert CreditService.check_sufficient('user-123', 100) is False


class TestCreditPlan:
    def test_get_all_plans(self):
        from services.usage.credit_plan import get_all_plans
        plans = get_all_plans()
        assert 'free' in plans
        assert 'pro' in plans
        assert 'team' in plans
