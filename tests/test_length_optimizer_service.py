"""length_optimizer_service 단위 테스트"""
import unittest

from services.length_optimizer_service import analyze_length


class TestAnalyzeLength(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_length('')
        self.assertEqual(result['char_count'], 0)
        self.assertEqual(result['status'], 'short')

    def test_short_content(self):
        text = '짧은 글입니다.'
        result = analyze_length(text, 'blog')
        self.assertEqual(result['status'], 'short')
        self.assertIn('부족', result['recommendation'])

    def test_optimal_content(self):
        # 블로그 최적 범위: 1500~3000자
        text = '가' * 2000
        result = analyze_length(text, 'blog')
        self.assertEqual(result['status'], 'optimal')
        self.assertIn('적합', result['recommendation'])

    def test_long_content(self):
        text = '가' * 5000
        result = analyze_length(text, 'blog')
        self.assertEqual(result['status'], 'long')
        self.assertIn('초과', result['recommendation'])

    def test_twitter_platform(self):
        text = '트위터 글' * 100  # 400자
        result = analyze_length(text, 'twitter')
        self.assertEqual(result['status'], 'long')

    def test_reading_time(self):
        text = '가' * 1000  # 1000자 → 약 2분
        result = analyze_length(text)
        self.assertEqual(result['reading_time_min'], 2.0)

    def test_unknown_platform_fallback(self):
        result = analyze_length('test', 'unknown_platform')
        # blog로 폴백
        self.assertEqual(result['optimal_range']['min'], 1500)

    def test_word_and_sentence_count(self):
        text = '첫 번째 문장입니다. 두 번째 문장입니다.'
        result = analyze_length(text)
        self.assertGreater(result['word_count'], 0)
        self.assertEqual(result['sentence_count'], 2)


if __name__ == '__main__':
    unittest.main()
