"""handsfree_capture_service 단위 테스트"""
import unittest

from services.content.handsfree_capture_service import (
    capture_speech,
    merge_captures,
    CapturedText,
    _remove_fillers,
    _remove_repeated_words,
    _normalize_whitespace,
    _ensure_sentence_ending,
    _split_sentences,
    _clean_standalone_fillers,
)


class TestRemoveFillers(unittest.TestCase):
    """필러 제거 함수 테스트"""

    def test_removes_korean_fillers(self):
        """한국어 필러(음, 그, 어) 제거"""
        result = _remove_fillers("음 오늘 어 날씨가 그 좋습니다")
        self.assertNotIn("음 ", result)
        self.assertIn("날씨가", result)

    def test_preserves_normal_text(self):
        """일반 텍스트 보존"""
        text = "오늘 날씨가 좋습니다"
        result = _remove_fillers(text)
        self.assertIn("오늘", result)
        self.assertIn("좋습니다", result)


class TestRemoveRepeatedWords(unittest.TestCase):
    """반복 단어 제거 테스트"""

    def test_removes_duplicates(self):
        """연속 반복 단어 제거"""
        result = _remove_repeated_words("정말 정말 좋아요")
        self.assertEqual(result, "정말 좋아요")

    def test_removes_triple_repeat(self):
        """3회 반복도 1개로"""
        result = _remove_repeated_words("네 네 네 알겠습니다")
        self.assertEqual(result, "네 알겠습니다")

    def test_preserves_non_repeated(self):
        """반복 아닌 텍스트 보존"""
        text = "좋은 아침입니다"
        result = _remove_repeated_words(text)
        self.assertEqual(result, text)


class TestNormalizeWhitespace(unittest.TestCase):
    """공백 정리 테스트"""

    def test_multiple_spaces(self):
        """다중 공백을 단일로"""
        result = _normalize_whitespace("hello   world")
        self.assertEqual(result, "hello world")

    def test_strips_edges(self):
        """양끝 공백 제거"""
        result = _normalize_whitespace("  hello  ")
        self.assertEqual(result, "hello")

    def test_empty_string(self):
        result = _normalize_whitespace("")
        self.assertEqual(result, "")


class TestEnsureSentenceEnding(unittest.TestCase):
    """문장 끝 마침표 추가 테스트"""

    def test_adds_period(self):
        result = _ensure_sentence_ending("좋습니다")
        self.assertEqual(result, "좋습니다.")

    def test_keeps_existing_period(self):
        result = _ensure_sentence_ending("좋습니다.")
        self.assertEqual(result, "좋습니다.")

    def test_keeps_question_mark(self):
        result = _ensure_sentence_ending("좋습니까?")
        self.assertEqual(result, "좋습니까?")

    def test_keeps_exclamation(self):
        result = _ensure_sentence_ending("좋아요!")
        self.assertEqual(result, "좋아요!")

    def test_empty_string(self):
        result = _ensure_sentence_ending("")
        self.assertEqual(result, "")


class TestSplitSentences(unittest.TestCase):
    """문장 분리 테스트"""

    def test_splits_by_period(self):
        result = _split_sentences("첫 번째. 두 번째. 세 번째.")
        self.assertEqual(len(result), 3)

    def test_splits_by_question(self):
        result = _split_sentences("맞습니까? 그렇습니다.")
        self.assertEqual(len(result), 2)

    def test_empty_string(self):
        result = _split_sentences("")
        self.assertEqual(result, [])

    def test_single_sentence(self):
        result = _split_sentences("하나의 문장입니다.")
        self.assertEqual(len(result), 1)


class TestCleanStandaloneFillers(unittest.TestCase):
    """독립 필러 제거 테스트"""

    def test_removes_leading_filler(self):
        """문장 시작 필러 제거"""
        result = _clean_standalone_fillers("음 오늘 날씨가 좋습니다")
        self.assertTrue(result.startswith("오늘"))

    def test_preserves_content(self):
        """내용 보존"""
        result = _clean_standalone_fillers("프로젝트를 시작합니다")
        self.assertEqual(result, "프로젝트를 시작합니다")


