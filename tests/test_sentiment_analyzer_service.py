"""sentiment_analyzer_service 단위 테스트"""
import unittest

from services.sentiment_analyzer_service import (
    analyze_sentiment,
    _score_paragraph,
)


class TestAnalyzeSentiment(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_sentiment('')
        self.assertEqual(result['overall_sentiment'], 'neutral')
        self.assertEqual(result['overall_score'], 0.0)

    def test_none_content(self):
        result = analyze_sentiment(None)
        self.assertEqual(result['overall_sentiment'], 'neutral')

    def test_positive_content(self):
        content = '이 제품은 매우 훌륭하고 효과적입니다. 성공적인 결과를 가져왔고 편리합니다. 추천합니다.'
        result = analyze_sentiment(content)
        self.assertEqual(result['overall_sentiment'], 'positive')
        self.assertGreater(result['overall_score'], 0)
        self.assertGreater(len(result['top_positive_words']), 0)

    def test_negative_content(self):
        content = '이 시스템에는 심각한 문제가 있고 위험합니다. 실패할 가능성이 높고 불편합니다. 리스크가 큽니다.'
        result = analyze_sentiment(content)
        self.assertEqual(result['overall_sentiment'], 'negative')
        self.assertLess(result['overall_score'], 0)
        self.assertGreater(len(result['top_negative_words']), 0)

    def test_neutral_content(self):
        content = '오늘 날씨가 흐립니다. 내일은 비가 올 수도 있습니다. 기온은 보통 수준입니다.'
        result = analyze_sentiment(content)
        self.assertEqual(result['overall_sentiment'], 'neutral')

    def test_distribution_sums_to_one(self):
        content = '좋은 제품이지만 문제도 있습니다. 전반적으로 보통입니다.'
        result = analyze_sentiment(content)
        dist = result['distribution']
        total = dist['positive'] + dist['negative'] + dist['neutral']
        self.assertAlmostEqual(total, 1.0, delta=0.01)

    def test_paragraph_sentiments(self):
        content = """좋은 결과를 얻었습니다. 효과적이었습니다.

문제가 발생했고 위험한 상황이었습니다."""
        result = analyze_sentiment(content)
        self.assertGreater(len(result['paragraph_sentiments']), 0)
        for ps in result['paragraph_sentiments']:
            self.assertIn('text_preview', ps)
            self.assertIn('sentiment', ps)
            self.assertIn('score', ps)

    def test_tone_summary_exists(self):
        result = analyze_sentiment('좋은 결과입니다.')
        self.assertIsInstance(result['tone_summary'], str)
        self.assertGreater(len(result['tone_summary']), 0)

    def test_score_bounded(self):
        result = analyze_sentiment('좋은 훌륭 우수 효과적 성공 향상 ' * 20)
        self.assertGreaterEqual(result['overall_score'], -1.0)
        self.assertLessEqual(result['overall_score'], 1.0)


class TestScoreParagraph(unittest.TestCase):

    def test_positive_paragraph(self):
        score, pos, neg = _score_paragraph('훌륭하고 효과적인 결과')
        self.assertGreater(score, 0)
        self.assertGreater(len(pos), 0)

    def test_negative_paragraph(self):
        score, pos, neg = _score_paragraph('심각한 문제와 위험한 리스크')
        self.assertLess(score, 0)
        self.assertGreater(len(neg), 0)

    def test_empty_paragraph(self):
        score, pos, neg = _score_paragraph('')
        self.assertEqual(score, 0.0)


if __name__ == '__main__':
    unittest.main()
