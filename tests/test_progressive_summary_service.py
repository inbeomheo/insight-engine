"""progressive_summary_service 단위 테스트"""
import unittest
from unittest.mock import patch


class TestProgressiveSummary(unittest.TestCase):

    def test_empty_content_raises(self):
        from services.progressive_summary_service import generate_progressive_summary
        with self.assertRaises(ValueError):
            generate_progressive_summary("")

    def test_whitespace_raises(self):
        from services.progressive_summary_service import generate_progressive_summary
        with self.assertRaises(ValueError):
            generate_progressive_summary("   ")

    @patch('services.progressive_summary_service._get_model', return_value='gemini/gemini-3-flash-preview')
    @patch('services.ai_service.create_content')
    def test_successful_summary(self, mock_create, mock_model):
        mock_create.return_value = {
            'content': '{"one_line": "한 줄 요약", "three_lines": "세 줄 요약입니다.", "full_summary": "전체 요약 내용"}'
        }
        from services.progressive_summary_service import generate_progressive_summary
        result = generate_progressive_summary("긴 콘텐츠 내용")
        self.assertEqual(result["one_line"], "한 줄 요약")
        self.assertEqual(result["three_lines"], "세 줄 요약입니다.")
        self.assertEqual(result["full_summary"], "전체 요약 내용")

    @patch('services.progressive_summary_service._get_model', return_value='gemini/gemini-3-flash-preview')
    @patch('services.ai_service.create_content')
    def test_parse_failure_fallback(self, mock_create, mock_model):
        mock_create.return_value = {'content': '유효하지 않은 응답입니다'}
        from services.progressive_summary_service import generate_progressive_summary
        result = generate_progressive_summary("콘텐츠")
        # 파싱 실패 시에도 3개 키 반환
        self.assertIn("one_line", result)
        self.assertIn("three_lines", result)
        self.assertIn("full_summary", result)

    @patch('services.progressive_summary_service._get_model', return_value='gemini/gemini-3-flash-preview')
    @patch('services.ai_service.create_content')
    def test_long_content_truncated(self, mock_create, mock_model):
        mock_create.return_value = {
            'content': '{"one_line": "요약", "three_lines": "세 줄", "full_summary": "전체"}'
        }
        from services.progressive_summary_service import generate_progressive_summary
        long_content = "가" * 10000
        result = generate_progressive_summary(long_content)
        self.assertIsInstance(result, dict)


if __name__ == '__main__':
    unittest.main()
