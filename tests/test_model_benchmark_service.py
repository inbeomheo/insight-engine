"""
ModelBenchmarkService 단위 테스트 (F6-14)
"""
import unittest
from services.analytics.model_benchmark_service import ModelBenchmarkService


class TestModelBenchmarkService(unittest.TestCase):

    def setUp(self):
        self.svc = ModelBenchmarkService()

    def test_record_and_benchmark(self):
        self.svc.record('gemini', 1000.0, 500, 800, 0.001, 85.0, True)
        self.svc.record('deepseek', 2000.0, 500, 800, 0.0005, 75.0, True)
        bench = self.svc.get_benchmark()
        models = [b['model'] for b in bench]
        self.assertIn('gemini', models)
        self.assertIn('deepseek', models)
        # 품질 내림차순 정렬
        self.assertGreaterEqual(bench[0]['avg_quality'], bench[1]['avg_quality'])

    def test_success_rate(self):
        self.svc.record('model', 1000.0, 100, 200, 0.001, 80.0, True)
        self.svc.record('model', 1000.0, 100, 200, 0.001, 80.0, False)
        bench = self.svc.get_benchmark()
        m = bench[0]
        self.assertEqual(m['success_rate'], 50.0)

    def test_tokens_per_sec(self):
        self.svc.record('fast', 1000.0, 100, 1000, 0.001, 80.0, True)
        bench = self.svc.get_benchmark()
        m = next(b for b in bench if b['model'] == 'fast')
        # 1000 output tokens / 1 sec = 1000 tokens/sec
        self.assertAlmostEqual(m['tokens_per_sec'], 1000.0)

    def test_rank_by_speed(self):
        self.svc.record('fast', 100.0, 100, 200, 0.001, 70.0, True)
        self.svc.record('slow', 5000.0, 100, 200, 0.001, 90.0, True)
        ranked = self.svc.rank_by('avg_duration_ms')
        self.assertEqual(ranked[0]['model'], 'fast')
        self.assertEqual(ranked[0]['rank'], 1)

    def test_rank_by_cost(self):
        self.svc.record('cheap', 1000.0, 100, 200, 0.0001, 70.0, True)
        self.svc.record('expensive', 1000.0, 100, 200, 0.01, 90.0, True)
        ranked = self.svc.rank_by('avg_cost_usd')
        self.assertEqual(ranked[0]['model'], 'cheap')

    def test_empty_benchmark(self):
        bench = self.svc.get_benchmark()
        self.assertEqual(bench, [])

    def test_model_detail(self):
        self.svc.record('m', 500.0, 100, 200, 0.001, 80.0, True)
        self.svc.record('m', 1500.0, 100, 200, 0.001, 80.0, True)
        detail = self.svc.get_model_detail('m')
        self.assertEqual(detail['count'], 2)
        self.assertAlmostEqual(detail['avg_duration_ms'], 1000.0)


if __name__ == '__main__':
    unittest.main()
