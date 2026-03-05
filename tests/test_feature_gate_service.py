"""
FeatureGateService 단위 테스트 (F4-18)
"""
import unittest
from services.feature_gate_service import FeatureGateService


class TestFeatureGateService(unittest.TestCase):

    def setUp(self):
        self.svc = FeatureGateService()

    def test_default_plan_is_free(self):
        self.assertEqual(self.svc.get_user_plan('u1'), 'free')

    def test_free_can_generate(self):
        self.assertTrue(self.svc.can_access('u1', 'generate'))

    def test_free_cannot_tts(self):
        self.assertFalse(self.svc.can_access('u1', 'tts'))

    def test_pro_can_tts(self):
        self.svc.set_user_plan('u1', 'pro')
        self.assertTrue(self.svc.can_access('u1', 'tts'))

    def test_enterprise_has_sso(self):
        self.svc.set_user_plan('u1', 'enterprise')
        self.assertTrue(self.svc.can_access('u1', 'sso'))

    def test_get_available_features(self):
        features = self.svc.get_available_features('u1')
        self.assertIn('generate', features)
        self.assertNotIn('tts', features)

    def test_get_plan_features(self):
        features = self.svc.get_plan_features('starter')
        self.assertIn('rag', features)
        self.assertNotIn('tts', features)


if __name__ == '__main__':
    unittest.main()
