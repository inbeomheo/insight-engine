"""Sentence Connector Variety Analyzer 서비스 테스트."""
import unittest
from services.analysis.sentence_analysis_service import analyze_connector_variety


class TestSentenceConnectorVariety(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_connector_variety('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['connector_count'], 0)

    def test_none_content(self):
        result = analyze_connector_variety(None)
        self.assertEqual(result['score'], 100.0)

    def test_no_connectors(self):
        content = '사과는 빨갛습니다. 바나나는 노랗습니다. 포도는 보라색입니다.'
        result = analyze_connector_variety(content)
        self.assertEqual(result['summary']['connector_count'], 0)

    def test_korean_connectors(self):
        content = '그리고 추가 내용입니다. 그러나 반대 의견도 있습니다. 따라서 결론을 내립니다.'
        result = analyze_connector_variety(content)
        self.assertEqual(result['summary']['connector_count'], 3)
        self.assertGreaterEqual(result['summary']['unique_connectors'], 3)

    def test_english_connectors(self):
        content = 'However, there are issues. Moreover, costs are high. Therefore, we need changes.'
        result = analyze_connector_variety(content)
        self.assertGreaterEqual(result['summary']['connector_count'], 3)

    def test_repeated_connector(self):
        content = '그리고 첫째입니다. 그리고 둘째입니다. 그리고 셋째입니다. 그리고 넷째입니다.'
        result = analyze_connector_variety(content)
        self.assertLess(result['summary']['variety_rate'], 50.0)

    def test_category_distribution(self):
        content = '그리고 순접입니다. 그러나 역접입니다. 따라서 인과입니다.'
        result = analyze_connector_variety(content)
        dist = result['category_distribution']
        self.assertGreater(len(dist), 0)

    def test_variety_rate_high(self):
        content = '그리고 하나입니다. 그러나 둘입니다. 따라서 셋입니다. 예를 들어 넷입니다.'
        result = analyze_connector_variety(content)
        self.assertEqual(result['summary']['variety_rate'], 100.0)

    def test_suggestions_no_connectors(self):
        content = '문장 하나입니다. 문장 둘입니다. 문장 셋입니다.'
        result = analyze_connector_variety(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_suggestions_repeated(self):
        content = '그리고 하나. 그리고 둘. 그리고 셋. 그리고 넷.'
        result = analyze_connector_variety(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_connector_structure(self):
        content = '그리고 테스트입니다. 그러나 확인합니다.'
        result = analyze_connector_variety(content)
        if result['connectors']:
            c = result['connectors'][0]
            self.assertIn('word', c)
            self.assertIn('category', c)
            self.assertIn('sentence', c)

    def test_return_structure(self):
        content = '테스트 문장입니다.'
        result = analyze_connector_variety(content)
        self.assertIn('connectors', result)
        self.assertIn('category_distribution', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('connector_count', result['summary'])
        self.assertIn('variety_rate', result['summary'])


if __name__ == '__main__':
    unittest.main()
