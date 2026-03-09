"""네이티브 스레드 변환 서비스 테스트"""
import unittest

from services.native_thread_service import (
    ThreadParts,
    convert_to_thread,
    _strip_markdown,
    _extract_hashtags,
    _split_by_sentences,
    _split_into_parts,
    _add_thread_numbering,
)


class TestStripMarkdown(unittest.TestCase):
    """마크다운 제거 테스트"""

    def test_headings(self):
        """제목 마크다운 제거"""
        self.assertEqual(_strip_markdown("## 제목입니다"), "제목입니다")

    def test_bold(self):
        """볼드 마크다운 제거"""
        self.assertEqual(_strip_markdown("**강조**"), "강조")

    def test_italic(self):
        """이탤릭 마크다운 제거"""
        self.assertEqual(_strip_markdown("*기울임*"), "기울임")

    def test_inline_code(self):
        """인라인 코드 마크다운 제거"""
        self.assertEqual(_strip_markdown("`코드`"), "코드")

    def test_link(self):
        """링크 마크다운 변환"""
        result = _strip_markdown("[텍스트](https://example.com)")
        self.assertIn("텍스트", result)
        self.assertNotIn("[", result)

    def test_list_bullet(self):
        """리스트 마커 변환"""
        result = _strip_markdown("- 항목")
        self.assertIn("•", result)


class TestExtractHashtags(unittest.TestCase):
    """해시태그 추출 테스트"""

    def test_existing_hashtags(self):
        """기존 해시태그 수집"""
        text = "이것은 #파이썬 과 #프로그래밍 에 대한 글"
        tags = _extract_hashtags(text)
        self.assertIn("파이썬", tags)
        self.assertIn("프로그래밍", tags)

    def test_max_count(self):
        """최대 개수 제한"""
        text = "#a #b #c #d #e #f #g"
        tags = _extract_hashtags(text, max_count=3)
        self.assertLessEqual(len(tags), 3)

    def test_no_hashtags_extracts_keywords(self):
        """해시태그 없으면 키워드에서 추출"""
        text = "파이썬 프로그래밍 가이드 완벽 정리"
        tags = _extract_hashtags(text)
        self.assertGreater(len(tags), 0)

    def test_dedup(self):
        """중복 해시태그 제거"""
        text = "#파이썬 #파이썬 #파이썬"
        tags = _extract_hashtags(text)
        self.assertEqual(tags.count("파이썬"), 1)


class TestSplitBySentences(unittest.TestCase):
    """문장 분리 테스트"""

    def test_period_split(self):
        """마침표로 분리"""
        result = _split_by_sentences("첫 문장. 두 번째 문장.")
        self.assertEqual(len(result), 2)

    def test_question_split(self):
        """물음표로 분리"""
        result = _split_by_sentences("질문? 대답.")
        self.assertEqual(len(result), 2)

    def test_empty_string(self):
        """빈 문자열"""
        result = _split_by_sentences("")
        self.assertEqual(len(result), 0)


class TestSplitIntoParts(unittest.TestCase):
    """파트 분할 테스트"""

    def test_short_text_single_part(self):
        """짧은 텍스트 → 파트 1개"""
        parts = _split_into_parts("짧은 글.", 500)
        self.assertEqual(len(parts), 1)

    def test_long_text_multiple_parts(self):
        """긴 텍스트 → 여러 파트"""
        text = ". ".join([f"문장 {i}입니다" for i in range(50)])
        parts = _split_into_parts(text, 100)
        self.assertGreater(len(parts), 1)

    def test_each_part_within_limit(self):
        """각 파트가 글자 제한 내"""
        text = ". ".join([f"이것은 문장 번호 {i}입니다" for i in range(30)])
        limit = 80
        parts = _split_into_parts(text, limit)
        for part in parts:
            self.assertLessEqual(len(part), limit + 50)  # 문장 단위라 약간 초과 가능

    def test_very_long_sentence_forced_split(self):
        """단일 긴 문장 → 강제 분할"""
        long_sentence = "가" * 600
        parts = _split_into_parts(long_sentence, 200)
        self.assertGreater(len(parts), 1)


class TestAddThreadNumbering(unittest.TestCase):
    """스레드 번호 매기기 테스트"""

    def test_single_part_no_numbering(self):
        """1개 파트면 번호 안 붙임"""
        result = _add_thread_numbering(["단일 파트"])
        self.assertEqual(result, ["단일 파트"])

    def test_multiple_parts_numbered(self):
        """여러 파트에 (1/N) 형태 번호"""
        result = _add_thread_numbering(["파트1", "파트2", "파트3"])
        self.assertTrue(result[0].startswith("(1/3)"))
        self.assertTrue(result[2].startswith("(3/3)"))


class TestConvertToThread(unittest.TestCase):
    """스레드 변환 통합 테스트"""

    def test_empty_content_raises(self):
        """빈 콘텐츠 → ValueError"""
        with self.assertRaises(ValueError):
            convert_to_thread("")

    def test_whitespace_only_raises(self):
        """공백만 → ValueError"""
        with self.assertRaises(ValueError):
            convert_to_thread("   ")

    def test_basic_conversion(self):
        """기본 변환 성공"""
        result = convert_to_thread("이것은 테스트 콘텐츠입니다.")
        self.assertIsInstance(result, ThreadParts)
        self.assertEqual(result.platform, "threads")
        self.assertGreater(result.total_parts, 0)
        self.assertEqual(len(result.parts), result.total_parts)

    def test_platform_normalization(self):
        """플랫폼명 정규화"""
        result = convert_to_thread("테스트", platform="  BLUESKY  ")
        self.assertEqual(result.platform, "bluesky")

    def test_threads_char_limit(self):
        """Threads 500자 제한"""
        long_text = "안녕하세요. " * 200
        result = convert_to_thread(long_text, platform="threads")
        self.assertGreater(result.total_parts, 1)

    def test_twitter_char_limit(self):
        """Twitter 280자 제한 → 더 많은 파트"""
        long_text = "안녕하세요. " * 200
        threads_result = convert_to_thread(long_text, platform="threads")
        twitter_result = convert_to_thread(long_text, platform="twitter")
        self.assertGreaterEqual(twitter_result.total_parts, threads_result.total_parts)

    def test_markdown_stripped(self):
        """마크다운이 제거됨"""
        content = "## 제목\n**굵은** 글씨와 *기울임*"
        result = convert_to_thread(content)
        for part in result.parts:
            self.assertNotIn("##", part)
            self.assertNotIn("**", part)

    def test_hashtags_extracted(self):
        """해시태그 추출"""
        content = "#파이썬 프로그래밍 #AI 가이드. 좋은 내용입니다."
        result = convert_to_thread(content)
        self.assertIsInstance(result.hashtags, list)

    def test_unknown_platform_uses_default(self):
        """알 수 없는 플랫폼 → 500자 기본 제한"""
        result = convert_to_thread("테스트 콘텐츠입니다.", platform="unknown_platform")
        self.assertEqual(result.platform, "unknown_platform")
        self.assertGreater(result.total_parts, 0)


if __name__ == "__main__":
    unittest.main()
