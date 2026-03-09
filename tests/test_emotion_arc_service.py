"""
emotion_arc_service 단위 테스트
"""
import unittest
from services.emotion_arc_service import (
    map_emotion_arc,
    EmotionArc,
    EmotionPoint,
    _detect_emotion,
    _split_into_segments,
    _determine_arc_type,
    _determine_dominant_emotion,
    _truncate_snippet,
    VALID_EMOTIONS,
)


class TestDetectEmotion(unittest.TestCase):
    """감정 탐지 테스트"""

    def test_joy_korean(self):
        emotion, intensity = _detect_emotion("정말 기쁘고 행복한 날이에요")
        self.assertEqual(emotion, "joy")
        self.assertGreater(intensity, 0.5)

    def test_joy_english(self):
        emotion, intensity = _detect_emotion("I am so happy and great")
        self.assertEqual(emotion, "joy")

    def test_sadness(self):
        emotion, intensity = _detect_emotion("너무 슬프고 외로운 밤")
        self.assertEqual(emotion, "sadness")

    def test_anger(self):
        emotion, intensity = _detect_emotion("정말 화나고 짜증나는 상황")
        self.assertEqual(emotion, "anger")

    def test_fear(self):
        emotion, intensity = _detect_emotion("무섭고 불안한 느낌이 들어요")
        self.assertEqual(emotion, "fear")

    def test_surprise(self):
        emotion, intensity = _detect_emotion("놀라운 반전이 있었다")
        self.assertEqual(emotion, "surprise")

    def test_neutral(self):
        emotion, intensity = _detect_emotion("오늘 날씨가 맑습니다")
        self.assertEqual(emotion, "neutral")

    def test_intensity_range(self):
        """강도는 0~1 범위"""
        for text in ["기쁘다", "슬프다", "화난다", "무섭다", "놀랍다", "평범한 텍스트"]:
            _, intensity = _detect_emotion(text)
            self.assertGreaterEqual(intensity, 0.0)
            self.assertLessEqual(intensity, 1.0)

    def test_multiple_keywords_increase_intensity(self):
        """여러 키워드가 강도를 높임"""
        _, low = _detect_emotion("기쁘다")
        _, high = _detect_emotion("기쁘고 행복하고 즐겁고 좋고 최고")
        self.assertGreaterEqual(high, low)


class TestSplitIntoSegments(unittest.TestCase):
    """구간 분할 테스트"""

    def test_timestamped_transcript(self):
        transcript = "[00:00] 첫 번째 [01:00] 두 번째 [02:00] 세 번째"
        segments = _split_into_segments(transcript)
        self.assertEqual(len(segments), 3)
        self.assertEqual(segments[0][0], "00:00")
        self.assertIn("첫 번째", segments[0][1])

    def test_plain_text_segments(self):
        """타임스탬프 없는 텍스트는 균등 분할"""
        lines = "\n".join([f"라인 {i}" for i in range(20)])
        segments = _split_into_segments(lines, segment_count=5)
        self.assertEqual(len(segments), 5)
        # 가상 타임스탬프 형식 확인
        self.assertRegex(segments[0][0], r'\d{2}:\d{2}')

    def test_empty_transcript(self):
        segments = _split_into_segments("")
        self.assertEqual(len(segments), 0)


class TestDetermineArcType(unittest.TestCase):
    """곡선 유형 결정 테스트"""

    def test_rising(self):
        points = [
            EmotionPoint("00:00", "neutral", 0.2, ""),
            EmotionPoint("01:00", "joy", 0.4, ""),
            EmotionPoint("02:00", "joy", 0.6, ""),
            EmotionPoint("03:00", "joy", 0.8, ""),
            EmotionPoint("04:00", "joy", 1.0, ""),
        ]
        self.assertEqual(_determine_arc_type(points), "rising")

    def test_falling(self):
        points = [
            EmotionPoint("00:00", "joy", 1.0, ""),
            EmotionPoint("01:00", "joy", 0.8, ""),
            EmotionPoint("02:00", "neutral", 0.5, ""),
            EmotionPoint("03:00", "sadness", 0.3, ""),
            EmotionPoint("04:00", "sadness", 0.1, ""),
        ]
        self.assertEqual(_determine_arc_type(points), "falling")

    def test_stable(self):
        points = [
            EmotionPoint("00:00", "neutral", 0.5, ""),
            EmotionPoint("01:00", "neutral", 0.5, ""),
            EmotionPoint("02:00", "neutral", 0.5, ""),
        ]
        self.assertEqual(_determine_arc_type(points), "stable")

    def test_single_point(self):
        points = [EmotionPoint("00:00", "joy", 0.5, "")]
        self.assertEqual(_determine_arc_type(points), "stable")

    def test_wave(self):
        points = [
            EmotionPoint("00:00", "joy", 0.3, ""),
            EmotionPoint("01:00", "joy", 0.8, ""),
            EmotionPoint("02:00", "sadness", 0.3, ""),
            EmotionPoint("03:00", "joy", 0.8, ""),
            EmotionPoint("04:00", "sadness", 0.3, ""),
        ]
        self.assertEqual(_determine_arc_type(points), "wave")


