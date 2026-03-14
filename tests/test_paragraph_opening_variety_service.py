"""Paragraph Opening Variety Checker 서비스 테스트."""
import unittest
from services.analysis.paragraph_opening_variety_service import check_paragraph_opening_variety


class TestParagraphOpeningVariety(unittest.TestCase):

    def test_empty_content(self):
        result = check_paragraph_opening_variety('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['total_paragraphs'], 0)

    def test_none_content(self):
        result = check_paragraph_opening_variety(None)
        self.assertEqual(result['score'], 100.0)

    def test_single_paragraph(self):
        content = '하나의 문단만 있습니다.'
        result = check_paragraph_opening_variety(content)
        self.assertEqual(result['summary']['total_paragraphs'], 1)
        self.assertEqual(result['score'], 100.0)

    def test_varied_openings(self):
        content = """첫째로 이것이 중요합니다.

그러나 다른 관점도 있습니다.

왜 이런 현상이 발생할까요.

연구에 따르면 결과가 다릅니다.

결론적으로 모두 중요합니다."""
        result = check_paragraph_opening_variety(content)
        self.assertGreaterEqual(result['summary']['variety_rate'], 80.0)

    def test_repetitive_openings(self):
        content = """테스트 코드를 작성합니다.

테스트 코드를 검증합니다.

테스트 코드를 수정합니다.

테스트 코드를 배포합니다."""
        result = check_paragraph_opening_variety(content)
        repeated = [o for o in result['openings'] if o['is_repeated']]
        self.assertGreater(len(repeated), 0)

    def test_english_varied(self):
        content = """First, let me explain.

However, there are concerns.

Research shows different results.

Finally, we conclude."""
        result = check_paragraph_opening_variety(content)
        self.assertGreaterEqual(result['summary']['variety_rate'], 80.0)

    def test_english_repetitive(self):
        content = """The system works well.

The system has features.

The system is fast.

The system costs less."""
        result = check_paragraph_opening_variety(content)
        self.assertGreater(len(result['pattern_frequency']), 0)

    def test_pattern_frequency(self):
        content = """테스트 코드를 작성합니다.

테스트 코드를 검증합니다.

테스트 코드를 실행합니다.

다른 시작입니다."""
        result = check_paragraph_opening_variety(content)
        self.assertGreater(len(result['pattern_frequency']), 0)
        self.assertGreater(result['pattern_frequency'][0]['count'], 1)

    def test_score_high_variety(self):
        content = """첫 번째 관점입니다.

반면에 다른 의견도 있습니다.

통계에 따르면 결과가 다릅니다.

결론적으로 요약합니다."""
        result = check_paragraph_opening_variety(content)
        self.assertGreaterEqual(result['score'], 70.0)

    def test_score_low_variety(self):
        content = '\n\n'.join([f'이것은 문단 {i}입니다.' for i in range(6)])
        result = check_paragraph_opening_variety(content)
        self.assertLess(result['score'], 90.0)

    def test_suggestions_repetitive(self):
        content = '\n\n'.join(['이것은 반복 문단입니다.'] * 5)
        result = check_paragraph_opening_variety(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_suggestions_good(self):
        content = """첫째 설명.\n\n둘째 관점.\n\n셋째 결론.\n\n넷째 요약."""
        result = check_paragraph_opening_variety(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_return_structure(self):
        content = '문단 하나.\n\n문단 둘.'
        result = check_paragraph_opening_variety(content)
        self.assertIn('openings', result)
        self.assertIn('pattern_frequency', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_paragraphs', result['summary'])
        self.assertIn('variety_rate', result['summary'])


if __name__ == '__main__':
    unittest.main()
