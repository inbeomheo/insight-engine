"""progressive_summary_service 단위 테스트"""
import unittest
from unittest.mock import patch


class TestProgressiveSummary(unittest.TestCase):

    def test_empty_content_raises(self):
        from services.content.progressive_summary_service import generate_progressive_summary
        with self.assertRaises(ValueError):
            generate_progressive_summary("")

    def test_whitespace_raises(self):
        from services.content.progressive_summary_service import generate_progressive_summary
        with self.assertRaises(ValueError):
            generate_progressive_summary("   ")

    @patch('services.content.progressive_summary_service._get_model', return_value='gemini/gemini-3-flash-preview')
    @patch('services.core.ai_service.create_content')
    def test_successful_summary(self, mock_create, mock_model):
        mock_create.return_value = {
            'content': '{"one_line": "한 줄 요약", "three_lines": "세 줄 요약입니다.", "full_summary": "전체 요약 내용"}'
        }
        from services.content.progressive_summary_service import generate_progressive_summary
        result = generate_progressive_summary("긴 콘텐츠 내용")
        self.assertEqual(result["one_line"], "한 줄 요약")
        self.assertEqual(result["three_lines"], "세 줄 요약입니다.")
        self.assertEqual(result["full_summary"], "전체 요약 내용")

    @patch('services.content.progressive_summary_service._get_model', return_value='gemini/gemini-3-flash-preview')
    @patch('services.core.ai_service.create_content')
    def test_parse_failure_fallback(self, mock_create, mock_model):
        mock_create.return_value = {'content': '유효하지 않은 응답입니다'}
        from services.content.progressive_summary_service import generate_progressive_summary
        result = generate_progressive_summary("콘텐츠")
        # 파싱 실패 시에도 3개 키 반환
        self.assertIn("one_line", result)
        self.assertIn("three_lines", result)
        self.assertIn("full_summary", result)

    @patch('services.content.progressive_summary_service._get_model', return_value='gemini/gemini-3-flash-preview')
    @patch('services.core.ai_service.create_content')
    def test_long_content_truncated(self, mock_create, mock_model):
        mock_create.return_value = {
            'content': '{"one_line": "요약", "three_lines": "세 줄", "full_summary": "전체"}'
        }
        from services.content.progressive_summary_service import generate_progressive_summary
        long_content = "가" * 10000
        result = generate_progressive_summary(long_content)
        self.assertIsInstance(result, dict)


class TestParseSummaryJson(unittest.TestCase):
    """_parse_summary_json 단위 테스트"""

    def test_valid_json(self):
        """유효한 JSON 파싱"""
        from services.content.progressive_summary_service import _parse_summary_json
        result = _parse_summary_json('{"one_line": "test"}')
        self.assertEqual(result['one_line'], 'test')

    def test_code_block_wrapped(self):
        """코드 블록으로 감싸진 JSON"""
        from services.content.progressive_summary_service import _parse_summary_json
        result = _parse_summary_json('```json\n{"one_line": "test"}\n```')
        self.assertEqual(result['one_line'], 'test')

    def test_trailing_comma(self):
        """LLM 출력의 trailing comma 처리"""
        from services.content.progressive_summary_service import _parse_summary_json
        result = _parse_summary_json('{"one_line": "test", "three_lines": "abc",}')
        self.assertIsNotNone(result)
        self.assertEqual(result['one_line'], 'test')

    def test_nested_trailing_comma(self):
        """중첩 구조의 trailing comma"""
        from services.content.progressive_summary_service import _parse_summary_json
        result = _parse_summary_json('{"one_line": "a", "three_lines": "b", "full_summary": "c",}')
        self.assertIsNotNone(result)
        self.assertEqual(result['full_summary'], 'c')

    def test_prefix_text(self):
        """JSON 앞에 텍스트가 있는 경우"""
        from services.content.progressive_summary_service import _parse_summary_json
        result = _parse_summary_json('여기 결과입니다: {"one_line": "test"}')
        self.assertEqual(result['one_line'], 'test')

    def test_empty_string(self):
        """빈 문자열은 None"""
        from services.content.progressive_summary_service import _parse_summary_json
        self.assertIsNone(_parse_summary_json(''))

    def test_plain_text_returns_none(self):
        """일반 텍스트는 None"""
        from services.content.progressive_summary_service import _parse_summary_json
        self.assertIsNone(_parse_summary_json('그냥 텍스트입니다'))

    def test_invalid_json_returns_none(self):
        """유효하지 않은 JSON은 None"""
        from services.content.progressive_summary_service import _parse_summary_json
        self.assertIsNone(_parse_summary_json('{invalid json content}'))


if __name__ == '__main__':
    unittest.main()