class TestCaptureSpeech(unittest.TestCase):
    """capture_speech 함수 테스트"""

    def test_empty_input(self):
        """빈 입력 → 빈 CapturedText"""
        result = capture_speech("")
        self.assertEqual(result.text, "")
        self.assertEqual(result.word_count, 0)
        self.assertEqual(result.sentence_count, 0)

    def test_none_input(self):
        """None 입력 처리"""
        result = capture_speech(None)
        self.assertEqual(result.text, "")
        self.assertEqual(result.word_count, 0)

    def test_whitespace_only(self):
        """공백만 있는 입력"""
        result = capture_speech("   ")
        self.assertEqual(result.text, "")

    def test_normal_text(self):
        """일반 텍스트 처리"""
        result = capture_speech("오늘 프로젝트를 시작합니다.")
        self.assertIn("프로젝트", result.text)
        self.assertGreater(result.word_count, 0)
        self.assertGreater(result.sentence_count, 0)

    def test_filler_removal(self):
        """필러가 포함된 텍스트 정제"""
        result = capture_speech("음 이제 뭐랄까 프로젝트를 시작해야 합니다")
        self.assertIn("프로젝트", result.text)
        self.assertGreater(result.word_count, 0)

    def test_repeated_word_removal(self):
        """반복 단어 제거 확인"""
        result = capture_speech("정말 정말 정말 좋은 결과입니다.")
        # '정말'이 1번만 남아야 함
        self.assertEqual(result.text.count("정말"), 1)

    def test_original_length_tracked(self):
        """원본 길이 추적"""
        text = "테스트 텍스트입니다"
        result = capture_speech(text)
        self.assertEqual(result.original_length, len(text))

    def test_cleaned_at_set(self):
        """cleaned_at 타임스탬프 존재"""
        result = capture_speech("테스트.")
        self.assertTrue(result.cleaned_at)

    def test_sentence_ending_added(self):
        """마침표 없는 텍스트에 마침표 추가"""
        result = capture_speech("프로젝트를 시작합니다")
        self.assertTrue(result.text.endswith('.'))

    def test_multiple_sentences(self):
        """여러 문장 처리"""
        result = capture_speech("첫 번째 문장입니다. 두 번째 문장입니다. 세 번째입니다.")
        self.assertEqual(result.sentence_count, 3)


class TestMergeCaptures(unittest.TestCase):
    """merge_captures 함수 테스트"""

    def test_empty_list(self):
        """빈 리스트 → 빈 CapturedText"""
        result = merge_captures([])
        self.assertEqual(result.text, "")
        self.assertEqual(result.word_count, 0)

    def test_single_capture(self):
        """단일 캡처 병합"""
        c = capture_speech("테스트 문장입니다.")
        result = merge_captures([c])
        self.assertIn("테스트", result.text)

    def test_multiple_captures(self):
        """여러 캡처 병합"""
        c1 = capture_speech("첫 번째 내용입니다.")
        c2 = capture_speech("두 번째 내용입니다.")
        result = merge_captures([c1, c2])
        self.assertIn("첫 번째", result.text)
        self.assertIn("두 번째", result.text)

    def test_original_length_summed(self):
        """원본 길이 합산"""
        c1 = CapturedText(text="가나다.", word_count=1, sentence_count=1, original_length=10)
        c2 = CapturedText(text="라마바.", word_count=1, sentence_count=1, original_length=20)
        result = merge_captures([c1, c2])
        self.assertEqual(result.original_length, 30)

    def test_empty_captures_filtered(self):
        """빈 텍스트 캡처는 무시"""
        c1 = CapturedText(text="", word_count=0, sentence_count=0, original_length=0)
        c2 = CapturedText(text="유효한 텍스트.", word_count=2, sentence_count=1, original_length=10)
        result = merge_captures([c1, c2])
        self.assertIn("유효한", result.text)


if __name__ == '__main__':
    unittest.main()
