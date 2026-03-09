"""competitor_benchmark_service 단위 테스트"""
import unittest

from services.competitor_benchmark_service import (
    benchmark_competitors,
    BenchmarkReport,
    AccountRank,
    _safe_float,
    _normalize_values,
    _compute_score,
    _identify_strengths,
    _identify_weaknesses,
)


class TestSafeFloat(unittest.TestCase):

    def test_valid_float(self):
        self.assertEqual(_safe_float(3.14), 3.14)
        self.assertEqual(_safe_float('2.5'), 2.5)

    def test_invalid_returns_default(self):
        self.assertEqual(_safe_float('abc'), 0.0)
        self.assertEqual(_safe_float(None), 0.0)
        self.assertEqual(_safe_float(None, 5.0), 5.0)


class TestNormalizeValues(unittest.TestCase):

    def test_basic_normalization(self):
        result = _normalize_values([10, 20, 30])
        self.assertAlmostEqual(result[0], 0.0)
        self.assertAlmostEqual(result[1], 0.5)
        self.assertAlmostEqual(result[2], 1.0)

    def test_single_value(self):
        result = _normalize_values([5])
        self.assertEqual(result, [0.5])

    def test_all_same(self):
        result = _normalize_values([7, 7, 7])
        self.assertEqual(result, [0.5, 0.5, 0.5])

    def test_empty(self):
        self.assertEqual(_normalize_values([]), [])


class TestComputeScore(unittest.TestCase):

    def test_top_account_gets_high_score(self):
        accounts = [
            {'subscribers': 100000, 'avg_views': 50000, 'engagement_rate': 0.08},
            {'subscribers': 10000, 'avg_views': 5000, 'engagement_rate': 0.02},
        ]
        score_top = _compute_score(accounts[0], accounts)
        score_low = _compute_score(accounts[1], accounts)
        self.assertGreater(score_top, score_low)

    def test_equal_accounts_get_similar_scores(self):
        accounts = [
            {'subscribers': 5000, 'avg_views': 3000},
            {'subscribers': 5000, 'avg_views': 3000},
        ]
        score_a = _compute_score(accounts[0], accounts)
        score_b = _compute_score(accounts[1], accounts)
        self.assertAlmostEqual(score_a, score_b)


class TestIdentifyStrengths(unittest.TestCase):

    def test_detects_strength(self):
        accounts = [
            {'subscribers': 100000, 'avg_views': 1000},
            {'subscribers': 10000, 'avg_views': 1000},
        ]
        strengths = _identify_strengths(accounts[0], accounts)
        self.assertTrue(any('subscribers' in s for s in strengths))

    def test_no_strengths_when_equal(self):
        accounts = [
            {'subscribers': 5000},
            {'subscribers': 5000},
        ]
        strengths = _identify_strengths(accounts[0], accounts)
        self.assertEqual(len(strengths), 0)


class TestIdentifyWeaknesses(unittest.TestCase):

    def test_detects_weakness(self):
        accounts = [
            {'subscribers': 1000, 'avg_views': 50000},
            {'subscribers': 100000, 'avg_views': 50000},
        ]
        weaknesses = _identify_weaknesses(accounts[0], accounts)
        self.assertTrue(any('subscribers' in w for w in weaknesses))


class TestBenchmarkCompetitors(unittest.TestCase):

    def test_empty_accounts(self):
        result = benchmark_competitors([])
        self.assertIsInstance(result, BenchmarkReport)
        self.assertEqual(result.accounts_analyzed, 0)
        self.assertEqual(len(result.rankings), 0)

    def test_single_account(self):
        accounts = [{'name': 'ChA', 'subscribers': 5000}]
        result = benchmark_competitors(accounts)
        self.assertEqual(result.accounts_analyzed, 1)
        self.assertEqual(len(result.rankings), 1)
        self.assertEqual(result.rankings[0].account_name, 'ChA')

    def test_multiple_accounts_ranked(self):
        accounts = [
            {'name': 'Low', 'subscribers': 1000, 'avg_views': 500, 'engagement_rate': 0.01},
            {'name': 'High', 'subscribers': 100000, 'avg_views': 50000, 'engagement_rate': 0.1},
            {'name': 'Mid', 'subscribers': 20000, 'avg_views': 10000, 'engagement_rate': 0.05},
        ]
        result = benchmark_competitors(accounts)
        self.assertEqual(result.accounts_analyzed, 3)
        # 1위가 High여야 함
        self.assertEqual(result.rankings[0].account_name, 'High')
        self.assertEqual(result.rankings[-1].account_name, 'Low')

    def test_rankings_have_strengths_weaknesses(self):
        accounts = [
            {'name': 'A', 'subscribers': 100000, 'avg_views': 100},
            {'name': 'B', 'subscribers': 100, 'avg_views': 100000},
        ]
        result = benchmark_competitors(accounts)
        a_rank = next(r for r in result.rankings if r.account_name == 'A')
        b_rank = next(r for r in result.rankings if r.account_name == 'B')
        # A는 subscribers 강점, avg_views 약점
        self.assertTrue(any('subscribers' in s for s in a_rank.strengths))
        self.assertTrue(any('avg_views' in w for w in a_rank.weaknesses))

    def test_insights_generated(self):
        accounts = [
            {'name': 'Top', 'subscribers': 100000},
            {'name': 'Bottom', 'subscribers': 100},
        ]
        result = benchmark_competitors(accounts)
        self.assertTrue(len(result.insights) > 0)
        self.assertTrue(any('Top' in i for i in result.insights))

    def test_account_name_fallback(self):
        """account_name 키로도 이름 추출 가능"""
        accounts = [{'account_name': 'TestCh', 'subscribers': 5000}]
        result = benchmark_competitors(accounts)
        self.assertEqual(result.rankings[0].account_name, 'TestCh')

    def test_score_range(self):
        accounts = [
            {'name': 'A', 'subscribers': 50000, 'avg_views': 30000},
            {'name': 'B', 'subscribers': 10000, 'avg_views': 5000},
        ]
        result = benchmark_competitors(accounts)
        for rank in result.rankings:
            self.assertGreaterEqual(rank.score, 0)
            self.assertLessEqual(rank.score, 100)

    def test_insights_gap_analysis(self):
        """점수 차이가 크면 격차 인사이트 생성"""
        accounts = [
            {'name': 'Top', 'subscribers': 1000000, 'avg_views': 500000, 'engagement_rate': 0.2},
            {'name': 'Bot', 'subscribers': 100, 'avg_views': 50, 'engagement_rate': 0.001},
        ]
        result = benchmark_competitors(accounts)
        self.assertTrue(any('격차' in i for i in result.insights))


if __name__ == '__main__':
    unittest.main()
