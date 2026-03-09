"""포트폴리오 히트맵 서비스 테스트"""
import unittest
from datetime import datetime, timedelta, timezone

from services.portfolio_heatmap_service import (
    HeatmapCell,
    HeatmapData,
    generate_heatmap,
    queue_for_refresh,
    _classify_coverage,
    _count_topic_in_library,
    _compute_market_demand,
    _compute_freshness,
    _compute_performance_score,
)


class TestClassifyCoverage(unittest.TestCase):
    """커버리지 분류 테스트"""

    def test_zero_content_is_gap(self):
        """콘텐츠 0개 → gap"""
        self.assertEqual(_classify_coverage(0, 0.8), "gap")

    def test_oversaturated(self):
        """수요 대비 콘텐츠 과다 → oversaturated"""
        # 수요 0.2 → 적정 1개, 콘텐츠 5개 → ratio 5.0
        self.assertEqual(_classify_coverage(5, 0.2), "oversaturated")

    def test_well_covered(self):
        """적정 수준 → well_covered"""
        # 수요 0.6 → 적정 3개, 콘텐츠 2개 → ratio ~0.67
        self.assertEqual(_classify_coverage(2, 0.6), "well_covered")

    def test_underexplored(self):
        """콘텐츠 부족 → underexplored"""
        # 수요 1.0 → 적정 5개, 콘텐츠 1개 → ratio 0.2
        self.assertEqual(_classify_coverage(1, 1.0), "underexplored")

    def test_zero_demand_with_content(self):
        """수요 0이어도 콘텐츠 있으면 gap 아님"""
        # 수요 0.0 → 적정 1개(max), 콘텐츠 10개 → ratio 10.0
        result = _classify_coverage(10, 0.0)
        self.assertEqual(result, "oversaturated")


class TestCountTopicInLibrary(unittest.TestCase):
    """토픽 카운트 테스트"""

    def test_match_by_topics_list(self):
        """topics 리스트에서 매칭"""
        library = [
            {"title": "글 1", "topics": ["Python", "AI"]},
            {"title": "글 2", "topics": ["Python", "Web"]},
            {"title": "글 3", "topics": ["Java"]},
        ]
        self.assertEqual(_count_topic_in_library("Python", library), 2)

    def test_match_by_title_fallback(self):
        """topics에 없어도 title에서 매칭"""
        library = [
            {"title": "Python 가이드", "topics": []},
            {"title": "Java 입문"},
        ]
        self.assertEqual(_count_topic_in_library("Python", library), 1)

    def test_case_insensitive(self):
        """대소문자 무시 매칭"""
        library = [{"title": "글", "topics": ["python"]}]
        self.assertEqual(_count_topic_in_library("PYTHON", library), 1)

    def test_no_match(self):
        """매칭 없음 → 0"""
        library = [{"title": "글", "topics": ["Java"]}]
        self.assertEqual(_count_topic_in_library("Rust", library), 0)

    def test_empty_library(self):
        """빈 라이브러리 → 0"""
        self.assertEqual(_count_topic_in_library("Python", []), 0)

    def test_no_double_count(self):
        """topics + title 양쪽 매칭 시 1회만 카운트"""
        library = [{"title": "Python 가이드", "topics": ["Python"]}]
        self.assertEqual(_count_topic_in_library("Python", library), 1)


class TestComputeMarketDemand(unittest.TestCase):
    """시장 수요 점수 테스트"""

    def test_first_topic_highest(self):
        """리스트 첫 번째 → 가장 높은 수요"""
        topics = ["AI", "Python", "Web"]
        demand = _compute_market_demand("AI", topics)
        self.assertGreater(demand, 0.9)

    def test_last_topic_lowest(self):
        """리스트 마지막 → 가장 낮은 수요"""
        topics = ["AI", "Python", "Web"]
        demand = _compute_market_demand("Web", topics)
        self.assertLess(demand, 0.5)

    def test_missing_topic(self):
        """리스트에 없는 토픽 → 0.0"""
        demand = _compute_market_demand("Rust", ["AI", "Python"])
        self.assertEqual(demand, 0.0)

    def test_empty_market_topics(self):
        """빈 시장 토픽 → 기본값 0.5"""
        demand = _compute_market_demand("AI", [])
        self.assertEqual(demand, 0.5)


