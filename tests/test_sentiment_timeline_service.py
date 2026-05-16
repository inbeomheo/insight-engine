"""sentiment_timeline_service 단위 테스트"""
import unittest

from services.content.sentiment_timeline_service import (
    analyze_sentiment_timeline,
    _analyze_paragraph_sentiment,
    _detect_trend,
)


class TestAnalyzeSentimentTimeline(unittest.TestCase):

    def test_empty(self):
        result = analyze_sentiment_timeline('')
        self.assertEqual(result['total_sections'], 0)

    def test_none(self):
        result = analyze_sentiment_timeline(None)
        self.assertEqual(result['total_sections'], 0)

    def test_positive_content(self):
        text = '이것은 훌륭한 성공 사례입니다. 성장과 발전이 뛰어납니다.'
        result = analyze_sentiment_timeline(text)
        self.assertEqual(result['overall']['label'], 'positive')

    def test_negative_content(self):
        text = '문제 위험 실패 우려 손실 하락 악화 피해가 발생했습니다.'
        result = analyze_sentiment_timeline(text)
        self.assertEqual(result['overall']['label'], 'negative')

    def test_neutral_content(self):
        text = '오늘 날씨가 맑습니다. 내일은 비가 올 수 있습니다.'
        result = analyze_sentiment_timeline(text)
        self.assertEqual(result['overall']['label'], 'neutral')

    def test_multi_section(self):
        text = '# 서론\n좋은 소식입니다.\n# 문제점\n심각한 위험이 있습니다.\n# 결론\n해결 가능합니다.'
        result = analyze_sentiment_timeline(text)
        self.assertEqual(result['total_sections'], 3)
        self.assertEqual(len(result['timeline']), 3)

    def test_timeline_structure(self):
        text = '# 섹션\n테스트 내용입니다.'
        result = analyze_sentiment_timeline(text)
        for entry in result['timeline']:
            self.assertIn('index', entry)
            self.assertIn('score', entry)
            self.assertIn('label', entry)
            self.assertIn('heading', entry)

    def test_positive_ratio(self):
        text = '# A\n성공적입니다.\n# B\n문제 발생.\n# C\n좋은 결과.'
        result = analyze_sentiment_timeline(text)
        self.assertGreaterEqual(result['positive_ratio'], 0.0)
        self.assertLessEqual(result['positive_ratio'], 1.0)

    def test_trend_detected(self):
        text = '# A\n실패와 문제가 있습니다.\n# B\n여전히 위험합니다.\n# C\n성공적으로 개선되었습니다.\n# D\n훌륭한 성과를 달성했습니다.'
        result = analyze_sentiment_timeline(text)
        self.assertIn(result['trend'], ['improving', 'declining', 'stable'])

    def test_score_range(self):
        text = '긍정적 성공 훌륭합니다.'
        result = analyze_sentiment_timeline(text)
        self.assertGreaterEqual(result['overall']['score'], -1.0)
        self.assertLessEqual(result['overall']['score'], 1.0)


class TestParagraphSentiment(unittest.TestCase):

    def test_positive(self):
        result = _analyze_paragraph_sentiment('훌륭한 성공 사례')
        self.assertGreater(result['score'], 0)
        self.assertEqual(result['label'], 'positive')

    def test_negative(self):
        result = _analyze_paragraph_sentiment('심각한 문제 위험')
        self.assertLess(result['score'], 0)

    def test_empty(self):
        result = _analyze_paragraph_sentiment('')
        self.assertEqual(result['score'], 0.0)

    def test_counts(self):
        result = _analyze_paragraph_sentiment('성공 실패 성장')
        self.assertGreater(result['positive'], 0)
        self.assertGreater(result['negative'], 0)


class TestDetectTrend(unittest.TestCase):

    def test_improving(self):
        self.assertEqual(_detect_trend([-0.5, -0.3, 0.2, 0.8]), 'improving')

    def test_declining(self):
        self.assertEqual(_detect_trend([0.8, 0.5, -0.2, -0.5]), 'declining')

    def test_stable(self):
        self.assertEqual(_detect_trend([0.1, 0.05, 0.1, 0.05]), 'stable')

    def test_single(self):
        self.assertEqual(_detect_trend([0.5]), 'stable')


if __name__ == '__main__':
    unittest.main()
