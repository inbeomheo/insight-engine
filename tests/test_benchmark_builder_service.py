"""벤치마크 빌더 서비스 테스트"""

import unittest

from services.benchmark_builder_service import (
    BenchmarkCase,
    BenchmarkResult,
    BenchmarkSuite,
    create_suite,
    evaluate_result,
    generate_report,
    compare_runs,
)


class TestCreateSuite(unittest.TestCase):
    """create_suite 함수 테스트"""

    def test_스위트_생성(self):
        configs = [
            {"name": "test1", "input_data": "input", "expected_output": "output", "category": "math"},
            {"name": "test2", "input_data": "in2", "expected_output": "out2"},
        ]
        suite = create_suite("test suite", configs)
        self.assertEqual(len(suite.cases), 2)
        self.assertEqual(suite.cases[0].name, "test1")
        self.assertEqual(suite.cases[0].category, "math")
        self.assertEqual(suite.cases[1].category, "general")

    def test_빈_설정(self):
        suite = create_suite("empty", [])
        self.assertEqual(len(suite.cases), 0)


class TestEvaluateResult(unittest.TestCase):
    """evaluate_result 함수 테스트"""

    def test_정확_일치(self):
        case = BenchmarkCase(case_id="1", expected_output="hello world")
        result = evaluate_result(case, "hello world", 100.0)
        self.assertTrue(result.passed)
        self.assertEqual(result.score, 1.0)
        self.assertEqual(result.latency_ms, 100.0)

    def test_부분_일치_통과(self):
        case = BenchmarkCase(case_id="1", expected_output="the quick brown fox jumps")
        result = evaluate_result(case, "the quick brown fox leaps", 50.0)
        self.assertGreater(result.score, 0.5)

    def test_완전_불일치(self):
        case = BenchmarkCase(case_id="1", expected_output="hello world")
        result = evaluate_result(case, "xyz abc", 50.0)
        self.assertFalse(result.passed)
        self.assertEqual(result.score, 0.0)

    def test_공백_제거_일치(self):
        case = BenchmarkCase(case_id="1", expected_output=" hello world ")
        result = evaluate_result(case, "hello world", 50.0)
        self.assertTrue(result.passed)
        self.assertEqual(result.score, 1.0)

    def test_빈_expected(self):
        case = BenchmarkCase(case_id="1", expected_output="")
        result = evaluate_result(case, "something", 50.0)
        # 빈 expected와 다른 actual
        self.assertFalse(result.passed)


class TestGenerateReport(unittest.TestCase):
    """generate_report 함수 테스트"""

    def test_정상_보고서(self):
        cases = [
            BenchmarkCase(case_id="1", category="math"),
            BenchmarkCase(case_id="2", category="logic"),
        ]
        results = [
            BenchmarkResult(case_id="1", passed=True, latency_ms=100, score=1.0),
            BenchmarkResult(case_id="2", passed=False, latency_ms=200, score=0.3),
        ]
        suite = BenchmarkSuite(suite_id="s1", cases=cases, results=results)
        report = generate_report(suite)

        self.assertEqual(report["evaluated"], 2)
        self.assertAlmostEqual(report["pass_rate"], 0.5)
        self.assertEqual(report["avg_latency_ms"], 150.0)
        self.assertIn("math", report["category_scores"])
        self.assertIn("logic", report["category_scores"])

    def test_빈_결과(self):
        suite = BenchmarkSuite(suite_id="s1", cases=[BenchmarkCase(case_id="1")])
        report = generate_report(suite)
        self.assertEqual(report["evaluated"], 0)
        self.assertEqual(report["pass_rate"], 0.0)

    def test_전체_통과(self):
        cases = [BenchmarkCase(case_id="1")]
        results = [BenchmarkResult(case_id="1", passed=True, score=1.0, latency_ms=50)]
        suite = BenchmarkSuite(suite_id="s1", cases=cases, results=results)
        report = generate_report(suite)
        self.assertEqual(report["pass_rate"], 1.0)

    def test_카테고리별_점수(self):
        cases = [
            BenchmarkCase(case_id="1", category="cat_a"),
            BenchmarkCase(case_id="2", category="cat_a"),
            BenchmarkCase(case_id="3", category="cat_b"),
        ]
        results = [
            BenchmarkResult(case_id="1", passed=True, score=1.0, latency_ms=10),
            BenchmarkResult(case_id="2", passed=True, score=0.8, latency_ms=20),
            BenchmarkResult(case_id="3", passed=False, score=0.2, latency_ms=30),
        ]
        suite = BenchmarkSuite(suite_id="s1", cases=cases, results=results)
        report = generate_report(suite)
        self.assertEqual(report["category_scores"]["cat_a"]["total"], 2)
        self.assertEqual(report["category_scores"]["cat_b"]["total"], 1)


class TestCompareRuns(unittest.TestCase):
    """compare_runs 함수 테스트"""

    def test_향상_비교(self):
        cases = [BenchmarkCase(case_id="1")]

        suite_a = BenchmarkSuite(suite_id="a", cases=cases, results=[
            BenchmarkResult(case_id="1", passed=False, score=0.5, latency_ms=100),
        ])
        suite_b = BenchmarkSuite(suite_id="b", cases=cases, results=[
            BenchmarkResult(case_id="1", passed=True, score=0.9, latency_ms=80),
        ])

        comparison = compare_runs(suite_a, suite_b)
        self.assertTrue(comparison["improved"])
        self.assertGreater(comparison["score_diff"], 0)
        self.assertLess(comparison["latency_diff_ms"], 0)

    def test_하락_비교(self):
        cases = [BenchmarkCase(case_id="1")]

        suite_a = BenchmarkSuite(suite_id="a", cases=cases, results=[
            BenchmarkResult(case_id="1", passed=True, score=0.9, latency_ms=50),
        ])
        suite_b = BenchmarkSuite(suite_id="b", cases=cases, results=[
            BenchmarkResult(case_id="1", passed=False, score=0.3, latency_ms=200),
        ])

        comparison = compare_runs(suite_a, suite_b)
        self.assertFalse(comparison["improved"])
        self.assertIn("하락", comparison["summary"])


if __name__ == "__main__":
    unittest.main()
