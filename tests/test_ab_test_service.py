"""
ABTestService 단위 테스트 (F6-10)
"""
import unittest
from services.analytics.ab_test_service import ABTestService


class TestABTestService(unittest.TestCase):

    def setUp(self):
        self.svc = ABTestService()

    def test_create_test(self):
        tid = self.svc.create_test('제목 테스트', ['A', 'B'])
        self.assertIsNotNone(tid)
        self.assertEqual(len(tid), 8)

    def test_requires_two_variants(self):
        with self.assertRaises(ValueError):
            self.svc.create_test('test', ['A'])

    def test_record_exposure_and_conversion(self):
        tid = self.svc.create_test('CTR 테스트', ['control', 'variant'])
        for _ in range(100):
            self.svc.record_exposure(tid, 'control')
        for _ in range(100):
            self.svc.record_exposure(tid, 'variant')
        for _ in range(10):
            self.svc.record_conversion(tid, 'control')
        for _ in range(30):
            self.svc.record_conversion(tid, 'variant')
        results = self.svc.get_results(tid)
        self.assertEqual(results['variants']['control']['exposures'], 100)
        self.assertEqual(results['variants']['variant']['conversions'], 30)

    def test_significance_detected(self):
        tid = self.svc.create_test('유의성 테스트', ['A', 'B'])
        # A: 1000 노출 / 50 전환 (5%)
        for _ in range(1000):
            self.svc.record_exposure(tid, 'A')
        for _ in range(50):
            self.svc.record_conversion(tid, 'A')
        # B: 1000 노출 / 200 전환 (20%)
        for _ in range(1000):
            self.svc.record_exposure(tid, 'B')
        for _ in range(200):
            self.svc.record_conversion(tid, 'B')
        results = self.svc.get_results(tid)
        self.assertTrue(results['significant'])
        self.assertEqual(results['winner'], 'B')

    def test_no_significance_small_sample(self):
        tid = self.svc.create_test('소샘플', ['A', 'B'])
        self.svc.record_exposure(tid, 'A')
        self.svc.record_exposure(tid, 'B')
        results = self.svc.get_results(tid)
        # 소샘플 → p_value 계산 불가 또는 비유의
        self.assertFalse(results.get('significant', False))

    def test_stop_test(self):
        tid = self.svc.create_test('정지 테스트', ['A', 'B'])
        result = self.svc.stop_test(tid)
        self.assertTrue(result)
        tests = self.svc.list_tests()
        t = next(t for t in tests if t['test_id'] == tid)
        self.assertFalse(t['active'])

    def test_nonexistent_test(self):
        result = self.svc.get_results('nonexistent')
        self.assertIn('error', result)


if __name__ == '__main__':
    unittest.main()
