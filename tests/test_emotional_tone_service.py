"""emotional_tone_service 단위 테스트"""
import unittest

from services.analysis.emotional_tone_service import (
    map_emotional_tone,
    _score_paragraph,
    _calculate_valence,
    _detect_flow_pattern,
)


class TestMapEmotionalTone(unittest.TestCase):

    def test_empty_content(self):
        result = map_emotional_tone('')
        self.assertEqual(result['arc'], [])
        self.assertEqual(result['score'], 0)

    def test_none_content(self):
        result = map_emotional_tone(None)
        self.assertEqual(result['flow_pattern'], 'none')

    def test_single_paragraph(self):
        result = map_emotional_tone('기쁜 소식이 있습니다. 행복한 결과가 나왔습니다.')
        self.assertGreater(len(result['arc']), 0)
        self.assertIn('dominant_emotion', result['overall'])

    def test_joy_detected(self):
        content = '정말 기쁜 소식입니다. 행복하고 감사한 마음입니다.'
        result = map_emotional_tone(content)
        self.assertIn('joy', result['overall']['distribution'])

    def test_sadness_detected(self):
        content = '슬프고 안타까운 상황입니다. 매우 어려운 시기를 보내고 있습니다.'
        result = map_emotional_tone(content)
        self.assertIn('sadness', result['overall']['distribution'])

    def test_multi_emotion_arc(self):
        content = '매우 슬프고 힘든 시작이었습니다.\n그러나 희망과 기대가 생겼습니다. 기쁜 결과를 달성했습니다.'
        result = map_emotional_tone(content)
        self.assertGreaterEqual(len(result['arc']), 2)

    def test_valence_range(self):
        content = '좋은 성과를 달성했습니다.\n힘든 과정이었지만 성공했습니다.'
        result = map_emotional_tone(content)
        self.assertGreaterEqual(result['overall']['valence'], -1)
        self.assertLessEqual(result['overall']['valence'], 1)

    def test_flow_pattern_detected(self):
        content = '일반적인 내용입니다.\n기쁜 소식이 있습니다.\n더욱 행복한 결과입니다.'
        result = map_emotional_tone(content)
        self.assertIn(result['flow_pattern'],
                      ('rising', 'falling', 'steady', 'volatile', 'peak', 'valley', 'flat'))

    def test_distribution_percentages(self):
        content = '기쁜 소식입니다. 감사합니다.\n걱정되는 부분도 있습니다.'
        result = map_emotional_tone(content)
        dist = result['overall']['distribution']
        if dist:
            total = sum(dist.values())
            self.assertAlmostEqual(total, 100, delta=1)

    def test_score_bounded(self):
        result = map_emotional_tone('테스트 콘텐츠입니다.')
        self.assertGreaterEqual(result['score'], 0)
        self.assertLessEqual(result['score'], 100)

    def test_suggestions_exist(self):
        result = map_emotional_tone('일반적인 콘텐츠입니다.\n특별한 감정이 없는 글입니다.')
        self.assertIsInstance(result['suggestions'], list)
        self.assertGreater(len(result['suggestions']), 0)


class TestScoreParagraph(unittest.TestCase):

    def test_neutral_paragraph(self):
        result = _score_paragraph('일반적인 문단입니다.')
        self.assertIn('neutral', result)

    def test_emotional_paragraph(self):
        result = _score_paragraph('기쁘고 행복한 순간입니다.')
        self.assertIn('joy', result)


class TestCalculateValence(unittest.TestCase):

    def test_positive_valence(self):
        v = _calculate_valence({'joy': 3, 'trust': 2})
        self.assertGreater(v, 0)

    def test_negative_valence(self):
        v = _calculate_valence({'sadness': 3, 'anger': 2})
        self.assertLess(v, 0)

    def test_zero_valence(self):
        v = _calculate_valence({})
        self.assertEqual(v, 0)


class TestDetectFlowPattern(unittest.TestCase):

    def test_single_entry(self):
        arc = [{'valence': 0.5}]
        self.assertEqual(_detect_flow_pattern(arc), 'flat')

    def test_rising_pattern(self):
        arc = [{'valence': -0.5}, {'valence': 0.0}, {'valence': 0.5}]
        self.assertEqual(_detect_flow_pattern(arc), 'rising')


if __name__ == '__main__':
    unittest.main()