class TestComputeFreshness(unittest.TestCase):
    """신선도 점수 테스트"""

    def test_recent_content_high_freshness(self):
        """최근 콘텐츠 → 높은 신선도"""
        now_str = datetime.now(timezone.utc).isoformat()
        self.assertGreater(_compute_freshness({"published_at": now_str}), 0.9)

    def test_old_content_low_freshness(self):
        """오래된 콘텐츠 → 낮은 신선도"""
        old = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
        freshness = _compute_freshness({"published_at": old})
        self.assertLess(freshness, 0.1)

    def test_no_date_returns_zero(self):
        """날짜 없음 → 0.0"""
        self.assertEqual(_compute_freshness({}), 0.0)

    def test_created_at_fallback(self):
        """published_at 없으면 created_at 사용"""
        now_str = datetime.now(timezone.utc).isoformat()
        freshness = _compute_freshness({"created_at": now_str})
        self.assertGreater(freshness, 0.9)

    def test_invalid_date_returns_zero(self):
        """잘못된 날짜 형식 → 0.0"""
        self.assertEqual(_compute_freshness({"published_at": "not-a-date"}), 0.0)


class TestComputePerformanceScore(unittest.TestCase):
    """성과 점수 테스트"""

    def test_high_performance(self):
        """100점 성과 → 1.0"""
        self.assertEqual(_compute_performance_score({"performance": 100}), 1.0)

    def test_zero_performance(self):
        """0점 성과 → 0.0"""
        self.assertEqual(_compute_performance_score({"performance": 0}), 0.0)

    def test_no_performance_default(self):
        """performance 필드 없음 → 0.5"""
        self.assertEqual(_compute_performance_score({}), 0.5)

    def test_fractional_performance(self):
        """0~1 범위 소수 → 그대로 사용"""
        self.assertAlmostEqual(_compute_performance_score({"performance": 0.7}), 0.7)


class TestGenerateHeatmap(unittest.TestCase):
    """generate_heatmap 통합 테스트"""

    def test_empty_market_topics(self):
        """시장 토픽 비어 있음 → 빈 히트맵"""
        result = generate_heatmap([], [])
        self.assertIsInstance(result, HeatmapData)
        self.assertEqual(result.total_topics, 0)
        self.assertEqual(result.cells, [])

    def test_gap_detection(self):
        """라이브러리에 없는 토픽 → gap"""
        result = generate_heatmap([], ["AI", "Python"])
        self.assertEqual(len(result.gaps), 2)
        self.assertIn("AI", result.gaps)

    def test_oversaturated_detection(self):
        """콘텐츠 과다 토픽 → oversaturated"""
        library = [
            {"title": f"AI 글 {i}", "topics": ["AI"]}
            for i in range(20)
        ]
        result = generate_heatmap(library, ["AI"])
        self.assertIn("AI", result.oversaturated)

    def test_cell_structure(self):
        """셀 데이터 구조 확인"""
        library = [{"title": "Python 입문", "topics": ["Python"]}]
        result = generate_heatmap(library, ["Python", "Java"])
        self.assertEqual(result.total_topics, 2)
        self.assertEqual(len(result.cells), 2)

        python_cell = result.cells[0]
        self.assertIsInstance(python_cell, HeatmapCell)
        self.assertEqual(python_cell.topic, "Python")
        self.assertGreater(python_cell.content_count, 0)
        self.assertIn(python_cell.coverage, {"oversaturated", "well_covered", "underexplored", "gap"})

    def test_mixed_coverage(self):
        """다양한 커버리지가 혼재"""
        library = [
            {"title": "AI 글 1", "topics": ["AI"]},
            {"title": "AI 글 2", "topics": ["AI"]},
            {"title": "AI 글 3", "topics": ["AI"]},
            {"title": "AI 글 4", "topics": ["AI"]},
            {"title": "AI 글 5", "topics": ["AI"]},
            {"title": "AI 글 6", "topics": ["AI"]},
            {"title": "AI 글 7", "topics": ["AI"]},
            {"title": "AI 글 8", "topics": ["AI"]},
            {"title": "AI 글 9", "topics": ["AI"]},
            {"title": "AI 글 10", "topics": ["AI"]},
            {"title": "AI 글 11", "topics": ["AI"]},
        ]
        result = generate_heatmap(library, ["AI", "Rust"])
        coverages = {c.coverage for c in result.cells}
        # AI는 과포화, Rust는 갭
        self.assertIn("oversaturated", coverages)
        self.assertIn("gap", coverages)


