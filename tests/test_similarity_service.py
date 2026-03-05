"""similarity_service 단위 테스트"""
import unittest

from services.similarity_service import compare_similarity


class TestCompareSimilarity(unittest.TestCase):

    def test_identical_texts(self):
        text = 'Python 프로그래밍 학습 가이드'
        score = compare_similarity(text, text)
        self.assertAlmostEqual(score, 1.0, places=2)

    def test_completely_different(self):
        score = compare_similarity(
            'Python 프로그래밍 개발 코딩',
            '김치찌개 요리 레시피 재료 준비',
        )
        self.assertLess(score, 0.3)

    def test_partially_similar(self):
        score = compare_similarity(
            'Python 웹 개발 프레임워크',
            'Python 데이터 분석 프레임워크',
        )
        self.assertGreater(score, 0.0)
        self.assertLess(score, 1.0)

    def test_empty_returns_zero(self):
        self.assertEqual(compare_similarity('', 'text'), 0.0)
        self.assertEqual(compare_similarity('text', ''), 0.0)
        self.assertEqual(compare_similarity('', ''), 0.0)

    def test_none_returns_zero(self):
        self.assertEqual(compare_similarity(None, 'text'), 0.0)

    def test_score_range(self):
        score = compare_similarity('hello world', 'hello there')
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_symmetry(self):
        a = 'Python 개발자 가이드'
        b = '자바스크립트 개발자 튜토리얼'
        self.assertAlmostEqual(
            compare_similarity(a, b),
            compare_similarity(b, a),
            places=4,
        )


if __name__ == '__main__':
    unittest.main()
