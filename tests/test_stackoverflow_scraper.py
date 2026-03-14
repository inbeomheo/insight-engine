"""
Stack Overflow 스크래퍼 단위 테스트

Stack Exchange API v2.3을 모킹하여 질문/답변 추출을 테스트합니다.
"""
import unittest
from unittest.mock import patch, MagicMock


class TestScrapeStackoverflow(unittest.TestCase):
    """scrape_stackoverflow 단위 테스트"""

    def test_raises_on_invalid_url(self):
        """유효하지 않은 SO URL에서 ValueError 발생"""
        from services.platform.social_scraper_service import scrape_stackoverflow

        with self.assertRaises(ValueError):
            scrape_stackoverflow("https://example.com/not-so")

    @patch("services.social_scraper_service.requests.get")
    def test_extracts_question_and_answers(self, mock_get):
        """질문 + 답변 추출 성공"""
        def side_effect(url, **kwargs):
            resp = MagicMock()
            resp.status_code = 200

            if "/answers" in url:
                # 답변 응답
                resp.json.return_value = {
                    "items": [
                        {
                            "body": "<p>답변 내용입니다.</p>",
                            "score": 42,
                            "is_accepted": True,
                        },
                        {
                            "body": "<p>두 번째 답변</p>",
                            "score": 10,
                            "is_accepted": False,
                        },
                    ]
                }
            else:
                # 질문 응답
                resp.json.return_value = {
                    "items": [{
                        "title": "파이썬에서 리스트 정렬하는 방법",
                        "body": "<p>리스트를 정렬하고 싶습니다.</p>",
                    }]
                }

            return resp

        mock_get.side_effect = side_effect

        from services.platform.social_scraper_service import scrape_stackoverflow

        result = scrape_stackoverflow(
            "https://stackoverflow.com/questions/12345/python-sort"
        )

        self.assertEqual(result["source_type"], "stackoverflow")
        self.assertEqual(result["title"], "파이썬에서 리스트 정렬하는 방법")
        self.assertIn("리스트를 정렬", result["content"])
        self.assertIn("답변 내용", result["content"])
        self.assertIn("votes: 42", result["content"])
        self.assertIn("✓", result["content"])

    @patch("services.social_scraper_service.requests.get")
    def test_question_only_when_answers_fail(self, mock_get):
        """답변 조회 실패 시 질문만 반환"""
        call_count = [0]

        def side_effect(url, **kwargs):
            call_count[0] += 1
            resp = MagicMock()

            if "/answers" in url:
                raise Exception("답변 조회 실패")

            resp.json.return_value = {
                "items": [{
                    "title": "테스트 질문",
                    "body": "<p>질문 본문입니다.</p>",
                }]
            }
            return resp

        mock_get.side_effect = side_effect

        from services.platform.social_scraper_service import scrape_stackoverflow

        result = scrape_stackoverflow(
            "https://stackoverflow.com/questions/99999/test"
        )

        self.assertEqual(result["source_type"], "stackoverflow")
        self.assertIn("질문 본문", result["content"])

    @patch("services.social_scraper_service.requests.get")
    def test_raises_when_question_not_found(self, mock_get):
        """질문을 찾을 수 없을 때 ValueError 발생"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"items": []}
        mock_get.return_value = mock_resp

        from services.platform.social_scraper_service import scrape_stackoverflow

        with self.assertRaises(ValueError) as ctx:
            scrape_stackoverflow(
                "https://stackoverflow.com/questions/00000/not-found"
            )
        self.assertIn("찾을 수 없습니다", str(ctx.exception))

    @patch("services.social_scraper_service.requests.get")
    def test_raises_on_network_error(self, mock_get):
        """네트워크 오류 시 ValueError 발생"""
        import requests as req_lib
        mock_get.side_effect = req_lib.RequestException("Connection error")

        from services.platform.social_scraper_service import scrape_stackoverflow

        with self.assertRaises(ValueError):
            scrape_stackoverflow(
                "https://stackoverflow.com/questions/11111/error"
            )


class TestDetectStackOverflow(unittest.TestCase):
    """multi_source_collector에서 Stack Overflow URL 감지 테스트"""

    def test_detects_stackoverflow(self):
        from services.content.multi_source_collector import detect_source_type
        self.assertEqual(
            detect_source_type("https://stackoverflow.com/questions/12345/how-to-sort"),
            "stackoverflow",
        )

    def test_detects_stackoverflow_with_www(self):
        from services.content.multi_source_collector import detect_source_type
        self.assertEqual(
            detect_source_type("https://www.stackoverflow.com/questions/67890/test"),
            "stackoverflow",
        )


if __name__ == "__main__":
    unittest.main()
