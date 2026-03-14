"""
소셜 미디어 스크래퍼 서비스 단위 테스트

Twitter, Reddit, Hacker News 스크래퍼 함수의 모킹 테스트.
"""
import unittest
from unittest.mock import patch, MagicMock


class TestScrapeTwitterThread(unittest.TestCase):
    """scrape_twitter_thread 단위 테스트"""

    @patch("services.platform.social_scraper_service._extract_with_trafilatura")
    def test_extracts_via_nitter(self, mock_extract):
        """nitter 인스턴스를 통해 본문 추출 성공"""
        # 첫 번째 nitter 인스턴스에서 성공
        mock_extract.return_value = ("테스트 트윗", "이것은 테스트 트윗 본문입니다. 충분히 긴 콘텐츠를 포함하고 있어야 합니다. 최소 30자 이상.")
        from services.platform.social_scraper_service import scrape_twitter_thread

        result = scrape_twitter_thread("https://twitter.com/user/status/123456")

        self.assertEqual(result["source_type"], "twitter")
        self.assertIn("테스트 트윗", result["content"])
        self.assertEqual(result["url"], "https://twitter.com/user/status/123456")
        # nitter URL로 호출되었는지 확인
        first_call_url = mock_extract.call_args_list[0][0][0]
        self.assertIn("nitter", first_call_url)

    @patch("services.platform.social_scraper_service._extract_with_trafilatura")
    def test_fallback_to_original_url(self, mock_extract):
        """nitter 실패 시 원본 URL로 폴백"""
        # nitter 인스턴스 실패 (2번) + 원본 URL 성공 (1번)
        mock_extract.side_effect = [
            ("", ""),  # nitter.net 실패
            ("", ""),  # nitter.privacydev.net 실패
            ("원본 트윗", "원본 URL에서 추출된 충분히 긴 본문 콘텐츠입니다. 최소 30자 이상의 텍스트가 필요합니다."),
        ]
        from services.platform.social_scraper_service import scrape_twitter_thread

        result = scrape_twitter_thread("https://x.com/user/status/789")

        self.assertEqual(result["source_type"], "twitter")
        self.assertIn("원본 URL에서 추출", result["content"])

    @patch("services.platform.social_scraper_service._extract_with_trafilatura")
    def test_raises_when_all_fail(self, mock_extract):
        """모든 추출 실패 시 ValueError 발생"""
        mock_extract.return_value = ("", "")
        from services.platform.social_scraper_service import scrape_twitter_thread

        with self.assertRaises(ValueError):
            scrape_twitter_thread("https://twitter.com/user/status/999")

    @patch("services.platform.social_scraper_service._extract_with_trafilatura")
    def test_generates_title_from_url(self, mock_extract):
        """제목이 없으면 URL에서 기본 제목 생성"""
        mock_extract.return_value = ("", "이것은 제목 없이 본문만 추출된 충분히 긴 콘텐츠입니다. 최소 30자 이상의 텍스트가 필요합니다.")
        from services.platform.social_scraper_service import scrape_twitter_thread

        result = scrape_twitter_thread("https://twitter.com/testuser/status/123")

        self.assertIn("testuser", result["title"])


