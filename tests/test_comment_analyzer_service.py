"""댓글 심층 분석 서비스 테스트"""
import unittest
from unittest.mock import patch, MagicMock


class TestCommentAnalyzerService(unittest.TestCase):

    @patch('services.comment_analyzer_service.ai_service')
    def test_analyze_comments_returns_structured_result(self, mock_ai):
        mock_ai.create_content.return_value = {
            'content': '{"insights":["I1"],"questions":["Q1"],"fact_checks":[],"sentiments":["S1"]}',
            'usage': {'total_tokens': 100}
        }
        from services.comment_analyzer_service import analyze_comments
        result = analyze_comments(
            comments=['좋은 영상입니다', '실제로 써봤는데 좋았어요'],
            model='gemini/gemini-3-flash-preview'
        )
        self.assertIn('insights', result)
        self.assertIn('questions', result)
        self.assertIn('fact_checks', result)
        self.assertIn('sentiments', result)
        self.assertEqual(result['insights'], ['I1'])

    @patch('services.comment_analyzer_service.ai_service')
    def test_analyze_comments_empty_list(self, mock_ai):
        from services.comment_analyzer_service import analyze_comments
        result = analyze_comments(comments=[], model='gemini/gemini-3-flash-preview')
        self.assertIsNone(result)
        mock_ai.create_content.assert_not_called()

    @patch('services.comment_analyzer_service.ai_service')
    def test_analyze_comments_ai_failure_returns_none(self, mock_ai):
        mock_ai.create_content.side_effect = Exception('AI error')
        from services.comment_analyzer_service import analyze_comments
        result = analyze_comments(
            comments=['test comment'],
            model='gemini/gemini-3-flash-preview'
        )
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
