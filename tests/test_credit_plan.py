"""credit_plan 단위 테스트 — 플랜 조회 함수 검증"""
import unittest

from services.usage.credit_plan import (
    get_plan_price,
    get_all_plans,
)


class TestGetPlanPrice(unittest.TestCase):
    def test_free_monthly(self):
        self.assertEqual(get_plan_price('free', 'monthly'), 0)

    def test_pro_monthly(self):
        self.assertEqual(get_plan_price('pro', 'monthly'), 9900)

    def test_team_yearly(self):
        self.assertEqual(get_plan_price('team', 'yearly'), 299000)

    def test_invalid_period(self):
        self.assertEqual(get_plan_price('pro', 'weekly'), 0)


class TestGetAllPlans(unittest.TestCase):
    def test_returns_all_three(self):
        plans = get_all_plans()
        self.assertIn('free', plans)
        self.assertIn('pro', plans)
        self.assertIn('team', plans)


if __name__ == '__main__':
    unittest.main()
