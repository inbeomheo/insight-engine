"""프레임 접근성 서비스 테스트"""

import unittest

from services.frame_accessibility_service import (
    FrameA11y,
    generate_description,
    assess_frame_complexity,
    create_audio_description,
    validate_accessibility,
)


class TestGenerateDescription(unittest.TestCase):
    """generate_description 함수 테스트"""

    def test_짧은_콘텐츠(self):
        desc = generate_description("로고 화면")
        self.assertIn("로고 화면", desc)

    def test_긴_콘텐츠(self):
        desc = generate_description("머신러닝 모델 학습 과정에서 손실 함수의 변화를 보여주는 그래프")
        self.assertIn("프레임", desc)

    def test_컨텍스트_포함(self):
        desc = generate_description("그래프", context="데이터 분석 챕터")
        self.assertIn("맥락", desc)

    def test_빈_콘텐츠(self):
        desc = generate_description("")
        self.assertIn("없습니다", desc)


class TestAssessFrameComplexity(unittest.TestCase):
    """assess_frame_complexity 함수 테스트"""

    def test_단순_프레임(self):
        result = assess_frame_complexity("로고")
        self.assertEqual(result, "simple")

    def test_보통_프레임(self):
        result = assess_frame_complexity("차트에 숫자 123이 표시됨")
        self.assertEqual(result, "moderate")

    def test_복잡_프레임(self):
        # 20+ 단어 + 숫자 + 특수문자
        content = " ".join(["단어"] * 25) + " 123 !@#"
        result = assess_frame_complexity(content)
        self.assertEqual(result, "complex")

    def test_빈_콘텐츠(self):
        result = assess_frame_complexity("")
        self.assertEqual(result, "simple")


class TestCreateAudioDescription(unittest.TestCase):
    """create_audio_description 함수 테스트"""

    def test_음성_해설_생성(self):
        frames = [
            FrameA11y(frame_id="1", timestamp="00:10", alt_description="로고 등장", complexity="simple"),
            FrameA11y(frame_id="2", timestamp="01:30", alt_description="그래프 표시", complexity="complex"),
        ]
        script = create_audio_description(frames)
        self.assertIn("[00:10]", script)
        self.assertIn("[01:30]", script)
        self.assertIn("로고 등장", script)
        self.assertIn("복잡한 장면", script)

    def test_빈_프레임(self):
        script = create_audio_description([])
        self.assertIn("없습니다", script)

    def test_설명_없는_프레임(self):
        frames = [FrameA11y(frame_id="1", timestamp="00:05")]
        script = create_audio_description(frames)
        self.assertIn("설명 없음", script)


class TestValidateAccessibility(unittest.TestCase):
    """validate_accessibility 함수 테스트"""

    def test_완벽한_접근성(self):
        frames = [
            FrameA11y(
                frame_id="1", has_captions=True,
                alt_description="설명", audio_description="해설",
                complexity="simple",
            ),
        ]
        result = validate_accessibility(frames)
        self.assertEqual(result["caption_coverage"], 1.0)
        self.assertEqual(result["description_coverage"], 1.0)
        self.assertEqual(len(result["issues"]), 0)

    def test_캡션_누락(self):
        frames = [
            FrameA11y(frame_id="1", has_captions=False, alt_description="설명"),
            FrameA11y(frame_id="2", has_captions=True, alt_description="설명"),
        ]
        result = validate_accessibility(frames)
        self.assertAlmostEqual(result["caption_coverage"], 0.5)
        self.assertGreater(len(result["issues"]), 0)

    def test_복잡_프레임_음성해설_누락(self):
        frames = [
            FrameA11y(
                frame_id="1", has_captions=True,
                alt_description="설명", complexity="complex",
                audio_description="",
            ),
        ]
        result = validate_accessibility(frames)
        has_complex_issue = any("복잡한" in issue for issue in result["issues"])
        self.assertTrue(has_complex_issue)

    def test_빈_프레임_리스트(self):
        result = validate_accessibility([])
        self.assertEqual(result["total_frames"], 0)
        self.assertEqual(result["overall_score"], 0.0)

    def test_종합_점수_범위(self):
        frames = [
            FrameA11y(frame_id="1", has_captions=True, alt_description="설명"),
        ]
        result = validate_accessibility(frames)
        self.assertGreaterEqual(result["overall_score"], 0.0)
        self.assertLessEqual(result["overall_score"], 1.0)


if __name__ == "__main__":
    unittest.main()
