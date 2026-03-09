"""emotion_curve_editor_service 단위 테스트"""
import unittest

from services.emotion_curve_editor_service import (
    edit_emotion_curve,
    EmotionCurve,
    CurvePoint,
    SUPPORTED_EMOTIONS,
    _validate_segment,
    _calculate_smoothness,
    _get_transition_label,
)


class TestEditEmotionCurve(unittest.TestCase):
    """edit_emotion_curve 함수 테스트"""

    def test_empty_segments(self):
        """빈 세그먼트 — 빈 곡선"""
        result = edit_emotion_curve([])
        self.assertEqual(result.points, [])
        self.assertEqual(result.transitions, [])
        self.assertEqual(result.smoothness, 1.0)

    def test_single_segment(self):
        """단일 세그먼트 — 1개 포인트, 전환 없음"""
        result = edit_emotion_curve([{'emotion': 'joy', 'intensity': 0.8}])
        self.assertEqual(len(result.points), 1)
        self.assertEqual(result.points[0].emotion, 'joy')
        self.assertEqual(result.points[0].intensity, 0.8)
        self.assertEqual(result.transitions, [])

    def test_multiple_segments(self):
        """여러 세그먼트 — 전환 포함"""
        segments = [
            {'emotion': 'neutral', 'intensity': 0.3},
            {'emotion': 'joy', 'intensity': 0.8},
            {'emotion': 'sadness', 'intensity': 0.6},
        ]
        result = edit_emotion_curve(segments)
        self.assertEqual(len(result.points), 3)
        self.assertEqual(len(result.transitions), 2)

    def test_same_emotion_transition(self):
        """같은 감정 연속 — '유지' 전환"""
        segments = [
            {'emotion': 'joy', 'intensity': 0.5},
            {'emotion': 'joy', 'intensity': 0.8},
        ]
        result = edit_emotion_curve(segments)
        self.assertTrue('유지' in result.transitions[0])

    def test_invalid_emotion(self):
        """지원하지 않는 감정 → ValueError"""
        with self.assertRaises(ValueError):
            edit_emotion_curve([{'emotion': 'rage', 'intensity': 0.5}])

    def test_invalid_intensity_range(self):
        """강도 범위 초과 → ValueError"""
        with self.assertRaises(ValueError):
            edit_emotion_curve([{'emotion': 'joy', 'intensity': 1.5}])

    def test_negative_intensity(self):
        """음수 강도 → ValueError"""
        with self.assertRaises(ValueError):
            edit_emotion_curve([{'emotion': 'joy', 'intensity': -0.1}])

    def test_missing_emotion_key(self):
        """emotion 키 누락 → ValueError"""
        with self.assertRaises(ValueError):
            edit_emotion_curve([{'intensity': 0.5}])

    def test_default_intensity(self):
        """intensity 키 누락 — 기본값 0.5"""
        result = edit_emotion_curve([{'emotion': 'neutral'}])
        self.assertEqual(result.points[0].intensity, 0.5)

    def test_position_sequential(self):
        """포인트 position이 순차적"""
        segments = [
            {'emotion': 'joy', 'intensity': 0.5},
            {'emotion': 'trust', 'intensity': 0.7},
            {'emotion': 'surprise', 'intensity': 0.9},
        ]
        result = edit_emotion_curve(segments)
        for i, point in enumerate(result.points):
            self.assertEqual(point.position, i)

    def test_smoothness_range(self):
        """매끄러움 0~1 범위"""
        segments = [
            {'emotion': 'joy', 'intensity': 0.2},
            {'emotion': 'anger', 'intensity': 0.9},
            {'emotion': 'sadness', 'intensity': 0.1},
        ]
        result = edit_emotion_curve(segments)
        self.assertGreaterEqual(result.smoothness, 0.0)
        self.assertLessEqual(result.smoothness, 1.0)

    def test_smooth_curve(self):
        """같은 감정 같은 강도 → 매끄러움 1.0"""
        segments = [
            {'emotion': 'neutral', 'intensity': 0.5},
            {'emotion': 'neutral', 'intensity': 0.5},
            {'emotion': 'neutral', 'intensity': 0.5},
        ]
        result = edit_emotion_curve(segments)
        self.assertEqual(result.smoothness, 1.0)

    def test_result_is_dataclass(self):
        """반환 타입 확인"""
        result = edit_emotion_curve([{'emotion': 'joy', 'intensity': 0.5}])
        self.assertIsInstance(result, EmotionCurve)
        self.assertIsInstance(result.points[0], CurvePoint)


class TestHelperFunctions(unittest.TestCase):
    """헬퍼 함수 테스트"""

    def test_validate_segment_valid(self):
        """유효한 세그먼트"""
        self.assertTrue(_validate_segment({'emotion': 'joy', 'intensity': 0.5}))

    def test_validate_segment_invalid_type(self):
        """dict가 아닌 입력"""
        self.assertFalse(_validate_segment('invalid'))

    def test_validate_segment_missing_emotion(self):
        """emotion 키 없음"""
        self.assertFalse(_validate_segment({'intensity': 0.5}))

    def test_validate_segment_bad_emotion(self):
        """지원하지 않는 감정"""
        self.assertFalse(_validate_segment({'emotion': 'rage', 'intensity': 0.5}))

    def test_get_transition_label_known(self):
        """알려진 전환"""
        label = _get_transition_label('neutral', 'joy')
        self.assertIn('기쁨', label)

    def test_get_transition_label_unknown(self):
        """알려지지 않은 전환 — 기본 템플릿"""
        label = _get_transition_label('joy', 'fear')
        self.assertIn('전환', label)

    def test_calculate_smoothness_single_point(self):
        """1개 포인트 — 매끄러움 1.0"""
        points = [CurvePoint(0, 'joy', 0.5)]
        self.assertEqual(_calculate_smoothness(points), 1.0)


if __name__ == '__main__':
    unittest.main()
