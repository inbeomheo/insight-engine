"""R50: /api/styles에 각 스타일의 description 필드 테스트"""
import unittest

from app import create_app


class TestStyleDescription(unittest.TestCase):
    """GET /api/styles의 description 필드 검증."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_each_style_has_description(self):
        """모든 스타일에 description 필드가 존재해야 한다."""
        resp = self.client.get('/api/styles')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        for style in data['styles']:
            self.assertIn('description', style,
                          f"스타일 '{style['id']}'에 description 없음")

    def test_descriptions_are_non_empty_strings(self):
        """모든 스타일의 description이 빈 문자열이 아니어야 한다."""
        resp = self.client.get('/api/styles')
        data = resp.get_json()
        for style in data['styles']:
            self.assertIsInstance(style['description'], str)
            self.assertTrue(len(style['description']) > 0,
                            f"스타일 '{style['id']}'의 description이 비어있음")

    def test_description_field_coexists_with_existing_fields(self):
        """description 추가 후에도 기존 필드(id, label, temperature)가 유지."""
        resp = self.client.get('/api/styles')
        data = resp.get_json()
        for style in data['styles']:
            self.assertIn('id', style)
            self.assertIn('label', style)
            self.assertIn('temperature', style)
            self.assertIn('description', style)

    def test_blog_seo_has_specific_description(self):
        """blog_seo 스타일의 description이 특정 내용을 포함."""
        resp = self.client.get('/api/styles')
        data = resp.get_json()
        blog_seo = next(s for s in data['styles'] if s['id'] == 'blog_seo')
        self.assertIn('SEO', blog_seo['description'])

    def test_style_count_unchanged(self):
        """description 추가 후에도 스타일 수가 14개로 유지."""
        resp = self.client.get('/api/styles')
        data = resp.get_json()
        self.assertEqual(data['count'], 14)


if __name__ == '__main__':
    unittest.main()