class TestScrapeRedditPost(unittest.TestCase):
    """scrape_reddit_post 단위 테스트"""

    @patch("services.platform.social_scraper_service.requests.get")
    def test_extracts_post_and_comments(self, mock_get):
        """포스트 본문 + 상위 댓글 추출"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {
                "data": {
                    "children": [{
                        "data": {
                            "title": "테스트 포스트",
                            "selftext": "포스트 본문입니다.",
                        }
                    }]
                }
            },
            {
                "data": {
                    "children": [
                        {"kind": "t1", "data": {"body": "첫 번째 댓글"}},
                        {"kind": "t1", "data": {"body": "두 번째 댓글"}},
                    ]
                }
            },
        ]
        mock_get.return_value = mock_resp

        from services.platform.social_scraper_service import scrape_reddit_post

        result = scrape_reddit_post("https://reddit.com/r/test/comments/abc123/title")

        self.assertEqual(result["title"], "테스트 포스트")
        self.assertIn("포스트 본문", result["content"])
        self.assertIn("첫 번째 댓글", result["content"])
        self.assertEqual(result["source_type"], "reddit")

    @patch("services.platform.social_scraper_service.requests.get")
    def test_post_without_comments(self, mock_get):
        """댓글 없는 포스트"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {"data": {"children": [{"data": {"title": "제목만", "selftext": "본문만 있는 포스트입니다."}}]}},
        ]
        mock_get.return_value = mock_resp

        from services.platform.social_scraper_service import scrape_reddit_post

        result = scrape_reddit_post("https://reddit.com/r/test/comments/xyz/title")

        self.assertEqual(result["title"], "제목만")
        self.assertNotIn("상위 댓글", result["content"])

    @patch("services.platform.social_scraper_service.requests.get")
    def test_raises_on_network_error(self, mock_get):
        """네트워크 오류 시 ValueError 발생"""
        import requests as req_lib
        mock_get.side_effect = req_lib.RequestException("Connection error")

        from services.platform.social_scraper_service import scrape_reddit_post

        with self.assertRaises(ValueError):
            scrape_reddit_post("https://reddit.com/r/test/comments/bad/title")


class TestScrapeHackernews(unittest.TestCase):
    """scrape_hackernews 단위 테스트"""

    @patch("services.platform.social_scraper_service.requests.get")
    def test_extracts_item_and_comments(self, mock_get):
        """아이템 + 상위 댓글 추출"""
        def side_effect(url, **kwargs):
            resp = MagicMock()
            if "/item/123.json" in url:
                resp.json.return_value = {
                    "title": "Show HN: 테스트 프로젝트",
                    "text": "프로젝트 설명",
                    "url": "https://example.com",
                    "kids": [456],
                }
            elif "/item/456.json" in url:
                resp.json.return_value = {
                    "text": "좋은 프로젝트네요!",
                }
            return resp

        mock_get.side_effect = side_effect

        from services.platform.social_scraper_service import scrape_hackernews

        result = scrape_hackernews("https://news.ycombinator.com/item?id=123")

        self.assertEqual(result["title"], "Show HN: 테스트 프로젝트")
        self.assertIn("프로젝트 설명", result["content"])
        self.assertIn("좋은 프로젝트", result["content"])
        self.assertEqual(result["source_type"], "hackernews")

    def test_raises_on_invalid_url(self):
        """유효하지 않은 HN URL에서 ValueError 발생"""
        from services.platform.social_scraper_service import scrape_hackernews

        with self.assertRaises(ValueError):
            scrape_hackernews("https://example.com/not-hn")

    @patch("services.platform.social_scraper_service.requests.get")
    def test_raises_when_item_not_found(self, mock_get):
        """아이템을 찾을 수 없을 때 ValueError 발생"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = None
        mock_get.return_value = mock_resp

        from services.platform.social_scraper_service import scrape_hackernews

        with self.assertRaises(ValueError):
            scrape_hackernews("https://news.ycombinator.com/item?id=999999")


class TestDetectSourceType(unittest.TestCase):
    """multi_source_collector.detect_source_type 소셜 URL 감지 테스트"""

    def test_detects_twitter(self):
        from services.content.multi_source_collector import detect_source_type
        self.assertEqual(detect_source_type("https://twitter.com/user/status/123"), "twitter")
        self.assertEqual(detect_source_type("https://x.com/user/status/456"), "twitter")

    def test_detects_reddit(self):
        from services.content.multi_source_collector import detect_source_type
        self.assertEqual(
            detect_source_type("https://www.reddit.com/r/python/comments/abc123/title"),
            "reddit",
        )

    def test_detects_hackernews(self):
        from services.content.multi_source_collector import detect_source_type
        self.assertEqual(
            detect_source_type("https://news.ycombinator.com/item?id=12345"),
            "hackernews",
        )

    def test_detects_github(self):
        from services.content.multi_source_collector import detect_source_type
        self.assertEqual(
            detect_source_type("https://github.com/owner/repo"),
            "github",
        )


if __name__ == "__main__":
    unittest.main()
