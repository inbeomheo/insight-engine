"""link_network_service 단위 테스트"""
import unittest

from services.link_network_service import (
    LinkNetworkService, _extract_keywords, _tf_idf_similarity
)


class TestExtractKeywords(unittest.TestCase):

    def test_korean_words(self):
        """한글 키워드 추출"""
        words = _extract_keywords('파이썬 프로그래밍 입문 가이드')
        self.assertIn('파이썬', words)
        self.assertIn('프로그래밍', words)

    def test_english_words(self):
        """영문 키워드 추출 (4자 이상)"""
        words = _extract_keywords('python programming guide deep learning')
        self.assertIn('python', words)
        self.assertIn('programming', words)

    def test_stopwords_filtered(self):
        """불용어 필터링"""
        words = _extract_keywords('있다 이다 하다 파이썬 프로그래밍')
        self.assertNotIn('있다', words)
        self.assertIn('파이썬', words)


class TestTfIdfSimilarity(unittest.TestCase):

    def test_identical(self):
        """동일 집합"""
        score = _tf_idf_similarity(['파이썬', '딥러닝'], ['파이썬', '딥러닝'])
        self.assertEqual(score, 1.0)

    def test_no_overlap(self):
        """겹치지 않는 집합"""
        score = _tf_idf_similarity(['파이썬', '딥러닝'], ['요리', '레시피'])
        self.assertEqual(score, 0.0)

    def test_empty(self):
        """빈 집합"""
        self.assertEqual(_tf_idf_similarity([], ['파이썬']), 0.0)


class TestLinkNetworkService(unittest.TestCase):

    def setUp(self):
        self.svc = LinkNetworkService(similarity_threshold=0.05)

    def test_add_document(self):
        """문서 추가"""
        self.svc.add_document('d1', '파이썬 입문', '파이썬 프로그래밍 기초 학습')
        self.assertIn('d1', self.svc.documents)

    def test_add_documents_batch(self):
        """배치 문서 추가"""
        docs = [
            {'id': 'd1', 'title': '제목1', 'content': '내용입니다'},
            {'id': 'd2', 'title': '제목2', 'content': '다른 내용입니다'},
        ]
        count = self.svc.add_documents_batch(docs)
        self.assertEqual(count, 2)
        self.assertEqual(len(self.svc.documents), 2)

    def test_recommendations_similar(self):
        """유사 문서 추천"""
        self.svc.add_document('d1', '파이썬 딥러닝', '파이썬 딥러닝 텐서플로 학습')
        self.svc.add_document('d2', '파이썬 머신러닝', '파이썬 딥러닝 사이킷런 학습')
        self.svc.add_document('d3', '요리 레시피', '김치찌개 만드는 방법 레시피')
        recs = self.svc.get_recommendations('d1', top_k=5)
        # d2가 d3보다 유사도 높아야 함
        if len(recs) >= 2:
            self.assertEqual(recs[0]['doc_id'], 'd2')

    def test_recommendations_nonexistent(self):
        """없는 문서 추천 → 빈 리스트"""
        self.assertEqual(self.svc.get_recommendations('nonexistent'), [])

    def test_recommendations_exclude(self):
        """제외 목록 적용"""
        self.svc.add_document('d1', '파이썬', '파이썬 프로그래밍')
        self.svc.add_document('d2', '파이썬', '파이썬 학습')
        recs = self.svc.get_recommendations('d1', exclude_ids=['d2'])
        doc_ids = [r['doc_id'] for r in recs]
        self.assertNotIn('d2', doc_ids)

    def test_build_link_graph(self):
        """링크 그래프 구축"""
        self.svc.add_document('d1', '파이썬', '파이썬 프로그래밍 딥러닝')
        self.svc.add_document('d2', '파이썬', '파이썬 딥러닝 학습')
        graph = self.svc.build_link_graph(top_k_per_doc=2)
        self.assertIn('d1', graph)
        self.assertIn('d2', graph)

    def test_suggest_link_anchors(self):
        """앵커 텍스트 제안"""
        source = '파이썬 프로그래밍은 재미있습니다. 딥러닝으로 모델을 만듭니다.'
        suggestions = self.svc.suggest_link_anchors(
            source, '파이썬 딥러닝 튜토리얼', 'https://example.com'
        )
        self.assertIsInstance(suggestions, list)

    def test_get_stats(self):
        """통계 조회"""
        self.svc.add_document('d1', '제목', '내용입니다 테스트')
        stats = self.svc.get_stats()
        self.assertEqual(stats['document_count'], 1)
        self.assertIn('total_links', stats)
        self.assertIn('avg_links_per_doc', stats)


if __name__ == '__main__':
    unittest.main()
