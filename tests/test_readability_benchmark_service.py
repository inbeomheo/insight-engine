"""readability_benchmark_service 단위 테스트"""
import unittest

from services.analysis.readability_benchmark_service import (
    benchmark_readability,
    get_categories,
    _calculate_metrics,
)


class TestBenchmarkReadability(unittest.TestCase):

    def test_empty_content(self):
        result = benchmark_readability('')
        self.assertEqual(result['overall_status'], 'below')
        self.assertEqual(result['percentile'], 0)

    def test_none_content(self):
        result = benchmark_readability(None)
        self.assertEqual(result['overall_status'], 'below')

    def test_basic_benchmark(self):
        content = """파이썬은 프로그래밍 언어입니다. 간결한 문법으로 초보자도 쉽게 배울 수 있습니다.
다양한 라이브러리를 제공하며 데이터 과학에서 널리 사용됩니다.
웹 개발, 자동화, 인공지능 등 다양한 분야에 활용 가능합니다."""
        result = benchmark_readability(content, 'blog')
        self.assertEqual(result['category'], 'blog')
        self.assertEqual(result['category_label'], '블로그')
        self.assertIn('avg_sentence_length', result['metrics'])
        self.assertIn('vocabulary_diversity', result['metrics'])
        self.assertIn(result['overall_status'], ('above', 'within', 'below'))
        self.assertGreaterEqual(result['percentile'], 0)
        self.assertLessEqual(result['percentile'], 100)

    def test_different_categories(self):
        content = '간단한 테스트 콘텐츠입니다. 여러 문장을 포함합니다.'
        for cat in ('blog', 'news', 'academic', 'marketing', 'sns'):
            result = benchmark_readability(content, cat)
            self.assertEqual(result['category'], cat)

    def test_invalid_category_defaults_to_blog(self):
        result = benchmark_readability('테스트', 'invalid')
        self.assertEqual(result['category'], 'blog')

    def test_suggestions_exist(self):
        result = benchmark_readability('짧은 테스트.')
        self.assertIsInstance(result['suggestions'], list)
        self.assertGreater(len(result['suggestions']), 0)


class TestGetCategories(unittest.TestCase):

    def test_returns_categories(self):
        cats = get_categories()
        self.assertGreater(len(cats), 0)
        self.assertTrue(all('id' in c and 'label' in c for c in cats))


class TestCalculateMetrics(unittest.TestCase):

    def test_calculates_metrics(self):
        metrics = _calculate_metrics('한국어 문장입니다. 두 번째 문장입니다.')
        self.assertIn('avg_sentence_length', metrics)
        self.assertIn('vocabulary_diversity', metrics)
        self.assertIn('foreign_ratio', metrics)

    def test_foreign_ratio_with_english(self):
        metrics = _calculate_metrics('This is a test with Python and JavaScript code.')
        self.assertGreater(metrics['foreign_ratio'], 0)


if __name__ == '__main__':
    unittest.main()