class TestQueueForRefresh(unittest.TestCase):
    """queue_for_refresh 통합 테스트"""

    def test_empty_list(self):
        """빈 리스트 → 빈 큐"""
        self.assertEqual(queue_for_refresh([]), [])

    def test_fresh_content_excluded(self):
        """신선한 콘텐츠는 큐에 포함되지 않음"""
        now_str = datetime.now(timezone.utc).isoformat()
        result = queue_for_refresh([
            {"title": "신선한 글", "published_at": now_str, "performance": 80},
        ])
        self.assertEqual(len(result), 0)

    def test_old_content_included(self):
        """오래된 콘텐츠 → 큐에 포함"""
        old = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
        result = queue_for_refresh([
            {"title": "오래된 글", "published_at": old, "performance": 50},
        ])
        self.assertEqual(len(result), 1)
        self.assertIn("신선도 부족", result[0]["refresh_reason"][0])

    def test_low_performance_included(self):
        """낮은 성과 → 큐에 포함"""
        now_str = datetime.now(timezone.utc).isoformat()
        result = queue_for_refresh([
            {"title": "성과 낮은 글", "published_at": now_str, "performance": 5},
        ])
        self.assertEqual(len(result), 1)
        self.assertTrue(any("낮은 성과" in r for r in result[0]["refresh_reason"]))

    def test_sorted_by_priority_desc(self):
        """우선순위 내림차순 정렬"""
        old = (datetime.now(timezone.utc) - timedelta(days=300)).isoformat()
        mid = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
        result = queue_for_refresh([
            {"title": "중간", "published_at": mid, "performance": 10},
            {"title": "매우 오래됨", "published_at": old, "performance": 0},
        ])
        if len(result) >= 2:
            self.assertGreaterEqual(result[0]["priority"], result[1]["priority"])

    def test_invalid_threshold_raises(self):
        """잘못된 임계치 → ValueError"""
        with self.assertRaises(ValueError):
            queue_for_refresh([{"title": "글"}], decay_threshold=1.5)

    def test_custom_threshold(self):
        """낮은 임계치 → 더 적은 콘텐츠 선별"""
        mid = (datetime.now(timezone.utc) - timedelta(days=80)).isoformat()
        # 기본 임계치 0.5에서는 포함될 수 있지만 0.1에서는 제외
        strict = queue_for_refresh(
            [{"title": "글", "published_at": mid, "performance": 80}],
            decay_threshold=0.1,
        )
        lenient = queue_for_refresh(
            [{"title": "글", "published_at": mid, "performance": 80}],
            decay_threshold=0.9,
        )
        self.assertLessEqual(len(strict), len(lenient))

    def test_refresh_reason_populated(self):
        """refresh_reason 필드가 비어 있지 않음"""
        old = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
        result = queue_for_refresh([
            {"title": "글", "published_at": old},
        ])
        self.assertGreater(len(result), 0)
        self.assertIn("refresh_reason", result[0])
        self.assertGreater(len(result[0]["refresh_reason"]), 0)

    def test_original_fields_preserved(self):
        """원본 콘텐츠 필드가 유지됨"""
        old = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
        result = queue_for_refresh([
            {"title": "원본 제목", "published_at": old, "custom_field": "값"},
        ])
        self.assertEqual(result[0]["title"], "원본 제목")
        self.assertEqual(result[0]["custom_field"], "값")


if __name__ == "__main__":
    unittest.main()
