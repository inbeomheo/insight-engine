"""AI 흔적 포렌식 서비스 테스트."""

import unittest
from services.ai_forensics_service import (
    ForensicIndicator,
    ForensicReport,
    analyze_content,
    detect_repetitive_patterns,
    detect_uniform_length,
    detect_generic_transitions,
    calculate_ai_probability,
)


class TestAIForensicsService(unittest.TestCase):
    """AIForensicsService 단위 테스트."""

    def test_detect_repetitive_patterns_found(self):
        """반복 3-gram이 있으면 탐지한다."""
        # 동일 3-gram을 3회 이상 반복
        text = "이것은 테스트 문장입니다. 이것은 테스트 문장입니다. 이것은 테스트 문장입니다. 다른 내용."
        result = detect_repetitive_patterns(text)
        self.assertIsNotNone(result)
        self.assertEqual(result.indicator_type, "repetitive_phrases")
        self.assertGreater(result.confidence, 0)

    def test_detect_repetitive_patterns_none(self):
        """반복 없으면 None."""
        text = "모든 문장이 서로 다른 내용을 포함합니다."
        result = detect_repetitive_patterns(text)
        self.assertIsNone(result)

    def test_detect_repetitive_patterns_short_text(self):
        """짧은 텍스트는 None."""
        result = detect_repetitive_patterns("짧음")
        self.assertIsNone(result)

    def test_detect_uniform_length_detected(self):
        """균일한 문장 길이가 탐지된다."""
        # 모두 비슷한 길이의 문장
        sentences = ["가나다라마바" for _ in range(10)]
        text = ". ".join(sentences) + "."
        result = detect_uniform_length(text)
        self.assertIsNotNone(result)
        self.assertEqual(result.indicator_type, "uniform_length")

    def test_detect_uniform_length_varied(self):
        """길이가 다양하면 None."""
        text = "짧. 이것은 아주 아주 아주 아주 아주 긴 문장입니다. 중간. 또 다른 매우 매우 긴 문장이 여기에 있습니다. 짧은 문장."
        result = detect_uniform_length(text)
        self.assertIsNone(result)

    def test_detect_uniform_length_few_sentences(self):
        """5문장 미만이면 None."""
        text = "하나. 둘. 셋."
        result = detect_uniform_length(text)
        self.assertIsNone(result)

    def test_detect_generic_transitions_high_ratio(self):
        """전환어 비율 30% 이상이면 탐지한다."""
        text = "또한 이런 내용입니다. 그러나 다른 의견도 있습니다. 따라서 결론을 내립니다. 한편 새로운 관점도 있습니다."
        result = detect_generic_transitions(text)
        self.assertIsNotNone(result)
        self.assertEqual(result.indicator_type, "generic_transitions")

    def test_detect_generic_transitions_low_ratio(self):
        """전환어 비율이 낮으면 None."""
        text = "사과는 빨갛다. 바나나는 노랗다. 포도는 보라색이다. 수박은 초록색이다."
        result = detect_generic_transitions(text)
        self.assertIsNone(result)

    def test_detect_generic_transitions_short(self):
        """3문장 미만이면 None."""
        text = "또한 이렇습니다."
        result = detect_generic_transitions(text)
        self.assertIsNone(result)

    def test_calculate_ai_probability_no_indicators(self):
        """지표 없으면 0.0."""
        self.assertEqual(calculate_ai_probability([]), 0.0)

    def test_calculate_ai_probability_with_indicators(self):
        """지표가 있으면 0.0 초과."""
        indicators = [
            ForensicIndicator("repetitive_phrases", 0.8, "test"),
            ForensicIndicator("uniform_length", 0.6, "test"),
        ]
        prob = calculate_ai_probability(indicators)
        self.assertGreater(prob, 0.0)
        self.assertLessEqual(prob, 1.0)

    def test_calculate_ai_probability_max_1(self):
        """확률이 1.0을 초과하지 않는다."""
        indicators = [
            ForensicIndicator("repetitive_phrases", 1.0, "test"),
            ForensicIndicator("uniform_length", 1.0, "test"),
            ForensicIndicator("generic_transitions", 1.0, "test"),
        ]
        prob = calculate_ai_probability(indicators)
        self.assertLessEqual(prob, 1.0)

    def test_analyze_content_returns_report(self):
        """analyze_content는 ForensicReport를 반환한다."""
        content = {"id": "test1", "text": "간단한 테스트 텍스트입니다."}
        report = analyze_content(content)
        self.assertIsInstance(report, ForensicReport)
        self.assertEqual(report.content_id, "test1")

    def test_analyze_content_human_edits_detected(self):
        """인간 편집 흔적이 탐지된다 (ㅋㅋ, ... 등)."""
        content = {"text": "이건 정말 웃기다 ㅋㅋㅋ 그리고 또..."}
        report = analyze_content(content)
        self.assertTrue(report.human_edits_detected)

    def test_analyze_content_no_human_edits(self):
        """인간 편집 흔적이 없으면 False."""
        content = {"text": "깔끔하게 작성된 공식 문서입니다. 내용이 정확합니다."}
        report = analyze_content(content)
        self.assertFalse(report.human_edits_detected)

    def test_analyze_content_generates_id(self):
        """id가 없으면 자동 생성한다."""
        report = analyze_content({"text": "test"})
        self.assertTrue(report.content_id.startswith("fc_"))

    def test_analyze_content_ai_like_text(self):
        """AI 스타일 텍스트에서 지표가 탐지된다."""
        # 균일 길이 + 전환어 다수
        text = (
            "또한 이 기술은 매우 유용합니다. "
            "그러나 한계도 분명히 존재합니다. "
            "따라서 신중한 접근이 필요합니다. "
            "한편 새로운 발전도 기대됩니다. "
            "게다가 시장 성장이 예상됩니다. "
            "마찬가지로 경쟁도 치열해집니다. "
            "결론적으로 전략적 투자가 중요합니다. "
            "이처럼 변화가 빠르게 진행됩니다. "
        )
        report = analyze_content({"text": text})
        self.assertGreater(len(report.indicators), 0)

    def test_analyze_content_empty_text(self):
        """빈 텍스트도 오류 없이 처리된다."""
        report = analyze_content({"text": ""})
        self.assertIsInstance(report, ForensicReport)
        self.assertEqual(report.ai_probability, 0.0)


if __name__ == "__main__":
    unittest.main()
