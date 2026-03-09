"""message_fragmentation_service 단위 테스트"""
import unittest

from services.message_fragmentation_service import (
    FragmentationReport,
    MessageFragment,
    analyze_fragmentation,
    _detect_tone,
    _summarize_message,
    _extract_keywords,
)


class TestDetectTone(unittest.TestCase):
    """톤 감지 테스트"""

    def test_formal_tone(self):
        text = "안녕하십니까. 안내 말씀드립니다. 고객님께서 바랍니다."
        self.assertEqual(_detect_tone(text), "formal")

    def test_casual_tone(self):
        text = "이거 진짜 대박이에요 ㅋㅋ 꿀팁 있어요"
        self.assertEqual(_detect_tone(text), "casual")

    def test_neutral_no_keywords(self):
        text = "ABC DEF 123"
        self.assertEqual(_detect_tone(text), "neutral")

    def test_promotional_tone(self):
        text = "특가 할인 이벤트! 무료 혜택 쿠폰 제공"
        self.assertEqual(_detect_tone(text), "promotional")


class TestSummarizeMessage(unittest.TestCase):
    """메시지 요약 테스트"""

    def test_short_message_unchanged(self):
        msg = "짧은 메시지"
        self.assertEqual(_summarize_message(msg), "짧은 메시지")

    def test_long_message_truncated(self):
        msg = "가" * 200
        result = _summarize_message(msg, max_len=80)
        self.assertTrue(result.endswith("..."))
        self.assertLessEqual(len(result), 84)  # 80 + "..."

    def test_newlines_replaced(self):
        msg = "첫줄\n둘째줄\n셋째줄"
        result = _summarize_message(msg)
        self.assertNotIn("\n", result)


class TestExtractKeywords(unittest.TestCase):
    """키워드 추출 테스트"""

    def test_korean_words(self):
        keywords = _extract_keywords("마케팅 전략과 콘텐츠 분석")
        self.assertIn("마케팅", keywords)
        self.assertIn("전략과", keywords)

    def test_english_words(self):
        keywords = _extract_keywords("SEO marketing strategy")
        self.assertIn("SEO", keywords)
        self.assertIn("marketing", keywords)

    def test_single_char_excluded(self):
        keywords = _extract_keywords("a 나 bb 다다")
        self.assertNotIn("a", keywords)
        self.assertIn("bb", keywords)


class TestAnalyzeFragmentation(unittest.TestCase):
    """메인 함수 테스트"""

    def test_empty_messages(self):
        result = analyze_fragmentation([])
        self.assertIsInstance(result, FragmentationReport)
        self.assertEqual(result.consistency_score, 0.0)

    def test_consistent_messages(self):
        messages = [
            {"channel": "email", "message": "안내 말씀드립니다. 고객님 바랍니다."},
            {"channel": "sms", "message": "안내 드립니다. 고객님 확인 바랍니다."},
        ]
        result = analyze_fragmentation(messages)
        self.assertGreater(result.consistency_score, 0.5)

    def test_fragmented_messages(self):
        messages = [
            {"channel": "email", "message": "안내 말씀드립니다. 고객님 확인 바랍니다."},
            {"channel": "sns", "message": "대박 ㅋㅋ 꿀팁이에요! 진짜 재미있어요"},
        ]
        result = analyze_fragmentation(messages)
        self.assertEqual(len(result.fragments), 2)

    def test_recommendations_generated(self):
        messages = [
            {"channel": "email", "message": "안내 드립니다."},
            {"channel": "sns", "message": "대박 ㅋㅋ"},
            {"channel": "blog", "message": "긴급 마감 지금 서두르세요"},
        ]
        result = analyze_fragmentation(messages)
        self.assertTrue(len(result.recommendations) > 0)

    def test_fragments_sorted_by_deviation(self):
        messages = [
            {"channel": "a", "message": "동일한 메시지 내용입니다."},
            {"channel": "b", "message": "동일한 메시지 내용입니다."},
            {"channel": "c", "message": "완전히 다른 주제 대박 ㅋㅋ 꿀팁"},
        ]
        result = analyze_fragmentation(messages)
        deviations = [f.deviation_score for f in result.fragments]
        self.assertEqual(deviations, sorted(deviations, reverse=True))

    def test_consistency_between_0_and_1(self):
        messages = [
            {"channel": "a", "message": "테스트 메시지 하나"},
            {"channel": "b", "message": "완전 다른 메시지 대박"},
        ]
        result = analyze_fragmentation(messages)
        self.assertGreaterEqual(result.consistency_score, 0.0)
        self.assertLessEqual(result.consistency_score, 1.0)

    def test_single_message(self):
        messages = [{"channel": "email", "message": "단일 메시지입니다."}]
        result = analyze_fragmentation(messages)
        self.assertEqual(len(result.fragments), 1)

    def test_message_fragment_dataclass(self):
        frag = MessageFragment(
            channel="email", message_summary="요약",
            tone="formal", deviation_score=0.3,
        )
        self.assertEqual(frag.channel, "email")
        self.assertEqual(frag.tone, "formal")

    def test_missing_channel_defaults(self):
        messages = [{"message": "내용만 있는 메시지"}]
        result = analyze_fragmentation(messages)
        self.assertEqual(result.fragments[0].channel, "unknown")


if __name__ == '__main__':
    unittest.main()
