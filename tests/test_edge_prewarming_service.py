"""에지 프리워밍 서비스 테스트"""

import unittest

from services.edge_prewarming_service import (
    EdgeNode,
    WarmingPlan,
    select_nodes,
    create_warming_plan,
    estimate_warming_time,
    get_node_utilization,
)


class TestSelectNodes(unittest.TestCase):
    """select_nodes 함수 테스트"""

    def test_용량_충분한_노드_선택(self):
        nodes = [
            EdgeNode(node_id="n1", region="us", capacity_mb=1000, current_usage_mb=200, latency_ms=20),
            EdgeNode(node_id="n2", region="eu", capacity_mb=1000, current_usage_mb=900, latency_ms=10),
            EdgeNode(node_id="n3", region="kr", capacity_mb=1000, current_usage_mb=100, latency_ms=30),
        ]
        selected = select_nodes(nodes, 200, max_nodes=2)
        self.assertLessEqual(len(selected), 2)
        # n2는 잔여 100MB < 200MB이므로 제외
        selected_ids = [n.node_id for n in selected]
        self.assertNotIn("n2", selected_ids)

    def test_지연시간_정렬(self):
        nodes = [
            EdgeNode(node_id="n1", region="us", capacity_mb=1000, current_usage_mb=0, latency_ms=50),
            EdgeNode(node_id="n2", region="eu", capacity_mb=1000, current_usage_mb=0, latency_ms=10),
        ]
        selected = select_nodes(nodes, 100)
        self.assertEqual(selected[0].node_id, "n2")  # 지연 낮은 순

    def test_빈_노드_리스트(self):
        selected = select_nodes([], 100)
        self.assertEqual(len(selected), 0)

    def test_용량_부족(self):
        nodes = [
            EdgeNode(node_id="n1", capacity_mb=100, current_usage_mb=90),
        ]
        selected = select_nodes(nodes, 50)
        self.assertEqual(len(selected), 0)  # 잔여 10MB < 50MB

    def test_max_nodes_제한(self):
        nodes = [
            EdgeNode(node_id=f"n{i}", capacity_mb=1000, current_usage_mb=0, latency_ms=i*10)
            for i in range(10)
        ]
        selected = select_nodes(nodes, 10, max_nodes=3)
        self.assertEqual(len(selected), 3)


class TestCreateWarmingPlan(unittest.TestCase):
    """create_warming_plan 함수 테스트"""

    def test_계획_생성(self):
        nodes = [
            EdgeNode(node_id="n1", region="us", capacity_mb=1000, current_usage_mb=0, latency_ms=20),
        ]
        plan = create_warming_plan("content1", 50, nodes)
        self.assertEqual(plan.content_id, "content1")
        self.assertGreater(len(plan.target_nodes), 0)
        self.assertGreater(plan.estimated_time_ms, 0)

    def test_큰_콘텐츠_높은_우선순위(self):
        nodes = [
            EdgeNode(node_id="n1", capacity_mb=10000, current_usage_mb=0, latency_ms=20),
        ]
        plan = create_warming_plan("big", 200, nodes)
        self.assertEqual(plan.priority, 1)

    def test_작은_콘텐츠_낮은_우선순위(self):
        nodes = [
            EdgeNode(node_id="n1", capacity_mb=1000, current_usage_mb=0, latency_ms=20),
        ]
        plan = create_warming_plan("small", 5, nodes)
        self.assertEqual(plan.priority, 3)

    def test_노드_없으면_빈_계획(self):
        plan = create_warming_plan("content1", 50, [])
        self.assertEqual(len(plan.target_nodes), 0)


class TestEstimateWarmingTime(unittest.TestCase):
    """estimate_warming_time 함수 테스트"""

    def test_시간_반환(self):
        plan = WarmingPlan(content_id="c1", estimated_time_ms=150.0)
        time = estimate_warming_time(plan, [])
        self.assertEqual(time, 150.0)


class TestGetNodeUtilization(unittest.TestCase):
    """get_node_utilization 함수 테스트"""

    def test_사용률_계산(self):
        nodes = [
            EdgeNode(node_id="n1", region="us", capacity_mb=1000, current_usage_mb=500, latency_ms=20),
        ]
        result = get_node_utilization(nodes)
        self.assertIn("n1", result)
        self.assertAlmostEqual(result["n1"]["utilization"], 0.5)
        self.assertEqual(result["n1"]["free_mb"], 500.0)

    def test_빈_노드_리스트(self):
        result = get_node_utilization([])
        self.assertEqual(len(result), 0)

    def test_완전_사용(self):
        nodes = [
            EdgeNode(node_id="n1", capacity_mb=100, current_usage_mb=100),
        ]
        result = get_node_utilization(nodes)
        self.assertAlmostEqual(result["n1"]["utilization"], 1.0)


if __name__ == "__main__":
    unittest.main()