class TestDetermineDominantEmotion(unittest.TestCase):
    """주요 감정 결정 테스트"""

    def test_dominant_joy(self):
        points = [
            EmotionPoint("00:00", "joy", 0.5, ""),
            EmotionPoint("01:00", "joy", 0.6, ""),
            EmotionPoint("02:00", "sadness", 0.4, ""),
        ]
        self.assertEqual(_determine_dominant_emotion(points), "joy")

    def test_empty_points(self):
        self.assertEqual(_determine_dominant_emotion([]), "neutral")


class TestTruncateSnippet(unittest.TestCase):
    """텍스트 스니펫 자르기 테스트"""

    def test_short_text(self):
        self.assertEqual(_truncate_snippet("짧은 텍스트"), "짧은 텍스트")

    def test_long_text(self):
        long_text = "가" * 150
        result = _truncate_snippet(long_text, 100)
        self.assertEqual(len(result), 100)
        self.assertTrue(result.endswith("..."))


class TestMapEmotionArc(unittest.TestCase):
    """map_emotion_arc 메인 함수 테스트"""

    def test_basic_arc(self):
        transcript = "[00:00] 오늘 정말 기쁘고 행복합니다 [01:00] 하지만 슬프고 외로운 일도 있었어요 [02:00] 결국 좋은 하루였습니다"
        result = map_emotion_arc("vid1", transcript)
        self.assertIsInstance(result, EmotionArc)
        self.assertEqual(result.video_id, "vid1")
        self.assertEqual(len(result.points), 3)
        self.assertIn(result.dominant_emotion, VALID_EMOTIONS)
        self.assertIn(result.arc_type, {"rising", "falling", "wave", "stable"})

    def test_empty_video_id(self):
        result = map_emotion_arc("", "some text")
        self.assertEqual(result.video_id, "")
        self.assertEqual(result.points, [])
        self.assertEqual(result.dominant_emotion, "neutral")
        self.assertEqual(result.arc_type, "stable")

    def test_empty_transcript(self):
        result = map_emotion_arc("vid1", "")
        self.assertEqual(result.points, [])
        self.assertEqual(result.dominant_emotion, "neutral")

    def test_none_transcript(self):
        result = map_emotion_arc("vid1")
        self.assertEqual(result.points, [])

    def test_plain_text_transcript(self):
        """타임스탬프 없는 자막도 처리"""
        text = "\n".join([
            "안녕하세요 오늘 기쁜 소식이 있습니다",
            "정말 행복한 일이 일어났어요",
            "그런데 슬픈 이야기도 있네요",
        ])
        result = map_emotion_arc("vid2", text)
        self.assertGreater(len(result.points), 0)

    def test_video_id_stripped(self):
        result = map_emotion_arc("  vid3  ", "[00:00] test")
        self.assertEqual(result.video_id, "vid3")

    def test_all_neutral(self):
        """감정 키워드 없는 텍스트"""
        transcript = "[00:00] 오늘 날씨가 맑다 [01:00] 내일도 맑을 예정이다"
        result = map_emotion_arc("vid4", transcript)
        self.assertEqual(result.dominant_emotion, "neutral")

    def test_points_have_snippets(self):
        """각 포인트에 텍스트 스니펫 포함"""
        transcript = "[00:00] 기쁜 소식입니다 [01:00] 슬픈 이야기네요"
        result = map_emotion_arc("vid5", transcript)
        for point in result.points:
            self.assertIsInstance(point.text_snippet, str)
            self.assertGreater(len(point.text_snippet), 0)

    def test_intensity_within_range(self):
        """모든 포인트의 강도가 0~1 범위"""
        transcript = "[00:00] 기쁘고 행복해요 [01:00] 화나고 짜증나요 [02:00] 무섭고 불안해요"
        result = map_emotion_arc("vid6", transcript)
        for point in result.points:
            self.assertGreaterEqual(point.intensity, 0.0)
            self.assertLessEqual(point.intensity, 1.0)


if __name__ == '__main__':
    unittest.main()
