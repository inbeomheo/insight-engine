"""credit_plan 단위 테스트 — 플랜 조회 함수 검증"""
import unittest

from services.usage.credit_plan import (
    get_plan_credits,
    get_plan_features,
    get_plan_price,
    get_all_plans,
    CREDIT_PLANS,
)


class TestGetPlanCredits(unittest.TestCase):
    def test_free_plan(self):
        self.assertEqual(get_plan_credits('free'), 10)

    def test_pro_plan(self):
        self.assertEqual(get_plan_credits('pro'), 100)

    def test_team_plan(self):
        self.assertEqual(get_plan_credits('team'), 500)

    def test_unknown_plan_defaults_to_free(self):
        self.assertEqual(get_plan_credits('enterprise'), 10)


class TestGetPlanFeatures(unittest.TestCase):
    def test_free_features(self):
        features = get_plan_features('free')
        self.assertIsInstance(features, list)
        self.assertTrue(any('10회' in f for f in features))

    def test_pro_has_api_key(self):
        features = get_plan_features('pro')
        self.assertTrue(any('API' in f for f in features))

    def test_unknown_defaults_to_free(self):
        features = get_plan_features('nonexistent')
        self.assertEqual(features, CREDIT_PLANS['free']['features'])


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
