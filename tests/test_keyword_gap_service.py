"""keyword_gap_service 단위 테스트"""
import unittest
from unittest.mock import patch

from services.keyword_gap_service import analyze_keyword_gap, _extract_keywords


class TestExtractKeywords(unittest.TestCase):

    def test_basic(self):
        keywords = _extract_keywords('Python 프로그래밍 학습 Python')
        self.assertIn('python', keywords)
        self.assertIn('프로그래밍', keywords)

    def test_stopwords_excluded(self):
        keywords = _extract_keywords('the is and Python')
        self.assertIn('python', keywords)
        self.assertNotIn('the', keywords)


class TestAnalyzeKeywordGap(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_keyword_gap('', [])
        self.assertEqual(result['my_keywords'], [])

    @patch('services.keyword_gap_service._fetch_competitor_text')
    def test_with_competitor(self, mock_fetch):
        mock_fetch.return_value = 'Python 머신러닝 딥러닝 데이터분석 통계'

        result = analyze_keyword_gap(
            'Python 프로그래밍 웹개발',
            ['https://example.com'],
        )

        self.assertIn('python', result['common_keywords'])
        # 머신러닝은 경쟁에만 있으므로 missing에 포함
        self.assertIn('머신러닝', result['missing_keywords'])
        # 웹개발은 내 콘텐츠에만 있으므로 unique에 포함
        self.assertIn('웹개발', result['unique_keywords'])

    @patch('services.keyword_gap_service._fetch_competitor_text')
    def test_no_competitor_content(self, mock_fetch):
        mock_fetch.return_value = ''

        result = analyze_keyword_gap('Python 개발', ['https://example.com'])
        self.assertEqual(result['missing_keywords'], [])
        self.assertGreater(len(result['my_keywords']), 0)

    def test_no_urls(self):
        result = analyze_keyword_gap('Python 개발', [])
        self.assertEqual(result['missing_keywords'], [])


if __name__ == '__main__':
    unittest.main()
