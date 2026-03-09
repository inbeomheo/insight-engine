"""vLLM 서빙 서비스 테스트"""

import unittest

from services.vllm_serving_service import (
    ServingConfig,
    ServingMetrics,
    InferenceRequest,
    create_config,
    estimate_throughput,
    simulate_speculative_decode,
    manage_kv_cache,
    calculate_memory_usage,
)


class TestCreateConfig(unittest.TestCase):
    """create_config 함수 테스트"""

    def test_기본_설정_생성(self):
        config = create_config("llama-7b")
        self.assertEqual(config.model_name, "llama-7b")
        self.assertEqual(config.max_batch_size, 32)
        self.assertEqual(config.gpu_memory_gb, 24.0)
        self.assertGreater(config.kv_cache_size, 0)

    def test_커스텀_설정(self):
        config = create_config("llama-13b", batch_size=64, gpu_memory=48.0)
        self.assertEqual(config.max_batch_size, 64)
        self.assertEqual(config.gpu_memory_gb, 48.0)

    def test_빈_모델명_에러(self):
        with self.assertRaises(ValueError):
            create_config("")

    def test_음수_배치크기_에러(self):
        with self.assertRaises(ValueError):
            create_config("llama-7b", batch_size=-1)

    def test_음수_gpu_메모리_에러(self):
        with self.assertRaises(ValueError):
            create_config("llama-7b", gpu_memory=-10)


class TestEstimateThroughput(unittest.TestCase):
    """estimate_throughput 함수 테스트"""

    def test_정상_처리량_추정(self):
        config = create_config("llama-7b")
        metrics = estimate_throughput(config, 100)
        self.assertEqual(metrics.requests_processed, 100)
        self.assertGreater(metrics.throughput_tps, 0)
        self.assertGreater(metrics.avg_latency_ms, 0)
        self.assertGreater(metrics.cache_hit_rate, 0)
        self.assertGreater(metrics.gpu_utilization, 0)

    def test_요청수_0이면_빈_메트릭(self):
        config = create_config("llama-7b")
        metrics = estimate_throughput(config, 0)
        self.assertEqual(metrics.requests_processed, 0)

    def test_추측_디코딩_모델_있으면_처리량_증가(self):
        config_without = create_config("llama-7b")
        config_with = create_config("llama-7b")
        config_with.speculative_draft_model = "draft-model"

        metrics_without = estimate_throughput(config_without, 100)
        metrics_with = estimate_throughput(config_with, 100)

        self.assertGreater(metrics_with.throughput_tps, metrics_without.throughput_tps)

    def test_큰_배치_크기_높은_효율(self):
        config_small = create_config("llama-7b", batch_size=1)
        config_large = create_config("llama-7b", batch_size=64)

        m_small = estimate_throughput(config_small, 100)
        m_large = estimate_throughput(config_large, 100)

        self.assertGreater(m_large.throughput_tps, m_small.throughput_tps)

    def test_gpu_활용률_범위(self):
        config = create_config("llama-7b")
        metrics = estimate_throughput(config, 50)
        self.assertGreaterEqual(metrics.gpu_utilization, 0)
        self.assertLessEqual(metrics.gpu_utilization, 1.0)


class TestSimulativeSpeculativeDecode(unittest.TestCase):
    """simulate_speculative_decode 함수 테스트"""

    def test_완전_일치(self):
        draft = ["a", "b", "c"]
        target = ["a", "b", "c"]
        result = simulate_speculative_decode(draft, target)
        self.assertEqual(result["acceptance_rate"], 1.0)
        self.assertEqual(result["accepted_count"], 3)
        self.assertGreater(result["speedup"], 1.0)

    def test_완전_불일치(self):
        draft = ["a", "b", "c"]
        target = ["x", "y", "z"]
        result = simulate_speculative_decode(draft, target)
        self.assertEqual(result["acceptance_rate"], 0.0)
        self.assertEqual(result["accepted_count"], 0)

    def test_부분_일치(self):
        draft = ["a", "b", "c"]
        target = ["a", "b", "x"]
        result = simulate_speculative_decode(draft, target)
        self.assertEqual(result["accepted_count"], 2)

    def test_빈_드래프트(self):
        result = simulate_speculative_decode([], ["a", "b"])
        self.assertEqual(result["acceptance_rate"], 0.0)
        self.assertEqual(result["speedup"], 1.0)


class TestManageKvCache(unittest.TestCase):
    """manage_kv_cache 함수 테스트"""

    def test_정상_캐시_관리(self):
        result = manage_kv_cache(2048, 10, "lru")
        self.assertEqual(result["total_slots"], 2048)
        self.assertGreater(result["allocated_slots"], 0)
        self.assertEqual(result["eviction_policy"], "lru")

    def test_fifo_정책(self):
        result = manage_kv_cache(2048, 10, "fifo")
        self.assertEqual(result["eviction_policy"], "fifo")

    def test_잘못된_정책_에러(self):
        with self.assertRaises(ValueError):
            manage_kv_cache(2048, 10, "random")

    def test_캐시_초과_시_eviction(self):
        result = manage_kv_cache(100, 100, "lru")  # 100요청 × 64슬롯 > 100
        self.assertGreater(result["evicted_entries"], 0)

    def test_음수_캐시_에러(self):
        with self.assertRaises(ValueError):
            manage_kv_cache(0, 10)


class TestCalculateMemoryUsage(unittest.TestCase):
    """calculate_memory_usage 함수 테스트"""

    def test_7b_모델_메모리(self):
        config = create_config("llama-7b")
        result = calculate_memory_usage(config)
        self.assertEqual(result["total_gb"], 24.0)
        self.assertGreater(result["model_weights_gb"], 0)
        self.assertGreater(result["kv_cache_gb"], 0)
        self.assertIn("fits_in_memory", result)

    def test_70b_모델_큰_가중치(self):
        config = create_config("llama-70b")
        result = calculate_memory_usage(config)
        self.assertGreater(result["model_weights_gb"], 30)

    def test_메모리_초과_감지(self):
        config = create_config("llama-70b", gpu_memory=8.0)
        result = calculate_memory_usage(config)
        self.assertFalse(result["fits_in_memory"])

    def test_활용률_범위(self):
        config = create_config("llama-7b")
        result = calculate_memory_usage(config)
        self.assertGreaterEqual(result["utilization"], 0)
        self.assertLessEqual(result["utilization"], 1.0)


if __name__ == "__main__":
    unittest.main()
