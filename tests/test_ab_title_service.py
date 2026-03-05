"""ab_title_service 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.ab_title_service import generate_title_variants, _get_available_model


class TestGetAvailableModel(unittest.TestCase):

    @patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'})
    def test_returns_gemini(self):
        model = _get_available_model()
        self.assertIsNotNone(model)
        self.assertTrue(model.startswith('gemini/'))

    @patch.dict('os.environ', {}, clear=True)
    def test_returns_none_without_keys(self):
        model = _get_available_model()
        self.assertIsNone(model)


class TestGenerateTitleVariants(unittest.TestCase):

    def test_empty_input(self):
        self.assertEqual(generate_title_variants('', 'title'), [])
        self.assertEqual(generate_title_variants('content', ''), [])

    @patch.dict('os.environ', {}, clear=True)
    def test_no_model_raises(self):
        with self.assertRaises(RuntimeError):
            generate_title_variants('content', 'title')

    @patch('services.ab_title_service.completion')
    @patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'})
    def test_returns_titles(self, mock_completion):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '["제목1", "제목2", "제목3"]'
        mock_completion.return_value = mock_response

        result = generate_title_variants('콘텐츠 본문', '원본 제목')
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], '제목1')

    @patch('services.ab_title_service.completion')
    @patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'})
    def test_handles_code_block(self, mock_completion):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '```json\n["A", "B"]\n```'
        mock_completion.return_value = mock_response

        result = generate_title_variants('content', 'title')
        self.assertEqual(result, ['A', 'B'])

    @patch('services.ab_title_service.completion')
    @patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'})
    def test_count_limit(self, mock_completion):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '["A", "B", "C", "D", "E"]'
        mock_completion.return_value = mock_response

        result = generate_title_variants('content', 'title', count=3)
        self.assertEqual(len(result), 3)


if __name__ == '__main__':
    unittest.main()
