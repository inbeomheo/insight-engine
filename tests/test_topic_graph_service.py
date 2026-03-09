"""토픽 그래프 서비스 테스트"""
import unittest
from services.topic_graph_service import (
    TopicNode, TopicEdge, TopicGraph,
    extract_topics, build_graph,
    find_central_topics, find_path,
)


class TestExtractTopics(unittest.TestCase):
    """토픽 추출 테스트"""

    def test_basic_extraction(self):
        text = '파이썬 파이썬 파이썬 자바 자바 코틀린'
        topics = extract_topics(text, max_topics=3)
        self.assertGreater(len(topics), 0)
        # 가장 빈번한 토픽이 첫 번째
        self.assertEqual(topics[0].topic, '파이썬')

    def test_weight_normalization(self):
        """가중치 정규화 (0~1)"""
        text = '머신러닝 머신러닝 딥러닝'
        topics = extract_topics(text, max_topics=5)
        for topic in topics:
            self.assertGreaterEqual(topic.weight, 0.0)
            self.assertLessEqual(topic.weight, 1.0)

    def test_max_topics_limit(self):
        text = ' '.join([f'토픽{i}' for i in range(20)])
        topics = extract_topics(text, max_topics=5)
        self.assertLessEqual(len(topics), 5)

    def test_related_terms(self):
        """관련 용어 추출"""
        text = '파이썬 머신러닝. 파이썬 딥러닝. 파이썬 데이터.'
        topics = extract_topics(text, max_topics=3)
        python_topic = [t for t in topics if t.topic == '파이썬']
        if python_topic:
            self.assertIsInstance(python_topic[0].related_terms, list)

    def test_empty_text(self):
        topics = extract_topics('')
        self.assertEqual(len(topics), 0)

    def test_stopwords_filtered(self):
        """불용어 필터링"""
        text = '그리고 그리고 그리고 파이썬'
        topics = extract_topics(text, max_topics=5)
        topic_names = [t.topic for t in topics]
        self.assertNotIn('그리고', topic_names)

    def test_node_id_generated(self):
        text = '파이썬 프로그래밍'
        topics = extract_topics(text, max_topics=2)
        for t in topics:
            self.assertTrue(len(t.node_id) > 0)

    def test_single_word(self):
        text = '파이썬'
        topics = extract_topics(text, max_topics=5)
        self.assertEqual(len(topics), 1)


class TestBuildGraph(unittest.TestCase):
    """그래프 생성 테스트"""

    def test_co_occurrence_edges(self):
        """같은 문장 공출현 → 엣지 생성"""
        text = '파이썬 머신러닝 함께 사용. 자바 별도 사용.'
        topics = [
            TopicNode('n1', '파이썬', 0.8, []),
            TopicNode('n2', '머신러닝', 0.6, []),
            TopicNode('n3', '자바', 0.4, []),
        ]
        graph = build_graph(text, topics)
        # 파이썬-머신러닝 엣지 존재
        edge_pairs = {(e.source_id, e.target_id) for e in graph.edges}
        # 양방향 중 한쪽은 있어야 함 (sorted이므로 순서 확인)
        has_edge = any(
            (e.source_id in ('n1', 'n2') and e.target_id in ('n1', 'n2'))
            for e in graph.edges
        )
        self.assertTrue(has_edge)

    def test_empty_topics(self):
        graph = build_graph('텍스트', [])
        self.assertEqual(len(graph.edges), 0)

    def test_empty_text(self):
        topics = [TopicNode('n1', '파이썬', 0.8, [])]
        graph = build_graph('', topics)
        self.assertEqual(len(graph.edges), 0)

    def test_edge_strength(self):
        """엣지 강도 정규화"""
        text = '파이썬 머신러닝. 파이썬 머신러닝. 파이썬 딥러닝.'
        topics = [
            TopicNode('n1', '파이썬', 0.8, []),
            TopicNode('n2', '머신러닝', 0.6, []),
            TopicNode('n3', '딥러닝', 0.4, []),
        ]
        graph = build_graph(text, topics)
        for edge in graph.edges:
            self.assertGreaterEqual(edge.strength, 0.0)
            self.assertLessEqual(edge.strength, 1.0)

    def test_nodes_preserved(self):
        topics = [TopicNode('n1', '파이썬', 0.8, [])]
        graph = build_graph('파이썬', topics)
        self.assertEqual(len(graph.nodes), 1)


