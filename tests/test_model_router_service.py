"""model_router_service 단위 테스트"""
import os
import unittest
from unittest.mock import patch

from services.model_router_service import (
    ModelRouter, ModelSpec, MODEL_CATALOG, RouterDecision
)


class TestModelSpec(unittest.TestCase):

    def test_model_catalog_populated(self):
        """모델 카탈로그 비어있지 않음"""
        self.assertGreater(len(MODEL_CATALOG), 0)

    def test_model_spec_fields(self):
        """ModelSpec 필드 확인"""
        key = list(MODEL_CATALOG.keys())[0]
        spec = MODEL_CATALOG[key]
        self.assertIsInstance(spec.provider, str)
        self.assertGreater(spec.context_window, 0)
        self.assertGreaterEqual(spec.quality_score, 0)
        self.assertLessEqual(spec.quality_score, 1)


class TestModelRouter(unittest.TestCase):

    @patch.dict(os.environ, {
        'GEMINI_API_KEY': 'test-key',
        'DEEPSEEK_API_KEY': 'test-key',
        'ZHIPUAI_API_KEY': '',
    })
    def setUp(self):
        self.router = ModelRouter()

    def test_detect_available_models(self):
        """API 키가 있는 모델만 사용 가능"""
        available = self.router._available_models
        # gemini, deepseek 키 설정 → 해당 프로바이더 모델만
        for key in available:
            spec = MODEL_CATALOG[key]
            self.assertIn(spec.provider, ['gemini', 'deepseek'])

    def test_route_balanced(self):
        """balanced 모드 라우팅"""
        decision = self.router.route('blog_seo', transcript_length=5000, mode='balanced')
        self.assertIsInstance(decision, RouterDecision)
        self.assertIn(decision.model_key, MODEL_CATALOG)

    def test_route_budget_mode(self):
        """budget 모드 — 저비용 모델 선택"""
        decision = self.router.route('summary', mode='budget')
        spec = MODEL_CATALOG[decision.model_key]
        self.assertIsNotNone(spec.cost_per_1k_output)

    def test_route_quality_mode(self):
        """quality 모드 — 고품질 모델 선택"""
        decision = self.router.route('tutorial', mode='quality')
        spec = MODEL_CATALOG[decision.model_key]
        self.assertGreaterEqual(spec.quality_score, 0.8)

    def test_route_fast_mode(self):
        """fast 모드 — 저레이턴시 모델 선택"""
        decision = self.router.route('sns_post', mode='fast')
        self.assertIsNotNone(decision.estimated_latency_s)

    def test_route_user_preference(self):
        """사용자 지정 모델 우선"""
        preferred = self.router._available_models[0]
        decision = self.router.route('blog_seo', user_model_preference=preferred)
        self.assertEqual(decision.model_key, preferred)
        self.assertEqual(decision.reason, "사용자 지정 모델")

    def test_estimate_cost(self):
        """비용 추정"""
        spec = list(MODEL_CATALOG.values())[0]
        cost = self.router._estimate_cost(spec, 10000)
        self.assertGreater(cost, 0)

    def test_get_fallbacks(self):
        """폴백 모델 목록 (primary 제외)"""
        primary = self.router._available_models[0]
        fallbacks = self.router._get_fallbacks(primary)
        self.assertNotIn(primary, fallbacks)

    def test_get_available_models(self):
        """사용 가능 모델 목록 반환"""
        models = self.router.get_available_models()
        self.assertGreater(len(models), 0)
        self.assertIn('model_key', models[0])
        self.assertIn('provider', models[0])

    def test_decision_has_fallback(self):
        """라우팅 결정에 폴백 포함"""
        decision = self.router.route('blog_seo')
        self.assertIsInstance(decision.fallback_models, list)


if __name__ == '__main__':
    unittest.main()
