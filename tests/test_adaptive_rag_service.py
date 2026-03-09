"""적응형 RAG 서비스 테스트"""
import unittest
from services.adaptive_rag_service import (
    RAGChunk, RAGStrategy,
    assess_complexity, select_strategy,
    iterative_search, multi_hop_search,
)


class TestAssessComplexity(unittest.TestCase):
    """질의 복잡도 평가 테스트"""

    def test_simple_single_keyword(self):
        self.assertEqual(assess_complexity('파이썬'), 'simple')

    def test_moderate_two_concepts(self):
        result = assess_complexity('파이썬 프로그래밍 입문')
        self.assertIn(result, ('simple', 'moderate'))

    def test_complex_with_relations(self):
        result = assess_complexity('인공지능과 머신러닝의 관계 그리고 딥러닝의 영향')
        self.assertEqual(result, 'complex')

    def test_complex_multiple_conjunctions(self):
        result = assess_complexity('프론트엔드 그리고 백엔드 그리고 데이터베이스')
        self.assertEqual(result, 'complex')

    def test_moderate_with_relation_keyword(self):
        result = assess_complexity('기후의 영향')
        self.assertEqual(result, 'moderate')

    def test_empty_query(self):
        self.assertEqual(assess_complexity(''), 'simple')

    def test_single_word(self):
        self.assertEqual(assess_complexity('AI'), 'simple')

    def test_comparative(self):
        result = assess_complexity('React와 Vue 비교 분석')
        self.assertIn(result, ('moderate', 'complex'))


class TestSelectStrategy(unittest.TestCase):
    """전략 선택 테스트"""

    def test_simple_strategy(self):
        strategy = select_strategy('simple')
        self.assertEqual(strategy.strategy_type, 'simple')
        self.assertEqual(strategy.num_iterations, 1)
        self.assertEqual(strategy.top_k, 5)

    def test_moderate_strategy(self):
        strategy = select_strategy('moderate')
        self.assertEqual(strategy.strategy_type, 'iterative')
        self.assertEqual(strategy.num_iterations, 2)

    def test_complex_strategy(self):
        strategy = select_strategy('complex')
        self.assertEqual(strategy.strategy_type, 'multi_hop')
        self.assertEqual(strategy.num_iterations, 3)
        self.assertEqual(strategy.top_k, 10)

    def test_default_fallback(self):
        """알 수 없는 복잡도 → simple"""
        strategy = select_strategy('unknown')
        self.assertEqual(strategy.strategy_type, 'simple')


class TestIterativeSearch(unittest.TestCase):
    """반복 검색 테스트"""

    def setUp(self):
        self.chunks = [
            RAGChunk('c1', '파이썬은 프로그래밍 언어입니다.'),
            RAGChunk('c2', '머신러닝은 파이썬으로 구현합니다.'),
            RAGChunk('c3', '딥러닝은 머신러닝의 하위 분야입니다.'),
            RAGChunk('c4', '자바는 엔터프라이즈 개발에 사용됩니다.'),
            RAGChunk('c5', '프로그래밍 학습에는 인내가 필요합니다.'),
        ]

    def test_basic_search(self):
        results = iterative_search(self.chunks, '파이썬')
        self.assertGreater(len(results), 0)

    def test_iterative_expansion(self):
        """반복으로 결과 확장"""
        results_1 = iterative_search(self.chunks, '파이썬', iterations=1)
        results_2 = iterative_search(self.chunks, '파이썬', iterations=3)
        # 반복이 많을수록 같거나 더 많은 결과
        self.assertGreaterEqual(len(results_2), len(results_1))

    def test_no_duplicates(self):
        """중복 청크 없음"""
        results = iterative_search(self.chunks, '파이썬', iterations=3)
        ids = [r.chunk_id for r in results]
        self.assertEqual(len(ids), len(set(ids)))

    def test_empty_query(self):
        results = iterative_search(self.chunks, '')
        self.assertEqual(len(results), 0)

    def test_empty_chunks(self):
        results = iterative_search([], '파이썬')
        self.assertEqual(len(results), 0)


class TestMultiHopSearch(unittest.TestCase):
    """다중 홉 검색 테스트"""

    def setUp(self):
        self.chunks = [
            RAGChunk('c1', '인공지능은 컴퓨터 과학의 분야입니다.'),
            RAGChunk('c2', '머신러닝은 인공지능의 하위 분야입니다.'),
            RAGChunk('c3', '딥러닝은 머신러닝에서 발전한 기술입니다.'),
            RAGChunk('c4', '신경망은 딥러닝의 핵심 구조입니다.'),
            RAGChunk('c5', '자연어 처리는 인공지능 응용입니다.'),
        ]

    def test_basic_multi_hop(self):
        results = multi_hop_search(self.chunks, '인공지능')
        self.assertGreater(len(results), 0)

    def test_chaining(self):
        """홉을 통한 체이닝 (관련 청크 발견)"""
        results = multi_hop_search(self.chunks, '인공지능', hops=3)
        # 인공지능 → 머신러닝 → 딥러닝 체인을 따라갈 수 있음
        self.assertGreater(len(results), 1)

    def test_no_duplicates(self):
        results = multi_hop_search(self.chunks, '인공지능', hops=5)
        ids = [r.chunk_id for r in results]
        self.assertEqual(len(ids), len(set(ids)))

    def test_single_hop(self):
        results = multi_hop_search(self.chunks, '인공지능', hops=1)
        self.assertGreater(len(results), 0)

    def test_empty_query(self):
        results = multi_hop_search(self.chunks, '')
        self.assertEqual(len(results), 0)


if __name__ == '__main__':
    unittest.main()
