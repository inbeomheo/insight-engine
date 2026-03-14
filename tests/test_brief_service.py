"""brief_service 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock


class TestGenerateBrief(unittest.TestCase):

    def test_empty_topic_raises(self):
        from services.content.brief_service import generate_brief
        with self.assertRaises(ValueError):
            generate_brief("")

    def test_whitespace_topic_raises(self):
        from services.content.brief_service import generate_brief
        with self.assertRaises(ValueError):
            generate_brief("   ")

    @patch('services.content.brief_service._get_model', return_value='gemini/gemini-3-flash-preview')
    @patch('services.core.ai_service.create_content')
    def test_successful_brief(self, mock_create, mock_model):
        mock_create.return_value = {
            'content': '{"title_suggestions": ["AI 입문"], "overview": "개요", '
                       '"target_audience": "개발자", "key_points": ["포인트1"], '
                       '"recommended_structure": ["서론"], "keywords": ["AI"], "tone": "전문적"}'
        }
        from services.content.brief_service import generate_brief
        result = generate_brief("인공지능 입문")
        self.assertIn("title_suggestions", result)
        self.assertIn("overview", result)
        self.assertEqual(result["target_audience"], "개발자")

    @patch('services.content.brief_service._get_model', return_value='gemini/gemini-3-flash-preview')
    @patch('services.core.ai_service.create_content')
    def test_parse_failure_fallback(self, mock_create, mock_model):
        mock_create.return_value = {'content': '유효하지 않은 JSON 응답입니다'}
        from services.content.brief_service import generate_brief
        result = generate_brief("테스트 주제")
        # 파싱 실패 시에도 구조 반환
        self.assertIn("title_suggestions", result)
        self.assertIn("overview", result)

    @patch('services.content.brief_service._get_model', return_value='gemini/gemini-3-flash-preview')
    @patch('services.core.ai_service.create_content')
    def test_with_keywords(self, mock_create, mock_model):
        mock_create.return_value = {
            'content': '{"title_suggestions": ["제목"], "overview": "개요", '
                       '"target_audience": "독자", "key_points": [], '
                       '"recommended_structure": [], "keywords": ["AI", "ML"], "tone": "친근"}'
        }
        from services.content.brief_service import generate_brief
        result = generate_brief("AI", keywords=["머신러닝", "딥러닝"])
        self.assertIsInstance(result, dict)


if __name__ == '__main__':
    unittest.main()
