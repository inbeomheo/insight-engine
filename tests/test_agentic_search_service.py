"""에이전트형 검색 서비스 테스트"""
import unittest
from services.agentic_search_service import (
    SearchQuery, SearchResult,
    classify_intent, decompose_query,
    rank_results, merge_results,
)


class TestClassifyIntent(unittest.TestCase):
    """질의 의도 분류 테스트"""

    def test_comparative_vs(self):
        self.assertEqual(classify_intent('Python vs Java 비교'), 'comparative')

    def test_comparative_difference(self):
        self.assertEqual(classify_intent('React와 Vue의 차이'), 'comparative')

    def test_factual_what(self):
        self.assertEqual(classify_intent('머신러닝이란 무엇인가'), 'factual')

    def test_factual_how(self):
        self.assertEqual(classify_intent('how to install python'), 'factual')

    def test_exploratory_why(self):
        self.assertEqual(classify_intent('왜 AI가 중요한가'), 'exploratory')

    def test_exploratory_future(self):
        self.assertEqual(classify_intent('블록체인의 미래 전망'), 'exploratory')

    def test_empty_query(self):
        self.assertEqual(classify_intent(''), 'factual')

    def test_default_factual(self):
        self.assertEqual(classify_intent('파이썬 설치'), 'factual')


class TestDecomposeQuery(unittest.TestCase):
    """질의 분해 테스트"""

    def test_conjunction_split(self):
        """접속사 기준 분해"""
        result = decompose_query('파이썬 그리고 자바 그리고 코틀린')
        self.assertGreater(len(result.sub_queries), 1)

    def test_comma_split(self):
        """쉼표 기준 분해"""
        result = decompose_query('프론트엔드, 백엔드, 데이터베이스')
        self.assertGreater(len(result.sub_queries), 1)

    def test_single_query(self):
        """단일 질의 (분해 안 됨)"""
        result = decompose_query('머신러닝')
        self.assertIsNotNone(result.query_id)
        self.assertEqual(result.original_query, '머신러닝')

    def test_intent_set(self):
        """의도 분류 연동"""
        result = decompose_query('Python vs Java 비교')
        self.assertEqual(result.intent, 'comparative')

    def test_empty_query(self):
        result = decompose_query('')
        self.assertEqual(result.original_query, '')
        self.assertEqual(result.sub_queries, [])

    def test_query_id_generated(self):
        result = decompose_query('테스트 질의')
        self.assertTrue(len(result.query_id) > 0)

    def test_and_keyword_split(self):
        result = decompose_query('React and Vue')
        self.assertGreater(len(result.sub_queries), 1)

    def test_or_keyword_split(self):
        result = decompose_query('프론트엔드 또는 백엔드')
        self.assertGreater(len(result.sub_queries), 1)


class TestRankResults(unittest.TestCase):
    """검색 결과 랭킹 테스트"""

    def test_sort_by_relevance(self):
        results = [
            SearchResult('r1', 'q1', '결과1', '스니펫1', 0.3),
            SearchResult('r2', 'q1', '결과2', '스니펫2', 0.9),
            SearchResult('r3', 'q1', '결과3', '스니펫3', 0.6),
        ]
        ranked = rank_results(results)
        self.assertEqual(ranked[0].result_id, 'r2')
        self.assertEqual(ranked[-1].result_id, 'r1')

    def test_empty_results(self):
        ranked = rank_results([])
        self.assertEqual(len(ranked), 0)

    def test_single_result(self):
        results = [SearchResult('r1', 'q1', '결과', '스니펫', 0.5)]
        ranked = rank_results(results)
        self.assertEqual(len(ranked), 1)

    def test_equal_relevance(self):
        results = [
            SearchResult('r1', 'q1', '결과1', '스니펫1', 0.5),
            SearchResult('r2', 'q1', '결과2', '스니펫2', 0.5),
        ]
        ranked = rank_results(results)
        self.assertEqual(len(ranked), 2)


class TestMergeResults(unittest.TestCase):
    """검색 결과 병합 테스트"""

    def test_dedup_by_title(self):
        """제목 기준 중복 제거"""
        group1 = [
            SearchResult('r1', 'q1', '파이썬 입문', '스니펫1', 0.8),
            SearchResult('r2', 'q1', '자바 가이드', '스니펫2', 0.7),
        ]
        group2 = [
            SearchResult('r3', 'q2', '파이썬 입문', '다른 스니펫', 0.9),
            SearchResult('r4', 'q2', '코틀린 소개', '스니펫4', 0.6),
        ]
        merged = merge_results([group1, group2])
        titles = [r.title for r in merged]
        self.assertEqual(len(titles), 3)  # 중복 제거
        self.assertNotIn('파이썬 입문', titles[1:])  # 첫 번째만 유지

    def test_sorted_by_relevance(self):
        group1 = [SearchResult('r1', 'q1', 'A', 's', 0.3)]
        group2 = [SearchResult('r2', 'q2', 'B', 's', 0.9)]
        merged = merge_results([group1, group2])
        self.assertEqual(merged[0].title, 'B')

    def test_empty_groups(self):
        merged = merge_results([[], []])
        self.assertEqual(len(merged), 0)

    def test_single_group(self):
        group = [SearchResult('r1', 'q1', 'A', 's', 0.5)]
        merged = merge_results([group])
        self.assertEqual(len(merged), 1)

    def test_case_insensitive_dedup(self):
        """대소문자 무시 중복 제거"""
        group1 = [SearchResult('r1', 'q1', 'Python Guide', 's', 0.8)]
        group2 = [SearchResult('r2', 'q2', 'python guide', 's', 0.6)]
        merged = merge_results([group1, group2])
        self.assertEqual(len(merged), 1)


if __name__ == '__main__':
    unittest.main()
