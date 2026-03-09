"""
멀티모달 클립 추출 서비스 테스트

services/multimodal_clip_service.py의 extract_by_prompt 및
내부 헬퍼 함수들을 검증합니다.
"""
import unittest

from services.multimodal_clip_service import (
    ClipResult,
    extract_by_prompt,
    _format_timestamp,
    _split_sentences,
    _calculate_relevance,
)


class TestFormatTimestamp(unittest.TestCase):
    """_format_timestamp 함수 테스트."""

    def test_zero_seconds(self):
        """0초는 00:00으로 변환됩니다."""
        self.assertEqual(_format_timestamp(0), "00:00")

    def test_under_one_minute(self):
        """60초 미만은 00:SS 형식입니다."""
        self.assertEqual(_format_timestamp(30), "00:30")

    def test_exact_minute(self):
        """정확히 N분은 NN:00 형식입니다."""
        self.assertEqual(_format_timestamp(120), "02:00")

    def test_mixed_minutes_seconds(self):
        """분+초 조합이 올바르게 변환됩니다."""
        self.assertEqual(_format_timestamp(95), "01:35")


class TestSplitSentences(unittest.TestCase):
    """_split_sentences 함수 테스트."""

    def test_empty_string(self):
        """빈 문자열은 빈 리스트를 반환합니다."""
        self.assertEqual(_split_sentences(""), [])

    def test_none_input(self):
        """None 입력은 빈 리스트를 반환합니다."""
        self.assertEqual(_split_sentences(None), [])

    def test_whitespace_only(self):
        """공백만 있는 문자열은 빈 리스트를 반환합니다."""
        self.assertEqual(_split_sentences("   "), [])

    def test_single_sentence(self):
        """단일 문장이 올바르게 분리됩니다."""
        result = _split_sentences("안녕하세요")
        self.assertEqual(result, ["안녕하세요"])

    def test_period_split(self):
        """마침표로 문장이 분리됩니다."""
        result = _split_sentences("첫 번째.두 번째.세 번째")
        self.assertEqual(len(result), 3)

    def test_newline_split(self):
        """줄바꿈으로 문장이 분리됩니다."""
        result = _split_sentences("첫 줄\n두 번째 줄\n세 번째 줄")
        self.assertEqual(len(result), 3)


class TestCalculateRelevance(unittest.TestCase):
    """_calculate_relevance 함수 테스트."""

    def test_no_keywords(self):
        """키워드가 없으면 0.0을 반환합니다."""
        self.assertEqual(_calculate_relevance("테스트 문장", []), 0.0)

    def test_full_match(self):
        """모든 키워드가 매칭되면 1.0을 반환합니다."""
        score = _calculate_relevance("파이썬 프로그래밍 튜토리얼", ["파이썬", "튜토리얼"])
        self.assertEqual(score, 1.0)

    def test_partial_match(self):
        """일부 키워드만 매칭되면 비율 점수를 반환합니다."""
        score = _calculate_relevance("파이썬 입문", ["파이썬", "자바"])
        self.assertEqual(score, 0.5)

    def test_no_match(self):
        """매칭되는 키워드가 없으면 0.0을 반환합니다."""
        score = _calculate_relevance("오늘 날씨가 좋다", ["파이썬", "자바"])
        self.assertEqual(score, 0.0)

    def test_case_insensitive(self):
        """대소문자 구분 없이 매칭합니다."""
        score = _calculate_relevance("Python Tutorial", ["python", "tutorial"])
        self.assertEqual(score, 1.0)


class TestExtractByPrompt(unittest.TestCase):
    """extract_by_prompt 함수 테스트."""

    def test_empty_transcript_returns_empty(self):
        """빈 자막이면 빈 리스트를 반환합니다."""
        result = extract_by_prompt("vid1", "파이썬", transcript="")
        self.assertEqual(result, [])

    def test_none_transcript_returns_empty(self):
        """None 자막이면 빈 리스트를 반환합니다."""
        result = extract_by_prompt("vid1", "파이썬")
        self.assertEqual(result, [])

    def test_empty_prompt_returns_empty(self):
        """빈 프롬프트이면 빈 리스트를 반환합니다."""
        result = extract_by_prompt("vid1", "", transcript="파이썬 튜토리얼")
        self.assertEqual(result, [])

    def test_matching_clips_returned(self):
        """키워드 매칭되는 문장에서 클립이 추출됩니다."""
        transcript = "파이썬 기초 강의입니다\n자바 프로그래밍을 배웁니다\n파이썬 고급 기술"
        result = extract_by_prompt("vid1", "파이썬", transcript=transcript)
        self.assertTrue(len(result) >= 1)
        for clip in result:
            self.assertIn("파이썬", clip.matched_text)

    def test_result_type_is_clip_result(self):
        """반환값이 ClipResult 인스턴스입니다."""
        transcript = "파이썬 튜토리얼"
        result = extract_by_prompt("vid1", "파이썬", transcript=transcript)
        self.assertTrue(all(isinstance(c, ClipResult) for c in result))

    def test_results_sorted_by_relevance_desc(self):
        """결과가 관련도 내림차순으로 정렬됩니다."""
        transcript = "파이썬 입문\n자바 프로그래밍\n파이썬 자바 고급"
        result = extract_by_prompt("vid1", "파이썬 자바", transcript=transcript)
        if len(result) >= 2:
            for i in range(len(result) - 1):
                self.assertGreaterEqual(
                    result[i].relevance_score,
                    result[i + 1].relevance_score,
                )

    def test_low_relevance_filtered(self):
        """관련도 0.3 미만인 결과는 제외됩니다."""
        # 4개 키워드 중 1개만 매칭 → 0.25 → 필터링
        transcript = "파이썬 입문 강좌"
        result = extract_by_prompt(
            "vid1", "파이썬 자바 루비 고랭", transcript=transcript
        )
        for clip in result:
            self.assertGreaterEqual(clip.relevance_score, 0.3)

    def test_video_id_propagated(self):
        """video_id가 결과에 정확히 전달됩니다."""
        transcript = "파이썬 튜토리얼"
        result = extract_by_prompt("my_video", "파이썬", transcript=transcript)
        for clip in result:
            self.assertEqual(clip.video_id, "my_video")

    def test_clip_id_unique(self):
        """각 클립의 clip_id가 고유합니다."""
        transcript = "파이썬 기초\n파이썬 중급\n파이썬 고급"
        result = extract_by_prompt("vid1", "파이썬", transcript=transcript)
        ids = [c.clip_id for c in result]
        self.assertEqual(len(ids), len(set(ids)))

    def test_timestamp_format(self):
        """타임스탬프가 MM:SS 형식입니다."""
        import re
        transcript = "파이썬 튜토리얼"
        result = extract_by_prompt("vid1", "파이썬", transcript=transcript)
        for clip in result:
            self.assertRegex(clip.start_time, r'^\d{2}:\d{2}$')
            self.assertRegex(clip.end_time, r'^\d{2}:\d{2}$')

    def test_no_match_returns_empty(self):
        """매칭되는 키워드가 없으면 빈 리스트를 반환합니다."""
        transcript = "오늘 날씨가 좋습니다\n내일도 맑겠습니다"
        result = extract_by_prompt("vid1", "파이썬 자바", transcript=transcript)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
