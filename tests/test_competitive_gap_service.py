"""competitive_gap_service 단위 테스트"""
import unittest

from services.competitive_gap_service import (
    GapAnalysis,
    TopicGap,
    find_gaps,
    _normalize_topic,
)


class TestNormalizeTopic(unittest.TestCase):
    """토픽 정규화 테스트"""

    def test_lowercase(self):
        self.assertEqual(_normalize_topic("SEO"), "seo")

    def test_strip_spaces(self):
        self.assertEqual(_normalize_topic("  AI  "), "ai")

    def test_already_normalized(self):
        self.assertEqual(_normalize_topic("python"), "python")


class TestFindGaps(unittest.TestCase):
    """메인 함수 테스트"""

    def test_both_empty(self):
        result = find_gaps([], [])
        self.assertIsInstance(result, GapAnalysis)
        self.assertEqual(result.gaps, [])
        self.assertEqual(result.coverage_ratio, 0.0)

    def test_no_overlap(self):
        own = ["python", "javascript"]
        competitor = ["rust", "go"]
        result = find_gaps(own, competitor)
        self.assertEqual(len(result.overlaps), 0)
        self.assertEqual(len(result.gaps), 2)
        self.assertEqual(len(result.unique_strengths), 2)

    def test_full_overlap(self):
        own = ["seo", "content"]
        competitor = ["SEO", "Content"]
        result = find_gaps(own, competitor)
        self.assertEqual(len(result.overlaps), 2)
        self.assertEqual(len(result.gaps), 0)
        self.assertEqual(len(result.unique_strengths), 0)
        self.assertAlmostEqual(result.coverage_ratio, 1.0)

    def test_partial_overlap(self):
        own = ["seo", "content", "design"]
        competitor = ["seo", "marketing", "analytics"]
        result = find_gaps(own, competitor)
        self.assertIn("seo", result.overlaps)
        self.assertTrue(len(result.gaps) > 0)
        self.assertTrue(len(result.unique_strengths) > 0)

    def test_coverage_ratio(self):
        own = ["a", "b"]
        competitor = ["b", "c", "d"]
        result = find_gaps(own, competitor)
        # 전체 토픽 {a, b, c, d} = 4, own {a, b} = 2
        self.assertAlmostEqual(result.coverage_ratio, 0.5)

    def test_gaps_sorted_by_opportunity(self):
        own = ["a"]
        # "seo"가 2번 등장하므로 기회 점수 더 높음
        competitor = ["seo", "seo", "marketing"]
        result = find_gaps(own, competitor)
        if len(result.gaps) >= 2:
            scores = [g.opportunity_score for g in result.gaps]
            self.assertEqual(scores, sorted(scores, reverse=True))

    def test_case_insensitive_matching(self):
        own = ["Python"]
        competitor = ["python", "PYTHON"]
        result = find_gaps(own, competitor)
        self.assertIn("python", result.overlaps)
        self.assertEqual(len(result.gaps), 0)

    def test_empty_strings_filtered(self):
        own = ["a", "", "  "]
        competitor = ["b", ""]
        result = find_gaps(own, competitor)
        # 빈 문자열은 필터링됨
        self.assertTrue(all(g.topic.strip() for g in result.gaps))

    def test_topic_gap_dataclass(self):
        gap = TopicGap(topic="ai", competitor_coverage=3, opportunity_score=0.75)
        self.assertEqual(gap.topic, "ai")
        self.assertEqual(gap.opportunity_score, 0.75)

    def test_unique_strengths_sorted(self):
        own = ["zzz", "aaa", "mmm"]
        competitor = []
        result = find_gaps(own, competitor)
        self.assertEqual(result.unique_strengths, sorted(result.unique_strengths))


if __name__ == '__main__':
    unittest.main()
