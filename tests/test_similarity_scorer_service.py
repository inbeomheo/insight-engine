"""similarity_scorer_service 단위 테스트"""
import unittest

from services.content.similarity_scorer_service import (
    score_similarity,
    _jaccard_similarity,
    _cosine_similarity,
    _extract_words,
)


class TestScoreSimilarity(unittest.TestCase):

    def test_identical_content(self):
        text = '동일한 콘텐츠입니다.'
        result = score_similarity(text, text)
        self.assertGreater(result['overall_score'], 0.9)
        self.assertEqual(result['verdict'], 'nearly_identical')

    def test_completely_different(self):
        result = score_similarity('한국어 텍스트입니다', 'completely different english text')
        self.assertLess(result['overall_score'], 0.3)

    def test_somewhat_similar(self):
        a = '인공지능은 머신러닝과 딥러닝을 포함합니다.'
        b = '인공지능 기술에는 머신러닝이 포함됩니다.'
        result = score_similarity(a, b)
        self.assertGreater(result['overall_score'], 0.2)

    def test_empty_content(self):
        result = score_similarity('', '내용')
        self.assertEqual(result['overall_score'], 0.0)

    def test_both_empty(self):
        result = score_similarity('', '')
        self.assertEqual(result['overall_score'], 0.0)

    def test_none_content(self):
        result = score_similarity(None, '내용')
        self.assertEqual(result['overall_score'], 0.0)

    def test_shared_keywords(self):
        a = '인공지능 머신러닝 딥러닝'
        b = '인공지능 자연어처리 딥러닝'
        result = score_similarity(a, b)
        self.assertIn('인공지능', result['shared_keywords'])
        self.assertIn('딥러닝', result['shared_keywords'])

    def test_unique_keywords(self):
        a = '파이썬 프로그래밍'
        b = '자바스크립트 개발'
        result = score_similarity(a, b)
        self.assertGreater(len(result['unique_to_a']), 0)
        self.assertGreater(len(result['unique_to_b']), 0)

    def test_verdict_values(self):
        valid = {'nearly_identical', 'very_similar', 'somewhat_similar', 'slightly_similar', 'different'}
        result = score_similarity('텍스트', '다른 텍스트')
        self.assertIn(result['verdict'], valid)

    def test_structure_similarity_same_headings(self):
        a = '# 서론\n내용\n## 본론\n내용'
        b = '# 서론\n다른 내용\n## 본론\n다른 내용'
        result = score_similarity(a, b)
        self.assertEqual(result['structure_similarity'], 1.0)

    def test_structure_similarity_different_headings(self):
        a = '# 서론\n내용'
        b = '# 결론\n내용'
        result = score_similarity(a, b)
        self.assertLess(result['structure_similarity'], 1.0)

    def test_score_range(self):
        result = score_similarity('텍스트 A', '텍스트 B')
        self.assertGreaterEqual(result['overall_score'], 0.0)
        self.assertLessEqual(result['overall_score'], 1.0)


class TestJaccardSimilarity(unittest.TestCase):

    def test_identical(self):
        self.assertEqual(_jaccard_similarity({'a', 'b'}, {'a', 'b'}), 1.0)

    def test_disjoint(self):
        self.assertEqual(_jaccard_similarity({'a'}, {'b'}), 0.0)

    def test_partial(self):
        sim = _jaccard_similarity({'a', 'b', 'c'}, {'b', 'c', 'd'})
        self.assertAlmostEqual(sim, 0.5)

    def test_both_empty(self):
        self.assertEqual(_jaccard_similarity(set(), set()), 1.0)


class TestCosineSimilarity(unittest.TestCase):

    def test_identical(self):
        from collections import Counter
        c = Counter({'a': 3, 'b': 2})
        self.assertAlmostEqual(_cosine_similarity(c, c), 1.0)

    def test_empty(self):
        from collections import Counter
        self.assertEqual(_cosine_similarity(Counter(), Counter()), 0.0)


class TestExtractWords(unittest.TestCase):

    def test_korean(self):
        words = _extract_words('한국어 테스트')
        self.assertIn('한국어', words)

    def test_english(self):
        words = _extract_words('hello world test')
        self.assertIn('hello', words)

    def test_empty(self):
        self.assertEqual(_extract_words(''), [])


if __name__ == '__main__':
    unittest.main()
