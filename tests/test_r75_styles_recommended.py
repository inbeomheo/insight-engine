"""R75: /api/styles 추천 스타일 필드 테스트."""
import unittest

from app import create_app


class TestStylesRecommended(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_recommended_field_exists(self):
        """응답에 recommended 필드 포함."""
        resp = self.client.get('/api/styles')
        data = resp.get_json()
        self.assertIn('recommended', data)
        self.assertIsInstance(data['recommended'], list)

    def test_recommended_count_is_three(self):
        """추천 스타일이 정확히 3개."""
        resp = self.client.get('/api/styles')
        data = resp.get_json()
        self.assertEqual(len(data['recommended']), 3)

    def test_recommended_ids(self):
        """추천 스타일이 blog_seo, summary, tutorial."""
        resp = self.client.get('/api/styles')
        data = resp.get_json()
        rec_ids = [s['id'] for s in data['recommended']]
        self.assertIn('blog_seo', rec_ids)
        self.assertIn('summary', rec_ids)
        self.assertIn('tutorial', rec_ids)

    def test_recommended_has_same_fields_as_styles(self):
        """추천 스타일에도 id, label, temperature 포함."""
        resp = self.client.get('/api/styles')
        data = resp.get_json()
        for style in data['recommended']:
            self.assertIn('id', style)
            self.assertIn('label', style)
            self.assertIn('temperature', style)

    def test_recommended_subset_of_styles(self):
        """추천 스타일은 전체 스타일의 부분집합."""
        resp = self.client.get('/api/styles')
        data = resp.get_json()
        all_ids = {s['id'] for s in data['styles']}
        for rec in data['recommended']:
            self.assertIn(rec['id'], all_ids)


if __name__ == '__main__':
    unittest.main()
