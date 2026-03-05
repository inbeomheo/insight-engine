"""tone_analyzer_service 단위 테스트"""
import unittest

from services.tone_analyzer_service import analyze_tone


class TestAnalyzeTone(unittest.TestCase):

    def test_empty_text(self):
        result = analyze_tone('')
        self.assertEqual(result['primary_tone'], 'neutral')
        self.assertIsInstance(result['scores'], dict)

    def test_none_text(self):
        result = analyze_tone(None)
        self.assertEqual(result['primary_tone'], 'neutral')

    def test_professional_tone(self):
        text = '분석 결과를 토대로 전략을 수립하고 효율적인 프로세스를 구현합니다. 시스템 최적화를 통해 성과를 달성합니다.'
        result = analyze_tone(text)
        self.assertIn('professional', result['scores'])
        self.assertGreater(result['scores']['professional'], 0)

    def test_casual_tone(self):
        text = '진짜 대박이에요! 솔직히 완전 꿀팁인데 개인적으로 엄청 추천해요 ㅋㅋ'
        result = analyze_tone(text)
        self.assertGreater(result['scores']['casual'], 0)

    def test_academic_tone(self):
        text = '본 연구에서는 가설을 검증하기 위해 실험을 수행하였다. 통계적으로 유의미한 결과를 도출하였으며 선행 연구(2024)와 일치한다.'
        result = analyze_tone(text)
        self.assertGreater(result['scores']['academic'], 0)

    def test_emotional_tone(self):
        text = '가슴이 따뜻해지는 감동적인 이야기... 소중한 사람에게 사랑을 전하세요. 감사합니다.'
        result = analyze_tone(text)
        self.assertGreater(result['scores']['emotional'], 0)

    def test_returns_suggestions(self):
        text = '분석 결과 시스템 전략 최적화 프로세스'
        result = analyze_tone(text)
        self.assertIsInstance(result['suggestions'], list)

    def test_scores_sum_reasonable(self):
        text = '일반적인 텍스트입니다.'
        result = analyze_tone(text)
        for tone, score in result['scores'].items():
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)


if __name__ == '__main__':
    unittest.main()
