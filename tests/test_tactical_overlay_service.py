"""전술 오버레이 서비스 테스트"""
import unittest
from services.tactical_overlay_service import (
    create_overlay, add_point, run_swot_analysis, prioritize_actions,
    TacticalOverlay, TacticalPoint
)


class TestTacticalOverlayService(unittest.TestCase):

    def setUp(self):
        self.overlay = create_overlay('시장 분석')
        self.overlay = add_point(self.overlay, '기술력', 'strength', {'x': 0, 'y': 0}, '핵심 역량')
        self.overlay = add_point(self.overlay, '브랜드', 'weakness', {'x': 1, 'y': 0}, '인지도 부족')
        self.overlay = add_point(self.overlay, '신시장', 'opportunity', {'x': 0, 'y': 1}, '해외 진출')
        self.overlay = add_point(self.overlay, '경쟁사', 'threat', {'x': 1, 'y': 1}, '대기업 진입')

    def test_create_overlay(self):
        overlay = create_overlay('테스트')
        self.assertIsInstance(overlay, TacticalOverlay)
        self.assertEqual(overlay.title, '테스트')

    def test_add_point(self):
        self.assertEqual(len(self.overlay.points), 4)

    def test_add_point_invalid_category(self):
        with self.assertRaises(ValueError):
            add_point(self.overlay, 'x', 'invalid', {}, '')

    def test_run_swot_analysis(self):
        result = run_swot_analysis(self.overlay)
        self.assertEqual(len(result['strength']), 1)
        self.assertEqual(len(result['weakness']), 1)
        self.assertEqual(len(result['opportunity']), 1)
        self.assertEqual(len(result['threat']), 1)
        self.assertEqual(result['summary']['total'], 4)

    def test_swot_empty_overlay(self):
        empty = create_overlay('빈')
        result = run_swot_analysis(empty)
        self.assertEqual(result['summary']['total'], 0)

    def test_prioritize_actions_order(self):
        actions = prioritize_actions(self.overlay)
        self.assertGreater(len(actions), 0)
        # 1순위 (offensive)가 먼저
        self.assertEqual(actions[0]['priority'], 1)
        self.assertEqual(actions[0]['strategy'], 'offensive')

    def test_prioritize_actions_includes_all_types(self):
        actions = prioritize_actions(self.overlay)
        strategies = {a['strategy'] for a in actions}
        self.assertIn('offensive', strategies)
        self.assertIn('defensive', strategies)
        self.assertIn('contingency', strategies)

    def test_prioritize_no_opportunities(self):
        overlay = create_overlay('제한')
        overlay = add_point(overlay, '약점', 'weakness', {}, '문제')
        actions = prioritize_actions(overlay)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['strategy'], 'defensive')

    def test_add_point_immutable(self):
        before = len(self.overlay.points)
        add_point(self.overlay, '새', 'strength', {}, '')
        # 원본 변경 없음 (새 객체 반환)
        self.assertEqual(len(self.overlay.points), before)

    def test_swot_summary_counts(self):
        result = run_swot_analysis(self.overlay)
        self.assertEqual(result['summary']['strengths_count'], 1)
        self.assertEqual(result['summary']['weaknesses_count'], 1)


if __name__ == '__main__':
    unittest.main()
