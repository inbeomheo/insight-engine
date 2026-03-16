"""multi_source_collector 단위 테스트 — URL 소스 타입 감지 + collect_content 위임

NOTE: 서비스 파일에 `from __future__ import annotations`가 파일 맨 앞이 아닌
      위치에 있어 SyntaxError 발생. 이를 우회하여 소스를 동적 로딩합니다.
"""
import re
import sys
import types
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# SyntaxError 우회: 문제 줄을 제거한 뒤 동적 로드
_SERVICE_PATH = Path(__file__).resolve().parent.parent / "services" / "content" / "multi_source_collector.py"


def _load_module():
    """서비스 모듈을 SyntaxError 우회하여 로드"""
    source = _SERVICE_PATH.read_text(encoding="utf-8")
    # `from __future__ import annotations`를 주석 처리 (파일 맨 앞이 아닌 위치)
    fixed = source.replace(
        "from __future__ import annotations",
        "# from __future__ import annotations  # patched for test",
        1,
    )
    mod = types.ModuleType("multi_source_collector")
    mod.__file__ = str(_SERVICE_PATH)
    # logging이 필요하므로 미리 준비
    code = compile(fixed, str(_SERVICE_PATH), "exec")
    exec(code, mod.__dict__)
    return mod


_mod = _load_module()
detect_source_type = _mod.detect_source_type
collect_content = _mod.collect_content

SOURCE_YOUTUBE = _mod.SOURCE_YOUTUBE
SOURCE_WEBPAGE = _mod.SOURCE_WEBPAGE
SOURCE_RSS = _mod.SOURCE_RSS
SOURCE_ARXIV = _mod.SOURCE_ARXIV
SOURCE_TWITTER = _mod.SOURCE_TWITTER
SOURCE_REDDIT = _mod.SOURCE_REDDIT
SOURCE_GITHUB = _mod.SOURCE_GITHUB
SOURCE_HACKERNEWS = _mod.SOURCE_HACKERNEWS
SOURCE_STACKOVERFLOW = _mod.SOURCE_STACKOVERFLOW
SOURCE_PODCAST = _mod.SOURCE_PODCAST


class TestDetectSourceType(unittest.TestCase):
    """detect_source_type: URL -> 소스 타입 자동 감지"""

    def test_youtube_urls(self):
        urls = [
            "https://www.youtube.com/watch?v=abc123",
            "https://youtu.be/abc123",
            "https://m.youtube.com/watch?v=abc123",
        ]
        for url in urls:
            self.assertEqual(detect_source_type(url), SOURCE_YOUTUBE, url)

    def test_arxiv_urls(self):
        urls = [
            "https://arxiv.org/abs/2303.08774",
            "https://arxiv.org/pdf/2303.08774",
            "2303.08774",
        ]
        for url in urls:
            self.assertEqual(detect_source_type(url), SOURCE_ARXIV, url)

    def test_rss_urls(self):
        urls = [
            "https://blog.example.com/feed",
            "https://example.com/rss",
            "https://example.com/blog.xml",
        ]
        for url in urls:
            self.assertEqual(detect_source_type(url), SOURCE_RSS, url)

    def test_twitter_urls(self):
        self.assertEqual(
            detect_source_type("https://twitter.com/user/status/123"),
            SOURCE_TWITTER,
        )
        self.assertEqual(
            detect_source_type("https://x.com/user/status/123"),
            SOURCE_TWITTER,
        )

    def test_reddit_url(self):
        self.assertEqual(
            detect_source_type("https://www.reddit.com/r/python/comments/abc123/title"),
            SOURCE_REDDIT,
        )

    def test_github_url(self):
        self.assertEqual(
            detect_source_type("https://github.com/user/repo"),
            SOURCE_GITHUB,
        )

    def test_hackernews_url(self):
        self.assertEqual(
            detect_source_type("https://news.ycombinator.com/item?id=12345"),
            SOURCE_HACKERNEWS,
        )

    def test_stackoverflow_url(self):
        self.assertEqual(
            detect_source_type("https://stackoverflow.com/questions/12345/title"),
            SOURCE_STACKOVERFLOW,
        )

    def test_spotify_podcast(self):
        self.assertEqual(
            detect_source_type("https://open.spotify.com/episode/abc123"),
            SOURCE_PODCAST,
        )

    def test_audio_file(self):
        self.assertEqual(
            detect_source_type("https://example.com/audio.mp3"),
            SOURCE_PODCAST,
        )

    def test_generic_webpage(self):
        self.assertEqual(
            detect_source_type("https://example.com/article"),
            SOURCE_WEBPAGE,
        )


class TestCollectContent(unittest.TestCase):
    """collect_content: 올바른 collector에 위임되는지 검증"""

    def test_empty_url_raises(self):
        with self.assertRaises(ValueError):
            collect_content("")

    def test_unsupported_source_type_raises(self):
        with self.assertRaises(ValueError):
            collect_content("https://example.com", source_type="unknown_type")


if __name__ == '__main__':
    unittest.main()
