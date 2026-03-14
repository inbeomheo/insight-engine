"""commentary_service 단위 테스트"""
import unittest
from unittest.mock import patch


class TestAddCommentary(unittest.TestCase):

    def test_empty_content_raises(self):
        from services.content.commentary_service import add_commentary
        with self.assertRaises(ValueError):
            add_commentary("")

    def test_whitespace_raises(self):
        from services.content.commentary_service import add_commentary
        with self.assertRaises(ValueError):
            add_commentary("   ")

    @patch('services.content.commentary_service._get_model', return_value='gemini/gemini-3-flash-preview')
    @patch('services.core.ai_service.create_content')
    def test_successful_commentary(self, mock_create, mock_model):
        commented_text = (
            "# 제목\n\n"
            "인공지능은 머신러닝을 기반으로 합니다.\n\n"
            "> **[해설]** 머신러닝은 데이터에서 패턴을 학습하는 기술입니다.\n\n"
            "딥러닝은 신경망을 사용합니다.\n\n"
            "> **[해설]** 신경망은 인간 뇌의 구조를 모방한 알고리즘입니다."
        )
        mock_create.return_value = {'content': commented_text}

        from services.content.commentary_service import add_commentary
        result = add_commentary("인공지능은 머신러닝을 기반으로 합니다.")
        self.assertIn("commented_content", result)
        self.assertEqual(result["comment_count"], 2)

    @patch('services.content.commentary_service._get_model', return_value='gemini/gemini-3-flash-preview')
    @patch('services.core.ai_service.create_content')
    def test_no_comments_added(self, mock_create, mock_model):
        mock_create.return_value = {'content': '원본 그대로 반환'}
        from services.content.commentary_service import add_commentary
        result = add_commentary("원본 텍스트")
        self.assertEqual(result["comment_count"], 0)

    @patch('services.content.commentary_service._get_model', return_value='gemini/gemini-3-flash-preview')
    @patch('services.core.ai_service.create_content')
    def test_empty_response_fallback(self, mock_create, mock_model):
        mock_create.return_value = {'content': ''}
        from services.content.commentary_service import add_commentary
        result = add_commentary("원본 텍스트")
        # 빈 응답 시 원본 반환
        self.assertEqual(result["commented_content"], "원본 텍스트")


if __name__ == '__main__':
    unittest.main()
