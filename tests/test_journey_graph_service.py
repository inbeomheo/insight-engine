"""여정 그래프 서비스 테스트"""
import unittest
from services.journey_graph_service import (
    create_journey, add_stage, connect_stages, find_pain_points,
    calculate_conversion, JourneyGraph, JourneyNode, JourneyEdge
)


class TestJourneyGraphService(unittest.TestCase):

    def setUp(self):
        self.journey = create_journey('구매 여정')

    def test_create_journey(self):
        self.assertIsInstance(self.journey, JourneyGraph)
        self.assertEqual(self.journey.title, '구매 여정')
        self.assertEqual(len(self.journey.nodes), 0)

    def test_add_stage(self):
        j = add_stage(self.journey, '인지', '광고 노출', '배너', 'neutral')
        self.assertEqual(len(j.nodes), 1)
        self.assertEqual(j.nodes[0].stage, '인지')

    def test_add_stage_with_pain_points(self):
        j = add_stage(self.journey, '결제', '결제 진행', '결제페이지', 'negative', ['UI 복잡'])
        self.assertEqual(j.nodes[0].pain_points, ['UI 복잡'])

    def test_connect_stages(self):
        j = add_stage(self.journey, '인지', 'd', 't', 'neutral')
        j = add_stage(j, '검색', 'd', 't', 'positive')
        n1 = j.nodes[0].node_id
        n2 = j.nodes[1].node_id
        j = connect_stages(j, n1, n2, '클릭', 0.3)
        self.assertEqual(len(j.edges), 1)
        self.assertEqual(j.edges[0].drop_off_rate, 0.3)

    def test_connect_stages_invalid_id(self):
        j = add_stage(self.journey, '인지', 'd', 't', 'neutral')
        with self.assertRaises(ValueError):
            connect_stages(j, j.nodes[0].node_id, 'nonexistent', '', 0.1)

    def test_connect_stages_clamp_drop_off(self):
        j = add_stage(self.journey, 'A', 'd', 't', 'neutral')
        j = add_stage(j, 'B', 'd', 't', 'positive')
        n1, n2 = j.nodes[0].node_id, j.nodes[1].node_id
        j = connect_stages(j, n1, n2, 't', 1.5)
        self.assertEqual(j.edges[0].drop_off_rate, 1.0)

    def test_find_pain_points(self):
        j = add_stage(self.journey, '인지', 'd', 't', 'neutral')
        j = add_stage(j, '결제', 'd', 't', 'negative', ['느림', '복잡'])
        points = find_pain_points(j)
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0]['stage'], '결제')

    def test_find_pain_points_empty(self):
        j = add_stage(self.journey, '인지', 'd', 't', 'positive')
        points = find_pain_points(j)
        self.assertEqual(len(points), 0)

    def test_calculate_conversion_no_edges(self):
        self.assertEqual(calculate_conversion(self.journey), 1.0)

    def test_calculate_conversion(self):
        j = add_stage(self.journey, 'A', '', '', 'neutral')
        j = add_stage(j, 'B', '', '', 'neutral')
        j = add_stage(j, 'C', '', '', 'neutral')
        n1, n2, n3 = j.nodes[0].node_id, j.nodes[1].node_id, j.nodes[2].node_id
        j = connect_stages(j, n1, n2, '', 0.2)  # 20% 이탈
        j = connect_stages(j, n2, n3, '', 0.5)  # 50% 이탈
        conv = calculate_conversion(j)
        self.assertAlmostEqual(conv, 0.8 * 0.5, places=4)

    def test_add_stage_immutable(self):
        add_stage(self.journey, '새', '', '', 'neutral')
        self.assertEqual(len(self.journey.nodes), 0)


if __name__ == '__main__':
    unittest.main()
