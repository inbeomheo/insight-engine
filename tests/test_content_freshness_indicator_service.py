"""Content Freshness Indicator 서비스 테스트."""
import unittest
from services.seo.content_freshness_indicator_service import check_content_freshness


class TestContentFreshnessIndicator(unittest.TestCase):

    def test_empty_content(self):
        result = check_content_freshness('')
        self.assertEqual(result['score'], 50.0)

    def test_none_content(self):
        result = check_content_freshness(None)
        self.assertEqual(result['score'], 50.0)

    def test_fresh_content(self):
        content = '2026년 3월 최신 AI 트렌드를 분석합니다. 최근 GPT 기술이 발전했습니다.'
        result = check_content_freshness(content)
        self.assertEqual(result['summary']['freshness_level'], 'fresh')
        self.assertGreaterEqual(result['score'], 70.0)

    def test_outdated_content(self):
        content = '2018년에 작성된 글입니다. 과거에 사용하던 방법입니다. ActiveX를 설치하세요.'
        result = check_content_freshness(content)
        self.assertIn(result['summary']['freshness_level'], ('outdated', 'aging'))

    def test_date_references(self):
        content = '2025년 1월에 업데이트되었습니다. 2024.12 기준 데이터입니다.'
        result = check_content_freshness(content)
        self.assertTrue(result['summary']['has_dates'])
        self.assertGreater(len(result['date_references']), 0)

    def test_newest_year(self):
        content = '2020년 보고서입니다. 2025년 업데이트됨.'
        result = check_content_freshness(content)
        self.assertEqual(result['summary']['newest_year'], 2025)

    def test_recent_signals(self):
        content = '최근 연구에 따르면 결과가 다릅니다. 현재 가장 많이 사용됩니다.'
        result = check_content_freshness(content)
        self.assertGreater(result['time_signals'].get('recent', 0), 0)

    def test_trend_keywords(self):
        content = 'AI와 LLM 기반 자동화가 트렌드입니다. ChatGPT와 Gemini 활용법.'
        result = check_content_freshness(content)
        self.assertGreater(result['freshness_indicators']['trend_keywords'], 0)

    def test_outdated_terms(self):
        content = 'Flash Player를 설치하고 ActiveX를 사용하세요.'
        result = check_content_freshness(content)
        self.assertGreater(result['freshness_indicators']['outdated_terms'], 0)

    def test_no_date_content(self):
        content = '일반적인 글입니다. 날짜 참조가 없습니다.'
        result = check_content_freshness(content)
        self.assertFalse(result['summary']['has_dates'])

    def test_score_range(self):
        content = '테스트 콘텐츠입니다.'
        result = check_content_freshness(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_suggestions_exist(self):
        content = '간단한 글입니다.'
        result = check_content_freshness(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_return_structure(self):
        content = '테스트입니다.'
        result = check_content_freshness(content)
        self.assertIn('date_references', result)
        self.assertIn('time_signals', result)
        self.assertIn('freshness_indicators', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('freshness_level', result['summary'])


if __name__ == '__main__':
    unittest.main()
