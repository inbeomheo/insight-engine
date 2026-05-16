"""content_service의 순수 유틸리티 함수 테스트

URL 추출, 자막 파싱, SSRF 방어, 언어 감지, 캐시 정리 등
외부 의존성 없는 함수에 집중. 통합 동작(자막 4단계 폴백 등)은 별도 통합 테스트에서.
"""
import os
import re
import shutil
import tempfile
import unittest
from unittest.mock import patch

from services.core import content_service
from services.core.content_service import (
    _sanitize_video_id,
    _parse_vtt,
    _parse_timedtext_xml,
    _is_safe_caption_url,
    _detect_language_from_text,
    is_youtube_url,
    get_video_id,
    clear_cache,
    purge_expired_cache,
)


class TestSanitizeVideoId(unittest.TestCase):
    """Path Traversal 방어 — video_id 형식 검증"""

    def test_valid_id_returns_same(self):
        valid = "dQw4w9WgXcQ"
        self.assertEqual(_sanitize_video_id(valid), valid)

    def test_valid_id_with_dash_and_underscore(self):
        self.assertEqual(_sanitize_video_id("ab_cd-EF123"), "ab_cd-EF123")

    def test_too_short(self):
        with self.assertRaises(ValueError):
            _sanitize_video_id("short")

    def test_too_long(self):
        with self.assertRaises(ValueError):
            _sanitize_video_id("a" * 12)

    def test_path_traversal_blocked(self):
        for evil in ("../etc/pas", "..\\system32", "abc/def/ghi", "../../../zz"):
            with self.subTest(evil=evil):
                with self.assertRaises(ValueError):
                    _sanitize_video_id(evil)

    def test_empty_or_none(self):
        with self.assertRaises(ValueError):
            _sanitize_video_id("")
        with self.assertRaises(ValueError):
            _sanitize_video_id(None)  # type: ignore[arg-type]

    def test_special_characters_blocked(self):
        for bad in ("aaaaaaaaaa!", "abc def ghi1", "12345678901;"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    _sanitize_video_id(bad)


class TestUrlDetection(unittest.TestCase):
    """YouTube URL 인식 및 video_id 추출"""

    VALID_URLS = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "http://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
    ]

    INVALID_URLS = [
        "https://vimeo.com/12345",
        "https://example.com",
        "not a url",
        "",
    ]

    def test_valid_urls_recognized(self):
        for url in self.VALID_URLS:
            with self.subTest(url=url):
                self.assertTrue(is_youtube_url(url), url)

    def test_invalid_urls_rejected(self):
        for url in self.INVALID_URLS:
            with self.subTest(url=url):
                self.assertFalse(is_youtube_url(url), url)

    def test_video_id_extraction(self):
        cases = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10s", "dQw4w9WgXcQ"),
        ]
        for url, expected in cases:
            with self.subTest(url=url):
                self.assertEqual(get_video_id(url), expected)

    def test_video_id_none_for_invalid(self):
        self.assertIsNone(get_video_id(""))
        self.assertIsNone(get_video_id("not a url"))
        self.assertIsNone(get_video_id("https://example.com/no-video-here"))


class TestParseVtt(unittest.TestCase):
    """VTT 자막 파서"""

    def test_basic_vtt(self):
        vtt = (
            "WEBVTT\n\n"
            "1\n"
            "00:00:00.000 --> 00:00:02.000\n"
            "안녕하세요\n\n"
            "2\n"
            "00:00:02.000 --> 00:00:04.000\n"
            "반갑습니다\n"
        )
        self.assertEqual(_parse_vtt(vtt), "안녕하세요 반갑습니다")

    def test_strips_inline_tags(self):
        vtt = (
            "WEBVTT\n\n"
            "00:00:00.000 --> 00:00:01.000\n"
            "<c.colorE5E5E5>hello</c> <b>world</b>\n"
        )
        self.assertEqual(_parse_vtt(vtt), "hello world")

    def test_empty_input(self):
        self.assertEqual(_parse_vtt(""), "")
        self.assertEqual(_parse_vtt("   "), "")

    def test_non_string_input(self):
        self.assertEqual(_parse_vtt(None), "")  # type: ignore[arg-type]
        self.assertEqual(_parse_vtt(123), "")  # type: ignore[arg-type]

    def test_only_header_returns_empty(self):
        self.assertEqual(_parse_vtt("WEBVTT\n\n"), "")


class TestParseTimedtextXml(unittest.TestCase):
    """TimedText XML 자막 파서"""

    def test_basic_xml(self):
        xml = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<transcript>'
            '<text start="0" dur="2">Hello</text>'
            '<text start="2" dur="2">World</text>'
            '</transcript>'
        )
        self.assertEqual(_parse_timedtext_xml(xml), "Hello World")

    def test_unescapes_html_entities(self):
        xml = '<transcript><text>&amp;quot;He said&amp;quot;</text></transcript>'
        # &amp;quot; → &quot;는 한 번만 unescape (정확한 동작 검증)
        result = _parse_timedtext_xml(xml)
        self.assertIn("He said", result)

    def test_malformed_xml_returns_empty(self):
        self.assertEqual(_parse_timedtext_xml("<not closed"), "")

    def test_empty_input(self):
        self.assertEqual(_parse_timedtext_xml(""), "")
        self.assertEqual(_parse_timedtext_xml(None), "")  # type: ignore[arg-type]

    def test_strips_newlines_in_text_content(self):
        xml = '<transcript><text>line1\nline2</text></transcript>'
        self.assertEqual(_parse_timedtext_xml(xml), "line1 line2")


