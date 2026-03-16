"""R102: /api/rewrite/platforms에 icon_emoji 필드 추가 테스트"""
import unittest

from app import create_app


class TestRewritePlatformIcons(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_each_platform_has_icon_emoji(self):
        """모든 플랫폼에 icon_emoji 필드가 있다."""
        resp = self.client.get('/api/rewrite/platforms')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        for p in data['available_platforms']:
            self.assertIn('icon_emoji', p, f"{p['name']}에 icon_emoji 없음")
            self.assertIsInstance(p['icon_emoji'], str)
            self.assertTrue(len(p['icon_emoji']) > 0, f"{p['name']}의 icon_emoji가 비어있음")

    def test_icon_emoji_matches_config(self):
        """icon_emoji가 config.PLATFORM_PRESETS 값과 일치한다."""
        from config import PLATFORM_PRESETS
        resp = self.client.get('/api/rewrite/platforms')
        data = resp.get_json()
        platform_map = {p['name']: p['icon_emoji'] for p in data['available_platforms']}
        for name, preset in PLATFORM_PRESETS.items():
            self.assertEqual(platform_map[name], preset['icon_emoji'])

    def test_twitter_icon_is_bird(self):
        """twitter의 아이콘이 새 이모지다."""
        resp = self.client.get('/api/rewrite/platforms')
        data = resp.get_json()
        twitter = next(p for p in data['available_platforms'] if p['name'] == 'twitter')
        self.assertEqual(twitter['icon_emoji'], '🐦')

    def test_backward_compatible_fields_still_present(self):
        """기존 필드(name, max_chars, tone, format)가 여전히 존재한다."""
        resp = self.client.get('/api/rewrite/platforms')
        data = resp.get_json()
        for p in data['available_platforms']:
            for field in ('name', 'max_chars', 'tone', 'format', 'icon_emoji'):
                self.assertIn(field, p)


if __name__ == '__main__':
    unittest.main()
