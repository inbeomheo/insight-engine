"""비디오 API 서비스 테스트"""

import unittest
import json
from services.video_api_service import (
    VideoAPIRequest, VideoAPIResponse,
    process_request, validate_request, format_response,
)


class TestVideoAPIService(unittest.TestCase):
    """비디오 API 서비스 테스트"""

    def _make_request(self, operation="get_info", video_id="abc123", params=None):
        return VideoAPIRequest(
            request_id="req1",
            video_id=video_id,
            operation=operation,
            params=params or {},
        )

    def test_process_request_get_info(self):
        """get_info 처리"""
        req = self._make_request("get_info")
        resp = process_request(req)
        self.assertEqual(resp.status, "success")
        self.assertIn("title", resp.data)
        self.assertIn("duration_seconds", resp.data)

    def test_process_request_get_transcript(self):
        """get_transcript 처리"""
        req = self._make_request("get_transcript")
        resp = process_request(req)
        self.assertEqual(resp.status, "success")
        self.assertIn("segments", resp.data)

    def test_process_request_get_chapters(self):
        """get_chapters 처리"""
        req = self._make_request("get_chapters")
        resp = process_request(req)
        self.assertEqual(resp.status, "success")
        self.assertIn("chapters", resp.data)

    def test_process_request_invalid_operation(self):
        """유효하지 않은 operation"""
        req = self._make_request("delete")
        resp = process_request(req)
        self.assertEqual(resp.status, "error")
        self.assertIn("errors", resp.data)

    def test_process_request_empty_video_id(self):
        """빈 video_id"""
        req = self._make_request(video_id="  ")
        resp = process_request(req)
        self.assertEqual(resp.status, "error")

    def test_process_request_has_timing(self):
        """처리 시간 포함"""
        req = self._make_request()
        resp = process_request(req)
        self.assertGreaterEqual(resp.processing_time_ms, 0)

    def test_validate_request_valid(self):
        """유효한 요청"""
        req = self._make_request()
        errors = validate_request(req)
        self.assertEqual(errors, [])

    def test_validate_request_empty_id(self):
        """빈 video_id 검증"""
        req = self._make_request(video_id="")
        errors = validate_request(req)
        self.assertTrue(len(errors) > 0)

    def test_validate_request_invalid_op(self):
        """유효하지 않은 operation 검증"""
        req = self._make_request(operation="unknown")
        errors = validate_request(req)
        self.assertTrue(any("operation" in e for e in errors))

    def test_format_response_json(self):
        """JSON 포맷"""
        resp = VideoAPIResponse("r1", "success", {"key": "value"}, 1.5)
        formatted = format_response(resp, "json")
        parsed = json.loads(formatted)
        self.assertEqual(parsed["status"], "success")
        self.assertEqual(parsed["data"]["key"], "value")

    def test_format_response_xml(self):
        """XML 포맷"""
        resp = VideoAPIResponse("r1", "success", {"title": "Test"}, 2.0)
        formatted = format_response(resp, "xml")
        self.assertIn('<?xml version="1.0"', formatted)
        self.assertIn("<status>success</status>", formatted)

    def test_format_response_invalid_format(self):
        """지원하지 않는 포맷"""
        resp = VideoAPIResponse("r1", "success", {}, 0)
        with self.assertRaises(ValueError):
            format_response(resp, "csv")

    def test_process_request_preserves_request_id(self):
        """request_id 유지"""
        req = self._make_request()
        resp = process_request(req)
        self.assertEqual(resp.request_id, "req1")

    def test_process_request_transcript_language(self):
        """get_transcript 언어 파라미터"""
        req = self._make_request("get_transcript", params={"language": "en"})
        resp = process_request(req)
        self.assertEqual(resp.data["language"], "en")


if __name__ == "__main__":
    unittest.main()
