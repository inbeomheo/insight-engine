"""프롬프트 시스템 정보 API 테스트."""
import unittest

from app import create_app


class TestPromptsInfo(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_returns_prompt_info(self):
        """프롬프트 시스템 정보 JSON 반환."""
        resp = self.client.get('/api/prompts/info')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('version', data)
        self.assertIn('styles', data)
        self.assertIn('forbidden_expressions', data)
        self.assertIn('total_styles', data)

    def test_styles_have_required_fields(self):
        """각 스타일에 필수 필드 포함."""
        resp = self.client.get('/api/prompts/info')
        data = resp.get_json()
        for style in data['styles']:
            self.assertIn('id', style)
            self.assertIn('label', style)
            self.assertIn('prompt_length', style)
            self.assertIn('has_examples', style)
            self.assertGreater(style['prompt_length'], 0)

    def test_forbidden_expressions_is_list(self):
        """금칙어가 리스트 형태."""
        resp = self.client.get('/api/prompts/info')
        data = resp.get_json()
        self.assertIsInstance(data['forbidden_expressions'], list)
        self.assertGreater(len(data['forbidden_expressions']), 0)

    def test_styles_have_forbidden_count(self):
        """각 스타일에 forbidden_count 필드가 0 이상의 정수로 포함."""
        resp = self.client.get('/api/prompts/info')
        data = resp.get_json()
        for style in data['styles']:
            self.assertIn('forbidden_count', style)
            self.assertIsInstance(style['forbidden_count'], int)
            self.assertGreaterEqual(style['forbidden_count'], 0)


if __name__ == '__main__':
    unittest.main()
