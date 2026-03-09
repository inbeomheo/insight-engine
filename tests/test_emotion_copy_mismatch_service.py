"""emotion_copy_mismatch_service 단위 테스트"""
import unittest

from services.emotion_copy_mismatch_service import (
    MismatchReport,
    detect_mismatch,
    _detect_emotion,
    _find_problem_phrases,
)


class TestDetectEmotion(unittest.TestCase):
    """감정 감지 함수 테스트"""

    def test_joy_keywords(self):
        text = "정말 기쁨과 행복을 주는 멋진 소식입니다."
        self.assertEqual(_detect_emotion(text), "joy")

    def test_sadness_keywords(self):
        text = "슬픔과 우울한 분위기가 감도는 안타까운 이야기입니다."
        self.assertEqual(_detect_emotion(text), "sadness")

    def test_anger_keywords(self):
        text = "분노와 짜증이 나는 최악의 상황입니다."
        self.assertEqual(_detect_emotion(text), "anger")

    def test_neutral_when_no_keywords(self):
        text = "이것은 테스트 문서입니다."
        self.assertEqual(_detect_emotion(text), "neutral")

    def test_empty_text(self):
        self.assertEqual(_detect_emotion(""), "neutral")


class TestFindProblemPhrases(unittest.TestCase):
    """문제 구절 탐지 테스트"""

    def test_no_mismatch_returns_empty(self):
        result = _find_problem_phrases("기쁨 가득한 글", "joy", "joy")
        self.assertEqual(result, [])

    def test_finds_mismatched_phrases(self):
        text = "이건 정말 최악의 상황이다. 분노가 느껴진다."
        result = _find_problem_phrases(text, "joy", "anger")
        self.assertTrue(len(result) > 0)

    def test_max_five_phrases(self):
        text = ". ".join(["슬픔이 있다"] * 10)
        result = _find_problem_phrases(text, "joy", "sadness")
        self.assertLessEqual(len(result), 5)


class TestDetectMismatch(unittest.TestCase):
    """메인 함수 테스트"""

    def test_empty_content(self):
        result = detect_mismatch("", "joy")
        self.assertIsInstance(result, MismatchReport)
        self.assertEqual(result.detected_emotion, "neutral")
        self.assertEqual(result.mismatch_score, 0.0)

    def test_matching_emotion_low_score(self):
        text = "기쁨과 행복이 넘치는 좋은 소식! 멋진 하루!"
        result = detect_mismatch(text, "joy")
        self.assertEqual(result.intended_emotion, "joy")
        self.assertEqual(result.detected_emotion, "joy")
        self.assertEqual(result.mismatch_score, 0.0)

    def test_mismatched_emotion_high_score(self):
        text = "슬픔과 우울함이 가득한 안타까운 이야기입니다."
        result = detect_mismatch(text, "joy")
        self.assertEqual(result.intended_emotion, "joy")
        self.assertEqual(result.detected_emotion, "sadness")
        self.assertGreater(result.mismatch_score, 0.5)

    def test_suggestions_generated_on_mismatch(self):
        text = "분노와 짜증이 나는 답답한 상황입니다."
        result = detect_mismatch(text, "trust")
        self.assertTrue(len(result.suggestions) > 0)

    def test_unknown_emotion_defaults_to_neutral(self):
        result = detect_mismatch("테스트 문장입니다.", "unknown_emotion")
        self.assertEqual(result.intended_emotion, "neutral")

    def test_problem_phrases_populated(self):
        text = "분노가 치밀어 오르는 짜증나는 상황. 최악이다."
        result = detect_mismatch(text, "joy")
        if result.detected_emotion != "joy":
            self.assertTrue(len(result.problem_phrases) > 0)

    def test_no_suggestions_when_matching(self):
        text = "기쁨 행복 좋은 멋진 축하합니다."
        result = detect_mismatch(text, "joy")
        # 일치 시 score가 0이므로 suggestions 비어야 함
        if result.mismatch_score <= 0.3:
            self.assertEqual(result.suggestions, [])

    def test_dataclass_fields(self):
        report = MismatchReport(
            intended_emotion="joy",
            detected_emotion="anger",
            mismatch_score=0.9,
            problem_phrases=["문제 구절"],
            suggestions=["제안"],
        )
        self.assertEqual(report.intended_emotion, "joy")
        self.assertEqual(len(report.problem_phrases), 1)


if __name__ == '__main__':
    unittest.main()
