"""
타임코드 포함 영상 Q&A 강화 서비스 테스트

services/video_qa_enhanced_service.py의 qa_with_timecodes 및
내부 헬퍼 함수들을 검증합니다.
"""
import unittest

from services.video_qa_enhanced_service import (
    QAResponse,
    TimecodeRef,
    qa_with_timecodes,
    _format_timestamp,
    _split_sentences,
    _extract_keywords,
    _calculate_sentence_relevance,
    _build_answer,
)


class TestFormatTimestamp(unittest.TestCase):
    """_format_timestamp 함수 테스트."""

    def test_zero(self):
        self.assertEqual(_format_timestamp(0), "00:00")

    def test_complex(self):
        self.assertEqual(_format_timestamp(185), "03:05")


class TestSplitSentences(unittest.TestCase):
    """_split_sentences 함수 테스트."""

    def test_empty(self):
        self.assertEqual(_split_sentences(""), [])

    def test_normal(self):
        result = _split_sentences("문장1.문장2.문장3")
        self.assertEqual(len(result), 3)


class TestExtractKeywords(unittest.TestCase):
    """_extract_keywords 함수 테스트."""

    def test_removes_stopwords(self):
        """불용어가 제거됩니다."""
        keywords = _extract_keywords("이것 파이썬 어떻게 사용하는")
        self.assertIn("파이썬", keywords)
        self.assertIn("사용하는", keywords)
        # '이것', '어떻게'는 불용어로 제거됨
        self.assertNotIn("이것", keywords)
        self.assertNotIn("어떻게", keywords)

    def test_removes_short_words(self):
        """1글자 단어가 제거됩니다."""
        keywords = _extract_keywords("a 파이썬 b 프로그래밍")
        for kw in keywords:
            self.assertGreaterEqual(len(kw), 2)

    def test_empty_question(self):
        """빈 질문에서 빈 키워드 리스트를 반환합니다."""
        self.assertEqual(_extract_keywords(""), [])


class TestCalculateSentenceRelevance(unittest.TestCase):
    """_calculate_sentence_relevance 함수 테스트."""

    def test_no_keywords(self):
        self.assertEqual(_calculate_sentence_relevance("문장", []), 0.0)

    def test_full_match(self):
        score = _calculate_sentence_relevance("파이썬 튜토리얼", ["파이썬", "튜토리얼"])
        self.assertEqual(score, 1.0)

    def test_no_match(self):
        score = _calculate_sentence_relevance("날씨가 좋다", ["파이썬"])
        self.assertEqual(score, 0.0)


class TestBuildAnswer(unittest.TestCase):
    """_build_answer 함수 테스트."""

    def test_no_matches(self):
        """매칭 없으면 기본 메시지를 반환합니다."""
        answer = _build_answer([], "질문")
        self.assertIn("찾을 수 없습니다", answer)

    def test_with_matches(self):
        """매칭 문장이 답변에 포함됩니다."""
        answer = _build_answer(["파이썬은 쉽다", "파이썬은 강력하다"], "파이썬")
        self.assertIn("파이썬은 쉽다", answer)
        self.assertIn("관련 내용을 찾았습니다", answer)

    def test_max_three_sentences(self):
        """답변에 최대 3개 문장만 포함됩니다."""
        sentences = ["문장1", "문장2", "문장3", "문장4", "문장5"]
        answer = _build_answer(sentences, "질문")
        self.assertIn("문장1", answer)
        self.assertIn("문장3", answer)
        self.assertNotIn("문장4", answer)


class TestQaWithTimecodes(unittest.TestCase):
    """qa_with_timecodes 함수 테스트."""

    def test_empty_question_returns_default(self):
        """빈 질문이면 안내 메시지를 반환합니다."""
        result = qa_with_timecodes("vid1", "", transcript="자막")
        self.assertIsInstance(result, QAResponse)
        self.assertIn("질문을 입력", result.answer)
        self.assertEqual(result.confidence, 0.0)

    def test_empty_transcript_returns_default(self):
        """빈 자막이면 답변 불가 메시지를 반환합니다."""
        result = qa_with_timecodes("vid1", "파이썬이 뭔가요?")
        self.assertIn("자막이 없어", result.answer)
        self.assertEqual(result.timecodes, [])

    def test_matching_question_returns_timecodes(self):
        """매칭되는 질문에 타임코드가 포함됩니다."""
        transcript = "파이썬은 프로그래밍 언어입니다\n자바는 다른 언어입니다\n파이썬 설치 방법"
        result = qa_with_timecodes("vid1", "파이썬 설치", transcript=transcript)
        self.assertTrue(len(result.timecodes) >= 1)
        self.assertGreater(result.confidence, 0.0)

    def test_result_type(self):
        """반환값이 QAResponse 인스턴스입니다."""
        result = qa_with_timecodes("vid1", "테스트", transcript="테스트 내용")
        self.assertIsInstance(result, QAResponse)

    def test_question_preserved(self):
        """원본 질문이 결과에 보존됩니다."""
        result = qa_with_timecodes("vid1", "파이썬이 뭔가요?", transcript="파이썬 내용")
        self.assertEqual(result.question, "파이썬이 뭔가요?")

    def test_timecode_format(self):
        """타임코드가 MM:SS 형식입니다."""
        import re
        transcript = "파이썬 기초 강의"
        result = qa_with_timecodes("vid1", "파이썬", transcript=transcript)
        for tc in result.timecodes:
            self.assertRegex(tc.timestamp, r'^\d{2}:\d{2}$')

    def test_timecode_has_relevance(self):
        """타임코드에 관련도 점수가 있습니다."""
        transcript = "파이썬 프로그래밍"
        result = qa_with_timecodes("vid1", "파이썬", transcript=transcript)
        for tc in result.timecodes:
            self.assertIsInstance(tc.relevance, float)
            self.assertGreaterEqual(tc.relevance, 0.0)
            self.assertLessEqual(tc.relevance, 1.0)

    def test_confidence_range(self):
        """신뢰도가 0.0 ~ 1.0 범위 내입니다."""
        transcript = "파이썬 기초\n파이썬 고급\n자바 입문"
        result = qa_with_timecodes("vid1", "파이썬 기초", transcript=transcript)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)

    def test_no_match_low_confidence(self):
        """매칭 없으면 신뢰도가 0입니다."""
        transcript = "오늘 날씨가 좋습니다\n내일도 맑겠습니다"
        result = qa_with_timecodes("vid1", "파이썬 프로그래밍", transcript=transcript)
        self.assertEqual(result.confidence, 0.0)

    def test_max_five_timecodes(self):
        """타임코드는 최대 5개까지 반환됩니다."""
        # 많은 매칭 문장 생성
        lines = [f"파이썬 강의 {i}편" for i in range(20)]
        transcript = "\n".join(lines)
        result = qa_with_timecodes("vid1", "파이썬 강의", transcript=transcript)
        self.assertLessEqual(len(result.timecodes), 5)

    def test_timecodes_sorted_by_relevance(self):
        """타임코드가 관련도 내림차순으로 정렬됩니다."""
        transcript = "파이썬 입문\n자바 프로그래밍\n파이썬 자바 고급 비교"
        result = qa_with_timecodes("vid1", "파이썬 자바", transcript=transcript)
        if len(result.timecodes) >= 2:
            for i in range(len(result.timecodes) - 1):
                self.assertGreaterEqual(
                    result.timecodes[i].relevance,
                    result.timecodes[i + 1].relevance,
                )


if __name__ == "__main__":
    unittest.main()
