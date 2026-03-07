"""Quotation Usage Analyzer 서비스 테스트."""
import unittest
from services.quotation_usage_analyzer_service import analyze_quotation_usage


class TestQuotationUsageAnalyzer(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_quotation_usage('')
        self.assertEqual(result['summary']['total_quotes'], 0)

    def test_none_content(self):
        result = analyze_quotation_usage(None)
        self.assertEqual(result['summary']['total_quotes'], 0)

    def test_no_quotes(self):
        content = '이 글에는 인용문이 없습니다. 순수한 텍스트입니다.'
        result = analyze_quotation_usage(content)
        self.assertEqual(result['summary']['total_quotes'], 0)
        self.assertEqual(result['summary']['level'], 'none')

    def test_direct_quote(self):
        content = '"이 프로젝트는 매우 중요하며 반드시 성공해야 합니다"라고 팀장이 말했습니다.'
        result = analyze_quotation_usage(content)
        self.assertGreater(result['summary']['direct_quotes'], 0)

    def test_emphasis_quote(self):
        content = '이것은 "중요한" 포인트입니다. "핵심" 개념을 이해하세요.'
        result = analyze_quotation_usage(content)
        self.assertGreater(result['summary']['emphasis_quotes'], 0)

    def test_block_quote(self):
        content = '본문입니다.\n\n> 이것은 블록 인용문입니다.\n\n다시 본문입니다.'
        result = analyze_quotation_usage(content)
        self.assertGreater(result['summary']['block_quotes'], 0)

    def test_korean_quotes(self):
        content = '「이것은 한국어 인용입니다」라고 저자가 말했습니다.'
        result = analyze_quotation_usage(content)
        self.assertGreater(result['summary']['direct_quotes'], 0)

    def test_attribution_detected(self):
        content = '"기술이 세상을 바꿀 것입니다"라고 전문가가 말했습니다.'
        result = analyze_quotation_usage(content)
        self.assertGreater(result['summary']['with_attribution'], 0)

    def test_multiple_quotes(self):
        content = ('"첫 번째 인용문이며 여러 단어를 포함합니다." '
                   '"두 번째 인용문도 충분히 긴 문장입니다." '
                   '"세 번째 인용도 마찬가지로 적절한 길이입니다."')
        result = analyze_quotation_usage(content)
        self.assertGreaterEqual(result['summary']['total_quotes'], 3)

    def test_level_moderate(self):
        quotes = ' '.join([f'"인용 {i}번 충분히 긴 문장입니다."' for i in range(5)])
        content = f'서론입니다. {quotes} 결론입니다.'
        result = analyze_quotation_usage(content)
        self.assertIn(result['summary']['level'], ('moderate', 'heavy'))

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = analyze_quotation_usage(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '"인용" 확인입니다.'
        result = analyze_quotation_usage(content)
        self.assertIn('quotations', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_quotes', result['summary'])
        self.assertIn('direct_quotes', result['summary'])
        self.assertIn('emphasis_quotes', result['summary'])
        self.assertIn('block_quotes', result['summary'])

    def test_quotation_structure(self):
        content = '"테스트 인용문입니다."'
        result = analyze_quotation_usage(content)
        for q in result['quotations']:
            self.assertIn('text', q)
            self.assertIn('type', q)

    def test_suggestions_for_no_quotes(self):
        content = '인용문이 없는 긴 글입니다. 여러 문장이 있습니다. 하지만 인용이 없습니다.'
        result = analyze_quotation_usage(content)
        has_no_quote_suggestion = any('인용' in s and '없' in s for s in result['suggestions'])
        self.assertTrue(has_no_quote_suggestion)

    def test_max_20_quotations(self):
        quotes = ' '.join([f'"인용 번호 {i}입니다"' for i in range(25)])
        content = f'서론입니다. {quotes}'
        result = analyze_quotation_usage(content)
        self.assertLessEqual(len(result['quotations']), 20)


if __name__ == '__main__':
    unittest.main()
