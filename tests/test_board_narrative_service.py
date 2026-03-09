"""
이사회 내러티브 보드 서비스 단위 테스트
"""
import unittest
from services.board_narrative_service import (
    generate_board_pack,
    BoardPack,
    _extract_highlights,
    _compute_metrics,
    _generate_action_items,
)


class TestBoardNarrativeService(unittest.TestCase):
    """generate_board_pack 함수 단위 테스트"""

    def _make_channel_data(self, **overrides):
        """테스트용 채널 데이터 팩토리"""
        data = {
            "total_content": 50,
            "published": 40,
            "total_views": 100000,
            "total_engagement": 5000,
            "subscribers": 10000,
            "subscriber_growth": 500,
            "total_cost": 25.0,
            "top_content": "AI 트렌드 2026",
        }
        data.update(overrides)
        return data

    def test_basic_board_pack(self):
        """기본 보드 팩 생성"""
        data = self._make_channel_data()
        result = generate_board_pack(data, period="monthly")
        self.assertIsInstance(result, BoardPack)
        self.assertEqual(result.period, "monthly")
        self.assertTrue(len(result.highlights) > 0)
        self.assertTrue(len(result.narrative) > 0)
        self.assertTrue(len(result.action_items) > 0)
        self.assertIn("total_content", result.metrics)

    def test_weekly_period(self):
        """주간 보드 팩"""
        result = generate_board_pack(self._make_channel_data(), period="weekly")
        self.assertEqual(result.period, "weekly")
        self.assertIn("금주", result.narrative)

    def test_quarterly_period(self):
        """분기별 보드 팩"""
        result = generate_board_pack(self._make_channel_data(), period="quarterly")
        self.assertEqual(result.period, "quarterly")

    def test_invalid_period(self):
        """잘못된 기간 → ValueError"""
        with self.assertRaises(ValueError):
            generate_board_pack({}, period="yearly")

    def test_empty_channel_data(self):
        """빈 채널 데이터"""
        result = generate_board_pack({}, period="monthly")
        self.assertIn("데이터 없음", result.highlights)
        self.assertIn("데이터 수집", result.action_items[0])

    def test_highlights_include_key_info(self):
        """하이라이트에 핵심 정보 포함"""
        data = self._make_channel_data()
        highlights = _extract_highlights(data)
        combined = " ".join(highlights)
        self.assertIn("50", combined)  # total_content
        self.assertIn("발행", combined)

    def test_highlights_subscriber_decline(self):
        """구독자 감소 시 경고"""
        data = self._make_channel_data(subscriber_growth=-200)
        highlights = _extract_highlights(data)
        combined = " ".join(highlights)
        self.assertIn("감소", combined)

    def test_metrics_computation(self):
        """지표 계산 정확성"""
        data = self._make_channel_data()
        metrics = _compute_metrics(data)
        self.assertEqual(metrics["total_content"], 50)
        self.assertEqual(metrics["published"], 40)
        self.assertEqual(metrics["publish_rate"], 80.0)
        self.assertGreater(metrics["avg_views_per_content"], 0)
        self.assertIn("total_cost", metrics)
        self.assertIn("cost_per_content", metrics)

    def test_metrics_no_cost(self):
        """비용 데이터 없을 때"""
        data = self._make_channel_data()
        del data["total_cost"]
        metrics = _compute_metrics(data)
        self.assertNotIn("total_cost", metrics)

    def test_action_items_low_publish_rate(self):
        """발행률 낮을 때 액션 아이템"""
        data = self._make_channel_data(total_content=100, published=50)
        metrics = _compute_metrics(data)
        items = _generate_action_items(metrics, data)
        combined = " ".join(items)
        self.assertIn("발행률", combined)

    def test_action_items_subscriber_decline(self):
        """구독자 감소 시 액션 아이템"""
        data = self._make_channel_data(subscriber_growth=-100)
        metrics = _compute_metrics(data)
        items = _generate_action_items(metrics, data)
        combined = " ".join(items)
        self.assertIn("구독자", combined)

    def test_narrative_includes_cost(self):
        """내러티브에 비용 정보 포함"""
        data = self._make_channel_data(total_cost=50.0)
        result = generate_board_pack(data, period="monthly")
        self.assertIn("$", result.narrative)

    def test_top_content_in_highlights(self):
        """최고 성과 콘텐츠가 하이라이트에 포함"""
        data = self._make_channel_data(top_content="인기 영상")
        highlights = _extract_highlights(data)
        combined = " ".join(highlights)
        self.assertIn("인기 영상", combined)

    def test_healthy_channel_positive_actions(self):
        """양호한 채널 — 기존 전략 유지 추천"""
        data = {
            "total_content": 10,
            "published": 10,
            "total_views": 50000,
            "total_engagement": 3000,
            "subscribers": 5000,
            "subscriber_growth": 300,
        }
        result = generate_board_pack(data, period="monthly")
        combined = " ".join(result.action_items)
        self.assertIn("유지", combined)


if __name__ == '__main__':
    unittest.main()
