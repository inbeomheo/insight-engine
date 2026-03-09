"""
비디오 투 텍스트 내레이션 서비스 테스트

services/video_to_text_service.py의 narrate_video 및
내부 헬퍼 함수들을 검증합니다.
"""
import unittest

from services.video_to_text_service import (
    NarrationResult,
    NarrationSegment,
    SUPPORTED_STYLES,
    narrate_video,
    _format_timestamp,
    _split_sentences,
    _count_words,
    _transform_descriptive,
    _transform_action,
    _transform_documentary,
    _assign_scene_type,
)


class TestFormatTimestamp(unittest.TestCase):
    """_format_timestamp 함수 테스트."""

    def test_zero(self):
        self.assertEqual(_format_timestamp(0), "00:00")

    def test_seconds_only(self):
        self.assertEqual(_format_timestamp(45), "00:45")

    def test_minutes_and_seconds(self):
        self.assertEqual(_format_timestamp(125), "02:05")


class TestSplitSentences(unittest.TestCase):
    """_split_sentences 함수 테스트."""

    def test_empty(self):
        self.assertEqual(_split_sentences(""), [])

    def test_newline_split(self):
        result = _split_sentences("첫 줄\n두 번째 줄")
        self.assertEqual(len(result), 2)


class TestCountWords(unittest.TestCase):
    """_count_words 함수 테스트."""

    def test_empty(self):
        self.assertEqual(_count_words(""), 0)

    def test_korean_words(self):
        self.assertEqual(_count_words("안녕 하세요 테스트"), 3)

    def test_none(self):
        self.assertEqual(_count_words(None), 0)


class TestTransformFunctions(unittest.TestCase):
    """스타일별 변환 함수 테스트."""

    def test_descriptive_contains_keyword(self):
        result = _transform_descriptive("테스트 문장")
        self.assertIn("설명", result)
        self.assertIn("테스트 문장", result)

    def test_action_contains_prefix(self):
        result = _transform_action("중요한 장면")
        self.assertIn("[액션]", result)
        self.assertIn("중요한 장면", result)

    def test_documentary_contains_narrator(self):
        result = _transform_documentary("역사적 사건")
        self.assertIn("내레이터", result)
        self.assertIn("역사적 사건", result)


class TestAssignSceneType(unittest.TestCase):
    """_assign_scene_type 함수 테스트."""

    def test_first_is_transition(self):
        self.assertEqual(_assign_scene_type(0, 5), "transition")

    def test_last_is_transition(self):
        self.assertEqual(_assign_scene_type(4, 5), "transition")

    def test_multiple_of_three_is_highlight(self):
        # index=3, total=10 → 3 % 3 == 0 → highlight
        self.assertEqual(_assign_scene_type(3, 10), "highlight")

    def test_regular_is_narration(self):
        # index=1, total=5 → narration
        self.assertEqual(_assign_scene_type(1, 5), "narration")


class TestNarrateVideo(unittest.TestCase):
    """narrate_video 함수 테스트."""

    def test_empty_transcript_returns_empty_result(self):
        """빈 자막이면 빈 내레이션을 반환합니다."""
        result = narrate_video("vid1", transcript="")
        self.assertIsInstance(result, NarrationResult)
        self.assertEqual(result.narration, "")
        self.assertEqual(result.segments, [])
        self.assertEqual(result.word_count, 0)

    def test_none_transcript_returns_empty(self):
        """None 자막이면 빈 내레이션을 반환합니다."""
        result = narrate_video("vid1")
        self.assertEqual(result.narration, "")
        self.assertEqual(result.segments, [])

    def test_invalid_style_raises_error(self):
        """지원하지 않는 스타일이면 ValueError가 발생합니다."""
        with self.assertRaises(ValueError) as ctx:
            narrate_video("vid1", transcript="테스트", style="invalid")
        self.assertIn("지원하지 않는 스타일", str(ctx.exception))

    def test_descriptive_style(self):
        """descriptive 스타일이 올바르게 적용됩니다."""
        result = narrate_video("vid1", transcript="파이썬 강의", style="descriptive")
        self.assertEqual(result.style, "descriptive")
        self.assertTrue(len(result.segments) >= 1)
        self.assertIn("설명", result.narration)

    def test_action_style(self):
        """action 스타일이 올바르게 적용됩니다."""
        result = narrate_video("vid1", transcript="중요한 장면", style="action")
        self.assertEqual(result.style, "action")
        self.assertIn("[액션]", result.narration)

    def test_documentary_style(self):
        """documentary 스타일이 올바르게 적용됩니다."""
        result = narrate_video("vid1", transcript="역사적 사건", style="documentary")
        self.assertEqual(result.style, "documentary")
        self.assertIn("내레이터", result.narration)

    def test_word_count_calculated(self):
        """단어 수가 올바르게 계산됩니다."""
        result = narrate_video("vid1", transcript="첫 번째 문장\n두 번째 문장")
        self.assertGreater(result.word_count, 0)

    def test_segments_have_timestamps(self):
        """각 세그먼트에 타임스탬프가 있습니다."""
        import re
        result = narrate_video("vid1", transcript="문장 하나\n문장 둘\n문장 셋")
        for seg in result.segments:
            self.assertRegex(seg.timestamp, r'^\d{2}:\d{2}$')

    def test_segments_have_scene_types(self):
        """각 세그먼트에 장면 타입이 할당됩니다."""
        result = narrate_video("vid1", transcript="문장1\n문장2\n문장3\n문장4")
        valid_types = {"narration", "transition", "highlight"}
        for seg in result.segments:
            self.assertIn(seg.scene_type, valid_types)

    def test_video_id_in_result(self):
        """결과에 video_id가 정확히 포함됩니다."""
        result = narrate_video("my_vid", transcript="테스트")
        self.assertEqual(result.video_id, "my_vid")

    def test_supported_styles_constant(self):
        """SUPPORTED_STYLES 상수가 3개 스타일을 포함합니다."""
        self.assertEqual(len(SUPPORTED_STYLES), 3)
        self.assertIn("descriptive", SUPPORTED_STYLES)
        self.assertIn("action", SUPPORTED_STYLES)
        self.assertIn("documentary", SUPPORTED_STYLES)

    def test_multiple_sentences_generate_segments(self):
        """여러 문장이 각각 세그먼트로 생성됩니다."""
        transcript = "첫 번째\n두 번째\n세 번째\n네 번째\n다섯 번째"
        result = narrate_video("vid1", transcript=transcript)
        self.assertEqual(len(result.segments), 5)


if __name__ == "__main__":
    unittest.main()