class TestFindCentralTopics(unittest.TestCase):
    """중심 토픽 탐색 테스트"""

    def test_central_by_degree(self):
        """연결 수 기반 중심 토픽"""
        graph = TopicGraph(
            nodes=[
                TopicNode('n1', '중심', 0.8, []),
                TopicNode('n2', '주변1', 0.5, []),
                TopicNode('n3', '주변2', 0.5, []),
                TopicNode('n4', '고립', 0.3, []),
            ],
            edges=[
                TopicEdge('n1', 'n2', 'co_occurrence', 0.9),
                TopicEdge('n1', 'n3', 'co_occurrence', 0.7),
            ],
        )
        central = find_central_topics(graph, top_k=1)
        self.assertEqual(central[0].node_id, 'n1')

    def test_empty_graph(self):
        graph = TopicGraph(nodes=[], edges=[])
        central = find_central_topics(graph, top_k=3)
        self.assertEqual(len(central), 0)

    def test_no_edges(self):
        """엣지 없는 그래프"""
        graph = TopicGraph(
            nodes=[TopicNode('n1', 'A', 0.5, []), TopicNode('n2', 'B', 0.5, [])],
            edges=[],
        )
        central = find_central_topics(graph, top_k=2)
        self.assertEqual(len(central), 2)

    def test_top_k_limit(self):
        graph = TopicGraph(
            nodes=[TopicNode(f'n{i}', f'T{i}', 0.5, []) for i in range(5)],
            edges=[],
        )
        central = find_central_topics(graph, top_k=2)
        self.assertEqual(len(central), 2)


class TestFindPath(unittest.TestCase):
    """경로 탐색 테스트"""

    def setUp(self):
        self.graph = TopicGraph(
            nodes=[
                TopicNode('n1', 'A', 0.5, []),
                TopicNode('n2', 'B', 0.5, []),
                TopicNode('n3', 'C', 0.5, []),
                TopicNode('n4', 'D', 0.5, []),
            ],
            edges=[
                TopicEdge('n1', 'n2', 'co_occurrence', 0.8),
                TopicEdge('n2', 'n3', 'co_occurrence', 0.7),
                TopicEdge('n3', 'n4', 'co_occurrence', 0.6),
            ],
        )

    def test_direct_path(self):
        path = find_path(self.graph, 'n1', 'n2')
        self.assertIsNotNone(path)
        self.assertEqual(path[0], 'n1')
        self.assertEqual(path[-1], 'n2')

    def test_multi_hop_path(self):
        path = find_path(self.graph, 'n1', 'n4')
        self.assertIsNotNone(path)
        self.assertEqual(path[0], 'n1')
        self.assertEqual(path[-1], 'n4')
        self.assertEqual(len(path), 4)

    def test_same_node(self):
        path = find_path(self.graph, 'n1', 'n1')
        self.assertEqual(path, ['n1'])

    def test_no_path(self):
        """연결 없는 노드 간"""
        graph = TopicGraph(
            nodes=[TopicNode('n1', 'A', 0.5, []), TopicNode('n2', 'B', 0.5, [])],
            edges=[],
        )
        path = find_path(graph, 'n1', 'n2')
        self.assertIsNone(path)

    def test_nonexistent_node(self):
        path = find_path(self.graph, 'n1', 'n99')
        self.assertIsNone(path)

    def test_bidirectional(self):
        """역방향 경로도 탐색 가능"""
        path = find_path(self.graph, 'n4', 'n1')
        self.assertIsNotNone(path)
        self.assertEqual(path[0], 'n4')
        self.assertEqual(path[-1], 'n1')


if __name__ == '__main__':
    unittest.main()
