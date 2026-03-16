"""R88: /api/prompts/info에 total_prompt_chars 테스트."""
import unittest

from app import create_app


class TestPromptsTotalChars(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_total_prompt_chars_exists(self):
        """응답에 total_prompt_chars 필드 포함."""
        resp = self.client.get('/api/prompts/info')
        data = resp.get_json()
        self.assertIn('total_prompt_chars', data)

    def test_total_prompt_chars_is_int(self):
        """total_prompt_chars는 정수."""
        resp = self.client.get('/api/prompts/info')
        data = resp.get_json()
        self.assertIsInstance(data['total_prompt_chars'], int)

    def test_total_prompt_chars_positive(self):
        """total_prompt_chars는 0보다 큼."""
        resp = self.client.get('/api/prompts/info')
        data = resp.get_json()
        self.assertGreater(data['total_prompt_chars'], 0)

    def test_total_equals_sum_of_lengths(self):
        """total_prompt_chars == 각 스타일 prompt_length 합계."""
        resp = self.client.get('/api/prompts/info')
        data = resp.get_json()
        expected = sum(s['prompt_length'] for s in data['styles'])
        self.assertEqual(data['total_prompt_chars'], expected)

    def test_total_prompt_chars_greater_than_style_count(self):
        """합계가 스타일 수보다 훨씬 큼 (프롬프트가 비어있지 않음 확인)."""
        resp = self.client.get('/api/prompts/info')
        data = resp.get_json()
        self.assertGreater(data['total_prompt_chars'], data['total_styles'] * 10)


if __name__ == '__main__':
    unittest.main()
