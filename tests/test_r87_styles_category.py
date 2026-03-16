"""R87: /api/styles에 category (정보형/창작형/마케팅형) 분류 테스트."""
import unittest

from app import create_app


class TestStylesCategory(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_each_style_has_category(self):
        """모든 스타일에 category 필드 포함."""
        resp = self.client.get('/api/styles')
        data = resp.get_json()
        for style in data['styles']:
            self.assertIn('category', style, f"{style['id']}에 category 없음")

    def test_category_values_valid(self):
        """category 값이 정보형/창작형/마케팅형 중 하나."""
        valid = {'정보형', '창작형', '마케팅형'}
        resp = self.client.get('/api/styles')
        data = resp.get_json()
        for style in data['styles']:
            self.assertIn(style['category'], valid, f"{style['id']}의 category가 유효하지 않음: {style['category']}")

    def test_all_three_categories_present(self):
        """세 가지 카테고리가 모두 존재."""
        resp = self.client.get('/api/styles')
        data = resp.get_json()
        categories = {s['category'] for s in data['styles']}
        self.assertIn('정보형', categories)
        self.assertIn('창작형', categories)
        self.assertIn('마케팅형', categories)

    def test_blog_seo_is_marketing(self):
        """blog_seo는 마케팅형."""
        resp = self.client.get('/api/styles')
        data = resp.get_json()
        blog_seo = next(s for s in data['styles'] if s['id'] == 'blog_seo')
        self.assertEqual(blog_seo['category'], '마케팅형')

    def test_summary_is_informational(self):
        """summary는 정보형."""
        resp = self.client.get('/api/styles')
        data = resp.get_json()
        summary = next(s for s in data['styles'] if s['id'] == 'summary')
        self.assertEqual(summary['category'], '정보형')

    def test_brunch_essay_is_creative(self):
        """brunch_essay는 창작형."""
        resp = self.client.get('/api/styles')
        data = resp.get_json()
        brunch = next(s for s in data['styles'] if s['id'] == 'brunch_essay')
        self.assertEqual(brunch['category'], '창작형')


if __name__ == '__main__':
    unittest.main()
