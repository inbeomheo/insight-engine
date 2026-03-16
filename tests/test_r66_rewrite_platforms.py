"""R66: /api/rewrite/platforms 엔드포인트 테스트"""
import unittest

from app import create_app


class TestRewritePlatforms(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_returns_available_platforms(self):
        """available_platforms 필드가 리스트로 반환된다."""
        resp = self.client.get('/api/rewrite/platforms')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('available_platforms', data)
        self.assertIsInstance(data['available_platforms'], list)

    def test_contains_known_platforms(self):
        """twitter, linkedin 등 알려진 플랫폼이 포함된다."""
        resp = self.client.get('/api/rewrite/platforms')
        data = resp.get_json()
        names = [p['name'] for p in data['available_platforms']]
        self.assertIn('twitter', names)
        self.assertIn('linkedin', names)

    def test_platform_has_required_fields(self):
        """각 플랫폼에 name, max_chars, tone, format 필드가 있다."""
        resp = self.client.get('/api/rewrite/platforms')
        data = resp.get_json()
        for p in data['available_platforms']:
            self.assertIn('name', p)
            self.assertIn('max_chars', p)
            self.assertIn('tone', p)
            self.assertIn('format', p)

    def test_no_auth_required(self):
        """인증 없이 접근 가능하다."""
        resp = self.client.get('/api/rewrite/platforms')
        self.assertEqual(resp.status_code, 200)

    def test_platform_count_matches_config(self):
        """반환 수가 config.PLATFORM_PRESETS 수와 일치한다."""
        from config import PLATFORM_PRESETS
        resp = self.client.get('/api/rewrite/platforms')
        data = resp.get_json()
        self.assertEqual(len(data['available_platforms']), len(PLATFORM_PRESETS))


if __name__ == '__main__':
    unittest.main()
