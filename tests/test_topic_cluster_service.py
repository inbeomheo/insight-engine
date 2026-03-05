"""topic_cluster_service 단위 테스트"""
import unittest

from services.topic_cluster_service import cluster_contents, _tokenize, _cosine_similarity


class TestTokenize(unittest.TestCase):

    def test_basic(self):
        tokens = _tokenize('Python 프로그래밍 학습')
        self.assertIn('python', tokens)
        self.assertIn('프로그래밍', tokens)

    def test_stopwords_removed(self):
        tokens = _tokenize('the quick brown fox')
        self.assertNotIn('the', tokens)
        self.assertIn('quick', tokens)

    def test_short_words_excluded(self):
        tokens = _tokenize('I x a developer')
        self.assertNotIn('x', tokens)  # 2자 미만
        self.assertNotIn('a', tokens)  # 1자


class TestCosineSimilarity(unittest.TestCase):

    def test_identical(self):
        v = {'a': 1.0, 'b': 2.0}
        self.assertAlmostEqual(_cosine_similarity(v, v), 1.0, places=5)

    def test_orthogonal(self):
        v1 = {'a': 1.0}
        v2 = {'b': 1.0}
        self.assertEqual(_cosine_similarity(v1, v2), 0.0)

    def test_empty(self):
        self.assertEqual(_cosine_similarity({}, {'a': 1.0}), 0.0)


class TestClusterContents(unittest.TestCase):

    def test_empty(self):
        self.assertEqual(cluster_contents([]), [])

    def test_single_item(self):
        result = cluster_contents([{'id': '1', 'title': 'test', 'content': 'hello world'}])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['content_ids'], ['1'])

    def test_similar_grouped(self):
        contents = [
            {'id': 'a', 'title': 'Python 프로그래밍', 'content': 'Python 개발 학습 튜토리얼 프로그래밍'},
            {'id': 'b', 'title': 'Python 개발', 'content': 'Python 프로그래밍 입문 개발자 튜토리얼'},
            {'id': 'c', 'title': '요리 레시피', 'content': '김치찌개 레시피 요리 방법 재료'},
        ]
        result = cluster_contents(contents, threshold=0.1)
        # Python 관련 2개가 같은 클러스터, 요리가 별도 클러스터
        all_ids = [cid for cluster in result for cid in cluster['content_ids']]
        self.assertEqual(sorted(all_ids), ['a', 'b', 'c'])

    def test_keywords_present(self):
        contents = [
            {'id': '1', 'title': 'AI 기술', 'content': '인공지능 머신러닝 딥러닝 기술 개발'},
        ]
        result = cluster_contents(contents)
        self.assertTrue(len(result[0]['keywords']) > 0)

    def test_uses_index_as_id(self):
        contents = [{'title': 'no id', 'content': 'test content'}]
        result = cluster_contents(contents)
        self.assertEqual(result[0]['content_ids'], ['0'])


if __name__ == '__main__':
    unittest.main()
