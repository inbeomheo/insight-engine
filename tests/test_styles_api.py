"""스타일 목록 API 테스트."""
import unittest

from app import create_app


class TestStylesApi(unittest.TestCase):
    """GET /api/styles 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_returns_styles_list(self):
        """스타일 목록이 배열로 반환."""
        resp = self.client.get('/api/styles')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('styles', data)
        self.assertIn('count', data)
        self.assertGreater(data['count'], 0)

    def test_style_has_required_fields(self):
        """각 스타일에 id, label, temperature 포함."""
        resp = self.client.get('/api/styles')
        data = resp.get_json()
        for style in data['styles']:
            self.assertIn('id', style)
            self.assertIn('label', style)
            self.assertIn('temperature', style)
            self.assertIsInstance(style['temperature'], float)

    def test_includes_modifiers(self):
        """모디파이어 정보 포함."""
        resp = self.client.get('/api/styles')
        data = resp.get_json()
        self.assertIn('modifiers', data)
        self.assertIn('length', data['modifiers'])

    def test_no_auth_required(self):
        """인증 없이 접근 가능 (공개 API)."""
        resp = self.client.get('/api/styles')
        self.assertEqual(resp.status_code, 200)


if __name__ == '__main__':
    unittest.main()