class TestIsSafeCaptionUrl(unittest.TestCase):
    """SSRF 방어 — YouTube/Google 도메인 화이트리스트"""

    def test_youtube_https_allowed(self):
        self.assertTrue(_is_safe_caption_url("https://www.youtube.com/api/timedtext?v=abc"))

    def test_googlevideo_allowed(self):
        self.assertTrue(_is_safe_caption_url("https://r1---sn-abc.googlevideo.com/timedtext?x=1"))

    def test_http_scheme_allowed(self):
        # 코드는 http/https 모두 허용 (HSTS는 별개)
        self.assertTrue(_is_safe_caption_url("http://www.youtube.com/api/timedtext"))

    def test_other_domains_blocked(self):
        for bad in (
            "https://evil.com/api/timedtext",
            "https://attacker.youtube.com.evil.com/x",  # 서브도메인 사칭
            "https://youtube.com.attacker.com/x",
            "file:///etc/passwd",
            "javascript:alert(1)",
            "ftp://youtube.com/x",
        ):
            with self.subTest(url=bad):
                self.assertFalse(_is_safe_caption_url(bad), bad)

    def test_invalid_inputs(self):
        self.assertFalse(_is_safe_caption_url(""))
        self.assertFalse(_is_safe_caption_url("not a url"))


class TestDetectLanguage(unittest.TestCase):
    """언어 감지 (한/일/중/영)"""

    def test_korean(self):
        self.assertEqual(_detect_language_from_text("안녕하세요 반갑습니다 오늘 날씨가 좋네요"), "ko")

    def test_japanese_hiragana(self):
        self.assertEqual(_detect_language_from_text("こんにちは、今日はいい天気ですね"), "ja")

    def test_japanese_katakana(self):
        self.assertEqual(_detect_language_from_text("コンピュータ プログラミング ソフトウェア テクノロジー システム"), "ja")

    def test_chinese(self):
        self.assertEqual(_detect_language_from_text("你好世界 今天天气真好我们去公园散步吧好不好"), "zh")

    def test_english(self):
        self.assertEqual(_detect_language_from_text("Hello world this is a test"), "en")

    def test_empty(self):
        self.assertEqual(_detect_language_from_text(""), "unknown")


class TestCacheOperations(unittest.TestCase):
    """캐시 디렉토리 작업 — clear_cache / purge_expired_cache"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="ie_cache_test_")
        self._orig_cache_dir = content_service.CACHE_DIR
        content_service.CACHE_DIR = self.tmpdir

    def tearDown(self):
        content_service.CACHE_DIR = self._orig_cache_dir
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _touch(self, name: str, age_seconds: float = 0) -> str:
        path = os.path.join(self.tmpdir, name)
        with open(path, 'w', encoding='utf-8') as f:
            f.write('{"x":1}')
        if age_seconds > 0:
            import time as _t
            past = _t.time() - age_seconds
            os.utime(path, (past, past))
        return path

    def test_clear_cache_all(self):
        self._touch("dQw4w9WgXcQ_transcript.json")
        self._touch("ab_cd-EF123_comments.json")
        self.assertEqual(clear_cache(), 2)
        self.assertEqual(len(os.listdir(self.tmpdir)), 0)

    def test_clear_cache_by_video_id(self):
        self._touch("dQw4w9WgXcQ_transcript.json")
        self._touch("dQw4w9WgXcQ_comments.json")
        self._touch("ab_cd-EF123_transcript.json")
        deleted = clear_cache("dQw4w9WgXcQ")
        self.assertEqual(deleted, 2)
        remaining = os.listdir(self.tmpdir)
        self.assertEqual(remaining, ["ab_cd-EF123_transcript.json"])

    def test_clear_cache_rejects_invalid_id(self):
        """Path Traversal 시도 — clear_cache가 _sanitize_video_id로 거부"""
        with self.assertRaises(ValueError):
            clear_cache("../etc/passwd")

    def test_purge_expired_cache(self):
        # 1시간 전 파일 (오래됨)
        old = self._touch("ab_cd-EF1234_transcript.json", age_seconds=3700)
        # 방금 파일 (신선)
        fresh = self._touch("dQw4w9WgXcQ_transcript.json", age_seconds=0)
        result = purge_expired_cache(max_age_hours=1)
        self.assertEqual(result['purged'], 1)
        self.assertEqual(result['remaining'], 1)
        self.assertTrue(result['freed_bytes'] > 0)
        self.assertFalse(os.path.exists(old))
        self.assertTrue(os.path.exists(fresh))

    def test_purge_empty_cache_dir(self):
        result = purge_expired_cache(max_age_hours=1)
        self.assertEqual(result, {'purged': 0, 'remaining': 0, 'freed_bytes': 0})


if __name__ == '__main__':
    unittest.main()
