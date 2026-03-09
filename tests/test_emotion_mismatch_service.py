"""감정 미스매치 탐지 서비스 테스트"""
import unittest
from services.emotion_mismatch_service import (
    detect_emotion, check_mismatch, scan_content,
    EmotionAnalysis, MismatchReport
)


class TestEmotionMismatchService(unittest.TestCase):

    def test_detect_emotion_joy(self):
        result = detect_emotion('정말 기쁘고 행복한 하루였습니다!')
        self.assertIsInstance(result, EmotionAnalysis)
        self.assertEqual(result.detected_emotion, 'joy')
        self.assertGreater(len(result.keywords_found), 0)

    def test_detect_emotion_sadness(self):
        result = detect_emotion('너무 슬프고 우울한 날이에요')
        self.assertEqual(result.detected_emotion, 'sadness')

    def test_detect_emotion_anger(self):
        result = detect_emotion('정말 화나고 짜증나는 상황')
        self.assertEqual(result.detected_emotion, 'anger')

    def test_detect_emotion_neutral(self):
        result = detect_emotion('오늘 날씨가 맑습니다')
        self.assertEqual(result.detected_emotion, 'neutral')

    def test_detect_emotion_confidence_range(self):
        result = detect_emotion('기쁘고 즐거운 시간')
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)

    def test_check_mismatch_detected(self):
        mismatch = check_mismatch('정말 슬프고 우울해요', 'joy')
        self.assertIsNotNone(mismatch)
        self.assertEqual(mismatch['intended'], 'joy')
        self.assertEqual(mismatch['detected'], 'sadness')

    def test_check_mismatch_no_mismatch(self):
        mismatch = check_mismatch('기쁘고 행복해요', 'joy')
        self.assertIsNone(mismatch)

    def test_check_mismatch_neutral_ignored(self):
        mismatch = check_mismatch('오늘 날씨가 좋습니다', 'joy')
        self.assertIsNone(mismatch)

    def test_scan_content(self):
        content = "정말 기쁜 소식입니다.\n하지만 슬프게도 문제가 있습니다.\n해결해봅시다."
        report = scan_content(content, 'joy')
        self.assertIsInstance(report, MismatchReport)
        self.assertGreater(len(report.analyses), 0)

    def test_scan_content_severity_low(self):
        content = "기쁜 하루. 행복합니다. 좋아요. 최고!"
        report = scan_content(content, 'joy')
        self.assertEqual(report.severity, 'low')

    def test_scan_content_severity_high(self):
        content = "슬프고 우울해요\n화나고 짜증나요\n무섭고 두려워요"
        report = scan_content(content, 'joy')
        self.assertEqual(report.severity, 'high')

    def test_detect_emotion_english(self):
        result = detect_emotion('I am so happy and glad')
        self.assertEqual(result.detected_emotion, 'joy')


if __name__ == '__main__':
    unittest.main()
